"""
Gemini Live API Bidirectional Streaming Client for VTA.

Architecture: ONE session for the entire tutorial.
- speak() sends instructions via send_client_content (no reconnect)
- After turn_complete, model is already listening — just enable mic
- Session resumption handles server disconnects transparently
- No more reconnect-per-task pattern

Based on Google's Live API reference:
  - session.receive() is a single long-lived async generator spanning all turns
  - turn_complete is an in-band signal, not session termination
  - send_client_content injects new instructions without reconnecting
"""

import asyncio
import base64
import logging
import os
import re
import time
from typing import Callable, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

ARIA_SYSTEM_PROMPT = """You are ARIA, a friendly voice tutor. You MUST follow these rules:
1. Speak in English only.
2. Read the provided content exactly as written. Do not make up your own content.
3. Do not teach or explain beyond what is written in the instructions.
4. Keep responses short and conversational.
5. After reading the content, ask the student if they have questions or are ready to continue."""

GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


class GeminiLiveClient:
    """Single-session bidirectional voice client using Gemini Live API.

    Key design: ONE session for the entire tutorial. No reconnect per task.
    Uses send_client_content() to inject new instructions mid-session.
    """

    def __init__(
        self,
        audio_output_callback: Optional[Callable] = None,
        transcript_callback: Optional[Callable] = None,
    ):
        self.audio_output_callback = audio_output_callback
        self.transcript_callback = transcript_callback

        self._genai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        self._session = None
        self._session_ctx = None
        self.is_active = False

        self._session_id = None
        self._system_prompt = ARIA_SYSTEM_PROMPT

        self._background_tasks: list = []
        self._audio_input_queue = asyncio.Queue()

        # Transcript buffer
        self._transcript_buffer: list = []
        self._transcript_event = asyncio.Event()
        self._transcript_settle_task = None

        # Speech detection
        self._last_audio_output_time = 0.0
        self._speech_done = asyncio.Event()

        # Cooldown
        self._transcript_ready_after = 0.0

        # Playback
        self._playback_done_event = asyncio.Event()
        self._playback_done_event.set()

        # Mic gate
        self._mic_enabled = False

        # Output transcript buffer
        self._output_transcript_buffer: list = []

        # Audio output buffer
        self._audio_out_buffer = bytearray()

        # Session resumption
        self._resumption_handle = None

        # Track if session has been started
        self._session_started = False

        # Pending prompt to send via send_text_kickstart
        self._pending_prompt = None

    _mic_drop_log_count = 0

    # ── Session lifecycle ───────────────────────────────────────────────

    async def _start_session(self, system_prompt: str) -> bool:
        """Start a NEW Gemini Live session. Called once per tutorial."""
        logger.info("Starting new Gemini Live session...")

        config_kwargs = {
            "response_modalities": ["AUDIO"],
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore",
                    ),
                ),
            ),
            "system_instruction": types.Content(
                parts=[types.Part(text=system_prompt)],
            ),
            "input_audio_transcription": types.AudioTranscriptionConfig(),
            "output_audio_transcription": types.AudioTranscriptionConfig(),
        }

        # Try to enable session resumption (may not be supported by all models)
        try:
            config_kwargs["session_resumption"] = types.SessionResumptionConfig()
        except Exception:
            pass

        try:
            config = types.LiveConnectConfig(**config_kwargs)

            self._session_ctx = self._genai_client.aio.live.connect(
                model=GEMINI_LIVE_MODEL,
                config=config,
            )
            self._session = await self._session_ctx.__aenter__()
            self.is_active = True
            self._session_started = True

            self._reset_state()

            # Start background tasks
            self._background_tasks = [
                asyncio.create_task(self._audio_sender_loop()),
                asyncio.create_task(self._response_processor_loop()),
                asyncio.create_task(self._monitor_speech_completion()),
            ]

            logger.info("Gemini Live session started successfully")
            return True

        except Exception as e:
            logger.error(f"Session start failed: {e}")
            self.is_active = False
            return False

    def _reset_state(self):
        """Reset per-turn state without closing session."""
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self._speech_done.clear()
        self._playback_done_event.clear()
        self._last_audio_output_time = 0.0
        self._mic_enabled = False
        self._output_transcript_buffer.clear()
        self._audio_out_buffer.clear()
        if self._transcript_settle_task and not self._transcript_settle_task.done():
            self._transcript_settle_task.cancel()
        self._transcript_settle_task = None

    async def reconnect(self, resume_context: str = "", prompt_override: str = "") -> bool:
        """Send new instructions to the model.

        If session is alive: uses send_client_content (fast, no reconnect).
        If session is dead: starts a new session (slow, but necessary).

        This method preserves the same interface as before so orchestrator.py
        requires NO changes.
        """
        if not self._session_id:
            logger.error("Cannot reconnect — no stored session ID")
            return False

        # Build the prompt
        if prompt_override:
            prompt = prompt_override
        else:
            prompt = self._system_prompt or ARIA_SYSTEM_PROMPT
            if resume_context:
                prompt += f"\n\n{resume_context}"

        # If session is alive, just prepare for next instruction (no reconnect!)
        if self.is_active and self._session and self._session_started:
            logger.info("Same session — preparing for next instruction")
            self._reset_state()
            self._transcript_ready_after = time.time() + 1.0
            self._pending_prompt = prompt  # Will be sent by send_text_kickstart
            return True

        # Session is dead — start a fresh one
        logger.info("Session dead — starting new session")
        await self._teardown()
        return await self._start_session(prompt)

    async def send_text_kickstart(self, text: str = "Please begin."):
        """Send instruction to make the model speak.

        Uses the pending prompt from reconnect() if available,
        otherwise uses the provided text.
        """
        if not self.is_active or not self._session:
            logger.warning("Stream not ready for text kickstart")
            return

        # Reset speech detection
        self._speech_done.clear()
        self._last_audio_output_time = 0.0
        self._playback_done_event.clear()

        # Use pending prompt from reconnect() if available
        instruction = self._pending_prompt or text
        self._pending_prompt = None

        logger.info(f"Instruction: '{instruction[:100]}'")

        try:
            await self._session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=instruction)],
                ),
                turn_complete=True,
            )
        except Exception as e:
            logger.error(f"send_client_content failed: {e}")
            self.is_active = False

    # ── Audio I/O ───────────────────────────────────────────────────────

    def add_audio_chunk(self, audio_data: str):
        """Queue a base64 audio chunk from the student."""
        if not self.is_active or not self._session:
            GeminiLiveClient._mic_drop_log_count += 1
            if GeminiLiveClient._mic_drop_log_count % 100 == 1:
                logger.debug(f"[MIC] Audio dropped — stream not ready (count={GeminiLiveClient._mic_drop_log_count})")
            return

        if not self._mic_enabled:
            GeminiLiveClient._mic_drop_log_count += 1
            if GeminiLiveClient._mic_drop_log_count % 200 == 1:
                logger.info(f"[MIC] Audio dropped — mic gate closed (count={GeminiLiveClient._mic_drop_log_count})")
            return

        GeminiLiveClient._mic_drop_log_count = 0

        try:
            raw_bytes = base64.b64decode(audio_data)
        except Exception:
            return

        self._audio_input_queue.put_nowait(raw_bytes)

    def enable_mic(self):
        self._mic_enabled = True
        GeminiLiveClient._mic_drop_log_count = 0
        logger.info("Mic enabled")

    def disable_mic(self):
        self._mic_enabled = False
        logger.info("Mic disabled")

    # ── Transcript ──────────────────────────────────────────────────────

    async def wait_for_student_speech(self, timeout: float = 120) -> str:
        """Wait for student to speak. No reconnect — session stays alive."""
        # If session died, restart it
        if not self.is_active or not self._session:
            logger.info("Session closed — restarting for student speech")
            prompt = self._system_prompt or ARIA_SYSTEM_PROMPT
            success = await self._start_session(prompt)
            if not success:
                return ""
            await asyncio.sleep(0.5)

        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self.enable_mic()

        try:
            deadline = time.time() + timeout if timeout > 0 else None

            while True:
                # Check session health
                if not self.is_active or not self._session:
                    logger.info("Session died while waiting — restarting")
                    self.disable_mic()
                    prompt = self._system_prompt or ARIA_SYSTEM_PROMPT
                    if not await self._start_session(prompt):
                        return ""
                    self._transcript_buffer.clear()
                    self._transcript_event.clear()
                    self.enable_mic()

                try:
                    wait_time = 2.0
                    if deadline:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            logger.warning(f"wait_for_student_speech timed out after {timeout}s")
                            return ""
                        wait_time = min(wait_time, remaining)

                    await asyncio.wait_for(self._transcript_event.wait(), timeout=wait_time)
                    break
                except asyncio.TimeoutError:
                    if deadline and time.time() >= deadline:
                        return ""
                    continue
        finally:
            self.disable_mic()

        return self.get_and_clear_transcript()

    def get_and_clear_transcript(self) -> str:
        text = " ".join(t for _, t in self._transcript_buffer).strip()
        text = re.sub(r'\s+', ' ', text)
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        return text

    async def _settle_transcript(self):
        """Wait 1.5s after last fragment before signaling."""
        await asyncio.sleep(1.5)
        if self._transcript_buffer:
            full_text = " ".join(t for _, t in self._transcript_buffer)
            if self.transcript_callback:
                await self.transcript_callback(full_text, "USER")
            self._transcript_event.set()

    # ── Speech detection ────────────────────────────────────────────────

    async def wait_for_speech_done(self, timeout: float = 90):
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self._speech_done.clear()

        logger.info(f"Waiting for speech done (timeout={timeout}s)...")
        try:
            await asyncio.wait_for(self._speech_done.wait(), timeout=timeout)
            logger.info("Speech done")
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_speech_done timed out after {timeout}s")

    async def wait_for_playback_done(self, timeout: float = 15.0):
        try:
            await asyncio.wait_for(self._playback_done_event.wait(), timeout=timeout)
            logger.info("Playback complete")
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_playback_done timed out after {timeout}s")

    def signal_playback_done(self):
        self._playback_done_event.set()

    async def _monitor_speech_completion(self):
        SILENCE_GAP = 2.0
        while self.is_active:
            await asyncio.sleep(0.5)
            if self._last_audio_output_time == 0.0:
                continue
            gap = time.time() - self._last_audio_output_time
            if gap >= SILENCE_GAP and not self._speech_done.is_set():
                logger.info(f"Speech done ({gap:.1f}s gap)")
                self._speech_done.set()

    # ── Background tasks ────────────────────────────────────────────────

    async def _audio_sender_loop(self):
        """Send student audio + silence keepalives."""
        SILENCE_CHUNK = b'\x00' * 3200
        SILENCE_AFTER_GAP = 0.5
        last_send_time = time.time()

        while self.is_active:
            try:
                try:
                    raw_bytes = await asyncio.wait_for(
                        self._audio_input_queue.get(), timeout=0.1
                    )
                    last_send_time = time.time()
                except asyncio.TimeoutError:
                    if self.is_active and self._session:
                        gap = time.time() - last_send_time
                        if gap >= SILENCE_AFTER_GAP:
                            try:
                                await self._session.send_realtime_input(
                                    audio=types.Blob(
                                        data=SILENCE_CHUNK,
                                        mime_type="audio/pcm;rate=16000",
                                    ),
                                )
                                last_send_time = time.time()
                            except Exception:
                                pass
                    continue

                if not self.is_active or not self._session:
                    continue

                await self._session.send_realtime_input(
                    audio=types.Blob(
                        data=raw_bytes,
                        mime_type="audio/pcm;rate=16000",
                    ),
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_active:
                    logger.error(f"Audio send error: {e}")
                    await asyncio.sleep(0.1)

    async def _response_processor_loop(self):
        """Process all responses from the session — spans ALL turns."""
        try:
            if not self._session:
                return

            async for response in self._session.receive():
                if not self.is_active:
                    break

                # Session resumption
                if hasattr(response, 'session_resumption_update') and response.session_resumption_update:
                    update = response.session_resumption_update
                    if hasattr(update, 'new_handle') and update.new_handle:
                        self._resumption_handle = update.new_handle
                        logger.info("Session resumption handle updated")

                # GoAway — server will disconnect soon
                if hasattr(response, 'go_away') and response.go_away is not None:
                    time_left = getattr(response.go_away, 'time_left', 'unknown')
                    logger.warning(f"GoAway received, {time_left} remaining — will reconnect")

                # Server content
                if response.server_content:
                    sc = response.server_content

                    # Model audio output
                    if sc.model_turn and sc.model_turn.parts:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                self._last_audio_output_time = time.time()
                                self._speech_done.clear()
                                self._audio_out_buffer.extend(part.inline_data.data)
                                if len(self._audio_out_buffer) >= 9600:
                                    audio_b64 = base64.b64encode(bytes(self._audio_out_buffer)).decode("utf-8")
                                    self._audio_out_buffer.clear()
                                    if self.audio_output_callback:
                                        await self.audio_output_callback(audio_b64)

                    # Turn complete
                    if sc.turn_complete:
                        logger.info("[TURN COMPLETE] Model finished speaking — listening")
                        # Flush audio buffer
                        if self._audio_out_buffer and self.audio_output_callback:
                            audio_b64 = base64.b64encode(bytes(self._audio_out_buffer)).decode("utf-8")
                            self._audio_out_buffer.clear()
                            await self.audio_output_callback(audio_b64)
                        # Flush output transcript
                        if self._output_transcript_buffer and self.transcript_callback:
                            full_text = " ".join(self._output_transcript_buffer)
                            self._output_transcript_buffer.clear()
                            await self.transcript_callback(full_text, "ASSISTANT")

                    # Interrupted — model was interrupted by student
                    if hasattr(sc, 'interrupted') and sc.interrupted:
                        logger.info("[INTERRUPTED] Student interrupted model")

                    # Input transcription (student speech)
                    if sc.input_transcription and sc.input_transcription.text:
                        user_text = sc.input_transcription.text.strip()
                        if user_text and time.time() >= self._transcript_ready_after:
                            self._transcript_buffer.append((time.time(), user_text))
                            if self._transcript_settle_task and not self._transcript_settle_task.done():
                                self._transcript_settle_task.cancel()
                            self._transcript_settle_task = asyncio.create_task(
                                self._settle_transcript()
                            )
                            logger.info(f"[STUDENT] {user_text}")

                    # Output transcription (model speech text)
                    if sc.output_transcription and sc.output_transcription.text:
                        model_text = sc.output_transcription.text.strip()
                        if model_text:
                            self._output_transcript_buffer.append(model_text)
                            logger.info(f"[ARIA] {model_text}")

            logger.info("Session receive loop ended (server closed)")

        except asyncio.CancelledError:
            logger.info("Response processor cancelled")
        except Exception as e:
            if self.is_active:
                logger.error(f"Response processor error: {e}")

        self.is_active = False
        self._session_started = False
        logger.info("Response processor exited")

    # ── Teardown ────────────────────────────────────────────────────────

    async def _teardown(self):
        self.is_active = False
        self._session_started = False

        for task in self._background_tasks:
            if task and not task.done():
                task.cancel()
        for task in self._background_tasks:
            if task:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self._background_tasks.clear()

        if self._session:
            try:
                await self._session_ctx.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
            self._session_ctx = None

        while not self._audio_input_queue.empty():
            try:
                self._audio_input_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def close(self):
        if not self.is_active and not self._session:
            return
        logger.info("Closing Gemini Live client...")
        await self._teardown()
        logger.info("Gemini Live client closed")
