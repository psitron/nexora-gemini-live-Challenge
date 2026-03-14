"""
Gemini Live API Bidirectional Streaming Client for VTA.

Replaces Nova Sonic SonicClient with Google's Gemini Live API.
Voice-only: no tool handling. Orchestrator drives flow via reconnect().
Transcript buffer lets orchestrator read what the student said.

Architecture (from Google's reference implementations):
  - session.receive() is a SINGLE long-lived async generator spanning all turns
  - turn_complete is an in-band signal, NOT a session termination
  - Audio sender and response processor run as concurrent tasks
  - Silence keepalives prevent server-side timeout
"""

import asyncio
import base64
import logging
import os
import time
from typing import Callable, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Minimal voice-only system prompt — task-specific instructions are
# baked into per-task prompt_override via reconnect().
ARIA_SYSTEM_PROMPT = """You are ARIA, a friendly voice tutor. You MUST follow these rules:
1. Speak in English only.
2. Read the provided content exactly as written. Do not make up your own content.
3. Do not teach or explain beyond what is written in the instructions.
4. Keep responses short and conversational.
5. After reading the content, ask the student if they have questions or are ready to continue.
Follow the instructions below."""

GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


class GeminiLiveClient:
    """Manages bidirectional streaming with Gemini Live API.

    Voice-only — no tool handling. The orchestrator controls task flow
    via reconnect() with per-task prompts. Student speech is captured
    in a transcript buffer for the orchestrator to read.
    """

    def __init__(
        self,
        audio_output_callback: Optional[Callable] = None,
        transcript_callback: Optional[Callable] = None,
    ):
        self.audio_output_callback = audio_output_callback
        self.transcript_callback = transcript_callback

        # Gemini client
        self._genai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        # Session state
        self._session = None
        self._session_ctx = None
        self.is_active = False

        # Stored for reconnect
        self._session_id = None
        self._system_prompt = ARIA_SYSTEM_PROMPT

        # Background tasks
        self._background_tasks: list = []

        # Audio input queue — student mic audio flows through here
        self._audio_input_queue = asyncio.Queue()

        # Transcript buffer — orchestrator reads student speech from here
        # Stores (timestamp, text) tuples so we can filter out narration-era speech
        self._transcript_buffer: list = []
        self._transcript_event = asyncio.Event()

        # Speech completion detection — detect when model stops sending audio
        self._last_audio_output_time = 0.0
        self._speech_done = asyncio.Event()

        # Transcript cooldown — ignore student speech for N seconds after stream setup
        self._transcript_ready_after = 0.0

        # Playback done — set by frontend signal when browser finishes playing audio
        self._playback_done_event = asyncio.Event()
        self._playback_done_event.set()  # Initially "done" (no audio playing yet)

        # Mic gate — when False, student audio is dropped.
        # Enabled only during wait_for_student_speech so model can't be interrupted
        # mid-narration by live mic input.
        self._mic_enabled = False

        # Output transcript buffer — accumulates fragments, flushed on turn_complete
        self._output_transcript_buffer: list = []

        # Transcript settle task — delays setting _transcript_event to collect full utterance
        self._transcript_settle_task = None

        # Audio output buffer — accumulates small chunks to reduce crackling
        self._audio_out_buffer = bytearray()

    _mic_drop_log_count = 0  # class-level counter to throttle drop logs

    def add_audio_chunk(self, audio_data: str):
        """Queue an audio chunk (base64 string) from the student.

        Drops audio if stream isn't ready or mic is gated (during narration).
        Gemini expects raw PCM bytes; frontend sends base64 → decode here.
        """
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

        # Decode base64 to raw PCM bytes for Gemini
        try:
            raw_bytes = base64.b64decode(audio_data)
        except Exception:
            logger.warning("[MIC] Failed to decode base64 audio chunk")
            return

        self._audio_input_queue.put_nowait(raw_bytes)

    def enable_mic(self):
        """Open the mic gate — student audio flows to Gemini (listening mode)."""
        self._mic_enabled = True
        GeminiLiveClient._mic_drop_log_count = 0
        logger.info("Mic enabled — student audio flowing to Gemini")

    def disable_mic(self):
        """Close the mic gate — student audio dropped (narration mode)."""
        self._mic_enabled = False
        logger.info("Mic disabled — Gemini in narration mode")

    # ── Transcript buffer for orchestrator ──────────────────────────────

    async def _ensure_live_session(self):
        """Ensure we have an active session, reconnecting if needed."""
        if self.is_active and self._session:
            return True

        logger.info("Session closed — reconnecting for student speech input")
        listen_prompt = (
            "You are ARIA, a voice tutor. The student is about to speak. "
            "Listen carefully and do not say anything until the student speaks. "
            "Stay completely silent and wait."
        )
        success = await self.reconnect(prompt_override=listen_prompt)
        if not success:
            logger.error("Failed to reconnect for student speech")
            return False
        await asyncio.sleep(0.5)
        return True

    async def wait_for_student_speech(self, timeout: float = 120) -> str:
        """Block until student speaks, return transcript text.

        If the session died (before or during waiting), automatically
        reconnects with a listening prompt.

        Enables mic on entry and disables on exit.
        """
        if not await self._ensure_live_session():
            return ""

        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self.enable_mic()

        try:
            # Use a polling loop so we can detect session death and reconnect
            deadline = time.time() + timeout if timeout > 0 else None

            while True:
                # Check if session died while waiting
                if not self.is_active or not self._session:
                    logger.info("Session died while waiting for speech — reconnecting")
                    self.disable_mic()
                    if not await self._ensure_live_session():
                        return ""
                    self._transcript_buffer.clear()
                    self._transcript_event.clear()
                    self.enable_mic()

                # Wait for transcript with short timeout for polling
                try:
                    wait_time = 2.0  # Poll every 2 seconds
                    if deadline:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            logger.warning(f"wait_for_student_speech timed out after {timeout}s")
                            return ""
                        wait_time = min(wait_time, remaining)

                    await asyncio.wait_for(self._transcript_event.wait(), timeout=wait_time)
                    # Got transcript!
                    break
                except asyncio.TimeoutError:
                    if deadline and time.time() >= deadline:
                        logger.warning(f"wait_for_student_speech timed out after {timeout}s")
                        return ""
                    # No transcript yet — loop and check session health
                    continue

        finally:
            self.disable_mic()

        return self.get_and_clear_transcript()

    def get_and_clear_transcript(self) -> str:
        """Get accumulated transcript and clear buffer.

        Cleans up fragmented syllables by collapsing multiple spaces
        and joining partial words (e.g. "rea dy" → "ready").
        """
        import re
        text = " ".join(t for _, t in self._transcript_buffer).strip()
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        return text

    async def _settle_transcript(self):
        """Wait 1.5s after last transcript fragment before signaling.

        This prevents grabbing just the first syllable — gives time for
        the full utterance to arrive in fragments.
        """
        await asyncio.sleep(1.5)
        if self._transcript_buffer:
            full_text = " ".join(t for _, t in self._transcript_buffer)
            if self.transcript_callback:
                await self.transcript_callback(full_text, "USER")
            self._transcript_event.set()

    # ── Speech completion detection ─────────────────────────────────────

    async def wait_for_speech_done(self, timeout: float = 90):
        """Wait until model finishes speaking (or timeout)."""
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self._speech_done.clear()

        logger.info(f"Waiting for Gemini to speak (timeout={timeout}s)...")
        try:
            await asyncio.wait_for(self._speech_done.wait(), timeout=timeout)
            logger.info("Gemini finished speaking")
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_speech_done timed out after {timeout}s")

    async def wait_for_playback_done(self, timeout: float = 15.0):
        """Wait until the browser signals it has finished playing all queued audio."""
        try:
            await asyncio.wait_for(self._playback_done_event.wait(), timeout=timeout)
            logger.info("Frontend playback complete")
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_playback_done timed out after {timeout}s — proceeding anyway")

    def signal_playback_done(self):
        """Called from main.py when frontend sends audio_playback_done event."""
        self._playback_done_event.set()
        logger.info("Frontend signaled: audio playback queue empty")

    async def _monitor_speech_completion(self):
        """Background task: set _speech_done when no audio output for 2s."""
        SILENCE_GAP = 2.0

        while self.is_active:
            await asyncio.sleep(0.5)

            if self._last_audio_output_time == 0.0:
                continue

            gap = time.time() - self._last_audio_output_time
            if gap >= SILENCE_GAP and not self._speech_done.is_set():
                logger.info(f"Speech done detected ({gap:.1f}s audio gap)")
                self._speech_done.set()

    # ── Text kickstart ──────────────────────────────────────────────────

    async def send_text_kickstart(self, text: str = "Please begin."):
        """Send a user text turn to trigger Gemini to start speaking."""
        if not self.is_active or not self._session:
            logger.warning("Stream not ready for text kickstart")
            return

        logger.info(f"Sending text kickstart: '{text}'")

        try:
            await self._session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=text)],
                ),
                turn_complete=True,
            )
        except Exception as e:
            logger.error(f"Text kickstart failed: {e}")

    # ── Session lifecycle ───────────────────────────────────────────────

    async def reconnect(self, resume_context: str = "", prompt_override: str = "") -> bool:
        """Tear down any existing session and create a fresh one."""
        if not self._session_id:
            logger.error("Cannot reconnect — no stored session ID")
            return False

        logger.info("Reconnecting Gemini Live session...")

        # Tear down existing session
        await self._teardown()

        # Build system prompt
        if prompt_override:
            prompt = prompt_override
        else:
            prompt = self._system_prompt or ARIA_SYSTEM_PROMPT
            if resume_context:
                prompt += f"\n\n{resume_context}"

        # Create fresh session
        try:
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore",
                        ),
                    ),
                ),
                system_instruction=types.Content(
                    parts=[types.Part(text=prompt)],
                ),
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
            )

            self._session_ctx = self._genai_client.aio.live.connect(
                model=GEMINI_LIVE_MODEL,
                config=config,
            )
            self._session = await self._session_ctx.__aenter__()
            self.is_active = True

            # Reset state
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

            # Start background tasks — all run concurrently for the session lifetime
            tasks = [
                asyncio.create_task(self._audio_sender_loop()),
                asyncio.create_task(self._response_processor_loop()),
                asyncio.create_task(self._monitor_speech_completion()),
            ]
            self._background_tasks = tasks

            # Ignore student speech for 2s after setup — prevents stale mic echo
            self._transcript_ready_after = time.time() + 2.0

            logger.info("Gemini Live session connected successfully")
            return True

        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            self.is_active = False
            return False

    async def _teardown(self):
        """Internal teardown of session and background tasks."""
        self.is_active = False

        # Cancel background tasks
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

        # Close session context manager
        if self._session:
            try:
                await self._session_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"Error closing Gemini session: {e}")
            self._session = None
            self._session_ctx = None

        # Drain audio queue
        while not self._audio_input_queue.empty():
            try:
                self._audio_input_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    # ── Background tasks ────────────────────────────────────────────────

    async def _audio_sender_loop(self):
        """Send queued student audio to Gemini Live session.

        Sends real mic audio when available. When no mic audio arrives
        for 500ms, sends a silence chunk to keep the WebSocket alive.
        """
        SILENCE_CHUNK = b'\x00' * 3200  # 100ms at 16kHz 16-bit mono
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
                    # Send silence keepalive to prevent server timeout
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
                    logger.error(f"Error sending audio to Gemini: {e}")
                    await asyncio.sleep(0.1)

    async def _response_processor_loop(self):
        """Process incoming responses from Gemini Live session.

        session.receive() is a SINGLE long-lived async generator that spans
        all turns. turn_complete is an in-band signal — the generator keeps
        yielding when the next turn starts (e.g., when the student speaks).
        """
        try:
            if not self._session:
                logger.warning("No session in response processor")
                return

            async for response in self._session.receive():
                if not self.is_active:
                    break

                # Handle server content (audio, transcripts, turn signals)
                if response.server_content:
                    sc = response.server_content

                    # Model turn — extract audio from individual parts
                    # Using model_turn.parts instead of response.data avoids
                    # the SDK concatenating non-audio parts (text/thought)
                    if sc.model_turn and sc.model_turn.parts:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                self._last_audio_output_time = time.time()
                                self._speech_done.clear()
                                # Accumulate audio data to reduce crackling
                                self._audio_out_buffer.extend(part.inline_data.data)
                                # Send when buffer reaches ~200ms of audio (9600 bytes at 24kHz 16-bit)
                                if len(self._audio_out_buffer) >= 9600:
                                    audio_b64 = base64.b64encode(bytes(self._audio_out_buffer)).decode("utf-8")
                                    self._audio_out_buffer.clear()
                                    if self.audio_output_callback:
                                        await self.audio_output_callback(audio_b64)

                    # Turn complete — model finished this turn, session stays open
                    if sc.turn_complete:
                        logger.info("[GEMINI] Model turn complete — session stays open")
                        # Flush remaining audio buffer
                        if self._audio_out_buffer and self.audio_output_callback:
                            audio_b64 = base64.b64encode(bytes(self._audio_out_buffer)).decode("utf-8")
                            self._audio_out_buffer.clear()
                            await self.audio_output_callback(audio_b64)
                        # Flush accumulated output transcript
                        if self._output_transcript_buffer and self.transcript_callback:
                            full_text = " ".join(self._output_transcript_buffer)
                            self._output_transcript_buffer.clear()
                            await self.transcript_callback(full_text, "ASSISTANT")

                    # Input transcription (user speech)
                    if sc.input_transcription and sc.input_transcription.text:
                        user_text = sc.input_transcription.text.strip()
                        if user_text:
                            if time.time() >= self._transcript_ready_after:
                                self._transcript_buffer.append((time.time(), user_text))
                                # Don't set event immediately — schedule it after a delay
                                # so we collect the full utterance, not just the first syllable
                                if self._transcript_settle_task and not self._transcript_settle_task.done():
                                    self._transcript_settle_task.cancel()
                                self._transcript_settle_task = asyncio.create_task(
                                    self._settle_transcript()
                                )
                                logger.info(f"[GEMINI TRANSCRIPT] Student said: {user_text[:100]}")
                            else:
                                logger.info(f"[GEMINI TRANSCRIPT] Cooldown — ignoring: {user_text[:80]}")

                    # Output transcription (model speech) — accumulate and send
                    # on turn_complete to avoid word-by-word display
                    if sc.output_transcription and sc.output_transcription.text:
                        model_text = sc.output_transcription.text.strip()
                        if model_text:
                            self._output_transcript_buffer.append(model_text)
                            logger.info(f"[GEMINI SPEAKING] {model_text}")

            # receive() iterator exhausted = server closed the session
            logger.info("Gemini Live session ended (server closed connection)")

        except asyncio.CancelledError:
            logger.info("Response processor cancelled")
        except Exception as e:
            if self.is_active:
                logger.error(f"Error processing Gemini response: {e}")

        self.is_active = False
        logger.info("Gemini response processor exited — is_active=False")

    # ── Cleanup ─────────────────────────────────────────────────────────

    async def close(self):
        """Close the session and clean up."""
        if not self.is_active and not self._session:
            return

        logger.info("Closing Gemini Live client...")
        await self._teardown()
        logger.info("Gemini Live client closed")
