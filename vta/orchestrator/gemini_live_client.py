"""
Gemini Live API Bidirectional Streaming Client for VTA.

The native audio model closes the WebSocket after every turn_complete.
This is server behavior we cannot change. So we reconnect per instruction,
but make it as fast and clean as possible.

Key optimizations:
- reconnect() includes the full instruction (no separate kickstart needed)
- No generic "How can I help?" — model speaks the instruction immediately
- Fast teardown and reconnect (~1s)
- Auto-reconnect for student speech if session dies
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

ARIA_SYSTEM_PROMPT = """You are Nexora, a friendly voice tutor. Rules:
1. RESPOND IN ENGLISH ONLY. YOU MUST RESPOND UNMISTAKABLY IN ENGLISH.
2. The student speaks English. All transcription and responses must be in English.
3. Say exactly what the user message tells you to say.
4. Do not add extra content beyond what is requested.
5. Keep it natural and conversational."""

GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


class GeminiLiveClient:
    """Voice client using Gemini Live API. Reconnects per instruction."""

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
        self._precreated_session = None

        self._transcript_buffer: list = []
        self._transcript_event = asyncio.Event()
        self._transcript_settle_task = None

        self._last_audio_output_time = 0.0
        self._speech_done = asyncio.Event()
        self._transcript_ready_after = 0.0
        self._output_enabled = True  # Gate for model audio output to frontend

        self._playback_done_event = asyncio.Event()
        self._playback_done_event.set()

        self._mic_enabled = False
        self._output_transcript_buffer: list = []
        self._audio_out_buffer = bytearray()

        # Store the prompt from reconnect() for send_text_kickstart()
        self._pending_instruction = None

    _mic_drop_log_count = 0

    async def _create_session(self, system_prompt: str) -> bool:
        """Create a fresh Gemini Live session."""
        try:
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore",
                        ),
                    ),
                    language_code="en-US",
                ),
                realtime_input_config=types.RealtimeInputConfig(
                    automatic_activity_detection=types.AutomaticActivityDetection(
                        disabled=False,
                        start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                        end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                        silence_duration_ms=500,
                    ),
                ),
                system_instruction=types.Content(
                    parts=[types.Part(text=system_prompt)],
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

            self._transcript_buffer.clear()
            self._transcript_event.clear()
            self._speech_done.clear()
            self._playback_done_event.clear()
            self._last_audio_output_time = 0.0
            self._mic_enabled = False
            self._output_enabled = True
            self._output_transcript_buffer.clear()
            self._audio_out_buffer.clear()
            if self._transcript_settle_task and not self._transcript_settle_task.done():
                self._transcript_settle_task.cancel()
            self._transcript_settle_task = None

            self._background_tasks = [
                asyncio.create_task(self._audio_sender_loop()),
                asyncio.create_task(self._response_processor_loop()),
                asyncio.create_task(self._monitor_speech_completion()),
            ]

            self._transcript_ready_after = time.time() + 1.5
            return True

        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            self.is_active = False
            return False

    async def _teardown(self):
        """Close session and cancel tasks."""
        self.is_active = False
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

    async def _precreate_listening_session(self):
        """Pre-create a listening session in the background so it's ready
        when wait_for_student_speech is called."""
        try:
            logger.info("Pre-creating listening session in background...")
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore",
                        ),
                    ),
                    language_code="en-US",
                ),
                realtime_input_config=types.RealtimeInputConfig(
                    automatic_activity_detection=types.AutomaticActivityDetection(
                        disabled=False,
                        start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                        end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                        silence_duration_ms=500,
                    ),
                ),
                system_instruction=types.Content(
                    parts=[types.Part(text=self._system_prompt or ARIA_SYSTEM_PROMPT)],
                ),
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
            )
            ctx = self._genai_client.aio.live.connect(
                model=GEMINI_LIVE_MODEL,
                config=config,
            )
            session = await ctx.__aenter__()
            self._precreated_session = (session, ctx)
            logger.info("Pre-created listening session ready")
        except Exception as e:
            logger.error(f"Failed to pre-create listening session: {e}")
            self._precreated_session = None

    async def reconnect(self, resume_context: str = "", prompt_override: str = "") -> bool:
        """Tear down and create fresh session with new instruction.

        The instruction is stored and sent by send_text_kickstart().
        """
        if not self._session_id:
            logger.error("No session ID")
            return False

        if prompt_override:
            self._pending_instruction = prompt_override
        else:
            prompt = self._system_prompt or ARIA_SYSTEM_PROMPT
            if resume_context:
                prompt += f"\n\n{resume_context}"
            self._pending_instruction = prompt

        await self._teardown()

        for attempt in range(1, 4):
            success = await self._create_session(self._system_prompt or ARIA_SYSTEM_PROMPT)
            if success:
                return True
            logger.warning(f"reconnect attempt {attempt}/3 failed — retrying in 1s")
            await asyncio.sleep(1)
        logger.error("reconnect failed after 3 attempts")
        return False

    async def send_text_kickstart(self, text: str = "Please begin.", image_bytes: bytes = None):
        """Send instruction (with optional image) to make the model speak.

        If image_bytes is provided, sends both the text instruction and
        the image (e.g., a PDF slide) so the model can SEE and explain it.
        """
        if not self.is_active or not self._session:
            logger.warning("Not ready for kickstart")
            return

        self._speech_done.clear()
        self._last_audio_output_time = 0.0
        self._playback_done_event.clear()

        instruction = self._pending_instruction or text
        self._pending_instruction = None

        # Build parts: text + optional image
        parts = [types.Part(text=instruction)]
        if image_bytes:
            parts.append(
                types.Part(
                    inline_data=types.Blob(
                        data=image_bytes,
                        mime_type="image/png",
                    )
                )
            )
            logger.info(f">>> {instruction[:80]} [+slide image {len(image_bytes)}B]")
        else:
            logger.info(f">>> {instruction[:100]}")

        try:
            await self._session.send_client_content(
                turns=types.Content(role="user", parts=parts),
                turn_complete=True,
            )
        except Exception as e:
            logger.error(f"Kickstart failed: {e}")
            self.is_active = False

    # ── Audio ───────────────────────────────────────────────────────────

    def add_audio_chunk(self, audio_data: str):
        if not self.is_active or not self._session:
            GeminiLiveClient._mic_drop_log_count += 1
            if GeminiLiveClient._mic_drop_log_count % 100 == 1:
                logger.debug(f"[MIC] dropped (no session, count={GeminiLiveClient._mic_drop_log_count})")
            return
        if not self._mic_enabled:
            GeminiLiveClient._mic_drop_log_count += 1
            if GeminiLiveClient._mic_drop_log_count % 200 == 1:
                logger.info(f"[MIC] dropped (gate closed, count={GeminiLiveClient._mic_drop_log_count})")
            return
        GeminiLiveClient._mic_drop_log_count = 0
        try:
            self._audio_input_queue.put_nowait(base64.b64decode(audio_data))
        except Exception:
            pass

    def enable_mic(self):
        self._mic_enabled = True
        GeminiLiveClient._mic_drop_log_count = 0
        logger.info("Mic ON")

    def disable_mic(self):
        self._mic_enabled = False
        logger.info("Mic OFF")

    # ── Transcript ──────────────────────────────────────────────────────

    async def wait_for_student_speech(self, timeout: float = 120) -> str:
        """Wait for student speech. Reconnects if session died."""
        if not self.is_active or not self._session:
            logger.info("Session dead — reconnecting for listening")
            await self._teardown()
            if not await self._create_session(
                self._system_prompt or ARIA_SYSTEM_PROMPT
            ):
                return ""
            await asyncio.sleep(0.3)

        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self._output_enabled = False  # Suppress any auto-response while listening
        self.enable_mic()

        try:
            deadline = time.time() + timeout if timeout > 0 else None
            while True:
                if not self.is_active or not self._session:
                    logger.info("Session died during wait — reconnecting")
                    self.disable_mic()
                    await self._teardown()
                    if not await self._create_session(
                        self._system_prompt or ARIA_SYSTEM_PROMPT
                    ):
                        return ""
                    self._output_enabled = False  # Re-suppress output after reconnect
                    self._transcript_buffer.clear()
                    self._transcript_event.clear()
                    self.enable_mic()

                try:
                    wait_time = 2.0
                    if deadline:
                        remaining = deadline - time.time()
                        if remaining <= 0:
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
        await asyncio.sleep(2.0)
        if self._transcript_buffer:
            full_text = " ".join(t for _, t in self._transcript_buffer)
            if self.transcript_callback:
                await self.transcript_callback(full_text, "USER")
            self._transcript_event.set()

    # ── Speech detection ────────────────────────────────────────────────

    async def wait_for_speech_done(self, timeout: float = 90):
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        # Don't clear _speech_done if already set — speech may have finished
        # before we got here (fast responses or session already closed)
        if self._speech_done.is_set():
            logger.info("Speech already done (detected before wait)")
            return
        try:
            await asyncio.wait_for(self._speech_done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Speech timeout ({timeout}s)")

    async def wait_for_playback_done(self, timeout: float = 15.0):
        try:
            await asyncio.wait_for(self._playback_done_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Playback timeout ({timeout}s)")

    def signal_playback_done(self):
        self._playback_done_event.set()

    async def _monitor_speech_completion(self):
        while self.is_active:
            await asyncio.sleep(0.5)
            if self._last_audio_output_time == 0.0:
                continue
            gap = time.time() - self._last_audio_output_time
            if gap >= 1.5 and not self._speech_done.is_set():
                logger.info(f"Speech done ({gap:.1f}s gap)")
                self._speech_done.set()
                asyncio.create_task(self._precreate_listening_session())

    # ── Background tasks ────────────────────────────────────────────────

    async def _audio_sender_loop(self):
        SILENCE = b'\x00' * 3200
        last_send = time.time()
        while self.is_active:
            try:
                try:
                    raw = await asyncio.wait_for(self._audio_input_queue.get(), timeout=0.1)
                    last_send = time.time()
                except asyncio.TimeoutError:
                    if self.is_active and self._session and (time.time() - last_send) >= 0.5:
                        try:
                            await self._session.send_realtime_input(
                                audio=types.Blob(data=SILENCE, mime_type="audio/pcm;rate=16000")
                            )
                            last_send = time.time()
                        except Exception:
                            pass
                    continue
                if not self.is_active or not self._session:
                    continue
                await self._session.send_realtime_input(
                    audio=types.Blob(data=raw, mime_type="audio/pcm;rate=16000")
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_active:
                    logger.error(f"Audio send error: {e}")
                    await asyncio.sleep(0.1)

    async def _response_processor_loop(self):
        try:
            if not self._session:
                return
            async for response in self._session.receive():
                if not self.is_active:
                    break

                if response.server_content:
                    sc = response.server_content

                    if sc.model_turn and sc.model_turn.parts:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                if not self._output_enabled:
                                    continue  # Suppress unsolicited model audio
                                self._last_audio_output_time = time.time()
                                self._speech_done.clear()
                                self._audio_out_buffer.extend(part.inline_data.data)
                                if len(self._audio_out_buffer) >= 9600:
                                    b64 = base64.b64encode(bytes(self._audio_out_buffer)).decode()
                                    self._audio_out_buffer.clear()
                                    if self.audio_output_callback:
                                        await self.audio_output_callback(b64)

                    if sc.turn_complete:
                        logger.info("[TURN COMPLETE]")
                        if self._output_enabled:
                            if self._audio_out_buffer and self.audio_output_callback:
                                b64 = base64.b64encode(bytes(self._audio_out_buffer)).decode()
                                self._audio_out_buffer.clear()
                                await self.audio_output_callback(b64)
                            if self._output_transcript_buffer and self.transcript_callback:
                                await self.transcript_callback(
                                    " ".join(self._output_transcript_buffer), "ASSISTANT"
                                )
                                self._output_transcript_buffer.clear()
                        else:
                            # Discard unsolicited output
                            self._audio_out_buffer.clear()
                            self._output_transcript_buffer.clear()

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

                    if sc.output_transcription and sc.output_transcription.text:
                        model_text = sc.output_transcription.text.strip()
                        if model_text:
                            self._output_transcript_buffer.append(model_text)
                            logger.info(f"[Nexora] {model_text}")

            logger.info("Session ended (server closed)")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.is_active:
                logger.error(f"Response error: {e}")
        self.is_active = False

    async def close(self):
        if not self.is_active and not self._session:
            return
        await self._teardown()
