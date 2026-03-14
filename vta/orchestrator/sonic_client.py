"""
Nova Sonic Bidirectional Streaming Client for VTA.

Adapted from the Nova S2S Workshop's s2s_session_manager.py.
Uses aws_sdk_bedrock_runtime for bidirectional audio streaming.

Voice-only: no tool handling. Orchestrator drives flow via reconnect().
Transcript buffer lets orchestrator read what the student said.
"""

import asyncio
import json
import logging
import time
import uuid
import warnings
from typing import Callable, Optional

from vta.orchestrator.s2s_events import S2sEvent

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

# Try to import Bedrock SDK (optional for local testing)
try:
    from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
    from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
    from aws_sdk_bedrock_runtime.config import Config
    from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver
    BEDROCK_SDK_AVAILABLE = True
except ImportError:
    BEDROCK_SDK_AVAILABLE = False
    logger.warning("aws-sdk-bedrock-runtime not installed - Nova Sonic voice features disabled")


class SonicClient:
    """Manages bidirectional streaming with Nova Sonic via Bedrock.

    Voice-only — no tool handling. The orchestrator controls task flow
    via reconnect() with per-task prompts. Student speech is captured
    in a transcript buffer for the orchestrator to read.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "amazon.nova-2-sonic-v1:0",
        audio_output_callback: Optional[Callable] = None,
        transcript_callback: Optional[Callable] = None,
    ):
        self.model_id = model_id
        self.region = region
        self.audio_output_callback = audio_output_callback
        self.transcript_callback = transcript_callback

        # Queues
        self.audio_input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

        # Stream state
        self.stream = None
        self.is_active = False
        self.bedrock_client = None
        self.response_task = None
        self._last_event_time = 0.0  # Updated on every received event; watchdog uses this

        # Session names
        self.prompt_name = None
        self.content_name = None
        self.audio_content_name = None

        # Stored for reconnect
        self._session_id = None
        self._system_prompt = None

        # Transcript buffer — orchestrator reads student speech from here
        # Stores (timestamp, text) tuples so we can filter out narration-era speech
        self._transcript_buffer: list = []
        self._transcript_event = asyncio.Event()

        # Speech completion detection — detect when Sonic stops sending audio
        self._last_audio_output_time = 0.0
        self._speech_done = asyncio.Event()
        self._speech_monitor_task = None

        # All background tasks — cancelled together on reconnect/close
        self._background_tasks: list = []

        # Transcript cooldown — ignore student speech for N seconds after stream setup
        # Prevents stale mic audio from the previous session being re-transcribed
        self._transcript_ready_after = 0.0

        # Playback done — set by frontend signal when browser finishes playing audio
        self._playback_done_event = asyncio.Event()
        self._playback_done_event.set()  # Initially "done" (no audio playing yet)

        # Mic gate — when False, student audio is dropped (Sonic hears only silence).
        # Enabled only during wait_for_student_speech so Sonic can't be interrupted
        # mid-narration by live mic input.
        self._mic_enabled = False

    def _initialize_client(self):
        """Initialize the Bedrock bidirectional streaming client."""
        if not BEDROCK_SDK_AVAILABLE:
            logger.warning("Bedrock SDK not available - running in mock mode")
            return

        self._refresh_credentials()

        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        self.bedrock_client = BedrockRuntimeClient(config=config)

    def _refresh_credentials(self):
        """Refresh IAM role credentials and set as environment variables."""
        import boto3
        import os

        session = boto3.Session(region_name=self.region)
        credentials = session.get_credentials()
        frozen_creds = credentials.get_frozen_credentials()

        os.environ['AWS_ACCESS_KEY_ID'] = frozen_creds.access_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = frozen_creds.secret_key
        if frozen_creds.token:
            os.environ['AWS_SESSION_TOKEN'] = frozen_creds.token

        logger.info("Refreshed AWS credentials from IAM role")

    def reset_session_state(self):
        """Reset session state for a new session."""
        self._drain_queue(self.audio_input_queue)
        self._drain_queue(self.output_queue)
        self.prompt_name = None
        self.content_name = None
        self.audio_content_name = None
        # Reset transcript buffer and speech detection
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self._speech_done.clear()
        self._playback_done_event.clear()
        self._last_audio_output_time = 0.0
        self._mic_enabled = False  # Always start narration mode on new stream

    async def initialize_stream(self):
        """Initialize the bidirectional stream with Bedrock."""
        if not BEDROCK_SDK_AVAILABLE:
            logger.error("=" * 80)
            logger.error("BEDROCK SDK NOT AVAILABLE - Voice features will not work!")
            logger.error("To enable voice:")
            logger.error("  1. Install: pip install aws-sdk-bedrock-runtime smithy-aws-core")
            logger.error("  2. Configure AWS credentials (aws configure)")
            logger.error("=" * 80)
            self.is_active = True
            return self

        # Refresh credentials before starting stream to prevent ExpiredTokenException
        self._refresh_credentials()

        if not self.bedrock_client:
            self._initialize_client()

        try:
            self.stream = await self.bedrock_client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            )
            self.is_active = True

            # Start background tasks — track all for cleanup on reconnect
            self.response_task = asyncio.create_task(self._process_responses())
            t_audio = asyncio.create_task(self._process_audio_input())
            t_watchdog = asyncio.create_task(self._stream_watchdog())
            self._background_tasks.extend([self.response_task, t_audio, t_watchdog])

            await asyncio.sleep(0.1)
            logger.info("Nova Sonic stream initialized successfully")
            return self
        except Exception as e:
            logger.error(f"Failed to initialize Nova Sonic stream: {e}")
            logger.error("Check AWS credentials and region configuration")
            raise

    async def setup_session(self, session_id: str, system_prompt: str = None):
        """
        Send the full session initialization sequence:
        sessionStart -> promptStart -> SYSTEM text -> audio content start -> silence burst.

        The silence burst activates the stream. Sonic speaks proactively when its
        system prompt instructs it to (e.g. "Welcome the student...").
        For later tasks where VAD is needed, the Ready button sends a text kickstart.
        """
        self._session_id = session_id
        self._system_prompt = system_prompt
        self.prompt_name = f"vta-{session_id}"
        self.content_name = f"system-{session_id}"
        self.audio_content_name = f"audio-{session_id}"

        # Reset speech detection for new session
        self._speech_done.clear()
        self._last_audio_output_time = 0.0

        # 1. Session start
        await self.send_event(S2sEvent.session_start())

        # 2. Prompt start (no tool config)
        await self.send_event(S2sEvent.prompt_start(self.prompt_name))

        # 3. System prompt (role=SYSTEM)
        await self.send_event(
            S2sEvent.content_start_text(self.prompt_name, self.content_name, role="SYSTEM")
        )
        await self.send_event(
            S2sEvent.text_input(self.prompt_name, self.content_name, system_prompt)
        )
        await self.send_event(
            S2sEvent.content_end(self.prompt_name, self.content_name)
        )

        # 4. Start audio content (interactive, bidirectional)
        await self.send_event(
            S2sEvent.content_start_audio(self.prompt_name, self.audio_content_name)
        )

        # 5. Send initial silence burst to activate the stream
        import base64 as _b64
        silence_b64 = _b64.b64encode(b'\x00' * 3200).decode('utf-8')
        await self.send_event(
            S2sEvent.audio_input(self.prompt_name, self.audio_content_name, silence_b64)
        )

        # Start speech completion monitor (tracked for cleanup)
        self._speech_monitor_task = asyncio.create_task(self._monitor_speech_completion())
        self._background_tasks.append(self._speech_monitor_task)

        # Ignore student speech for 5s after setup — prevents stale mic audio from
        # being re-transcribed on the new stream
        self._transcript_ready_after = time.time() + 5.0

        logger.info(f"Session {session_id} fully initialized with Sonic (voice-only, no tools)")

    async def send_event(self, event_data: dict):
        """Send a raw event to the Bedrock stream."""
        if not self.is_active:
            logger.warning("Stream not active, cannot send event")
            return

        if not BEDROCK_SDK_AVAILABLE or not self.stream:
            # Mock mode - just log the event
            logger.debug(f"[MOCK] Would send event: {list(event_data.get('event', {}).keys())}")
            return

        event_json = json.dumps(event_data)
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
        )
        await self.stream.input_stream.send(event)

        if "sessionEnd" in event_data.get("event", {}):
            await self.close()

    _mic_drop_log_count = 0  # class-level counter to throttle drop logs

    def add_audio_chunk(self, audio_data: str):
        """Queue an audio chunk (base64 string) from the student.

        Drops audio if stream isn't ready or mic is gated (during narration).
        Mic is only enabled during wait_for_student_speech to prevent Sonic
        from responding conversationally mid-narration.
        """
        if not self.prompt_name or not self.audio_content_name:
            SonicClient._mic_drop_log_count += 1
            if SonicClient._mic_drop_log_count % 100 == 1:
                logger.debug(f"[MIC] Audio dropped — stream not ready (count={SonicClient._mic_drop_log_count})")
            return

        if not self._mic_enabled:
            SonicClient._mic_drop_log_count += 1
            if SonicClient._mic_drop_log_count % 50 == 1:
                logger.info(f"[MIC] Audio dropped — mic gate closed (count={SonicClient._mic_drop_log_count})")
            return

        SonicClient._mic_drop_log_count = 0
        logger.debug(f"[MIC] Audio chunk queued (len={len(audio_data)})")

        self.audio_input_queue.put_nowait({
            "prompt_name": self.prompt_name,
            "content_name": self.audio_content_name,
            "audio_bytes": audio_data,
        })

    def enable_mic(self):
        """Open the mic gate — student audio flows to Sonic (listening mode)."""
        self._mic_enabled = True
        logger.info("Mic enabled — student audio flowing to Sonic")

    def disable_mic(self):
        """Close the mic gate — student audio dropped (narration mode)."""
        self._mic_enabled = False
        logger.info("Mic disabled — Sonic in narration mode")

    # ── Transcript buffer for orchestrator ──────────────────────────────

    async def wait_for_student_speech(self, timeout: float = 120) -> str:
        """Block until student speaks, return transcript text.

        Enables mic on entry (so Sonic hears the student) and disables on exit
        (back to narration mode). This prevents Sonic from being interrupted
        mid-narration by live mic audio.

        Args:
            timeout: Max seconds to wait. 0 = no timeout.

        Returns:
            Accumulated transcript text, or empty string on timeout.
        """
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self.enable_mic()

        try:
            if timeout > 0:
                await asyncio.wait_for(self._transcript_event.wait(), timeout=timeout)
            else:
                await self._transcript_event.wait()
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_student_speech timed out after {timeout}s")
            return ""
        finally:
            self.disable_mic()

        return self.get_and_clear_transcript()

    def get_and_clear_transcript(self) -> str:
        """Get accumulated transcript and clear buffer."""
        text = " ".join(t for _, t in self._transcript_buffer).strip()
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        return text


    # ── Speech completion detection ─────────────────────────────────────

    async def wait_for_speech_done(self, timeout: float = 90):
        """Wait until Sonic finishes speaking (or timeout).

        Clears transcript buffer at start so pre-narration echoes are discarded.
        If Sonic never speaks within timeout, logs a warning and returns so the
        orchestrator can continue (no infinite hang).
        """
        self._transcript_buffer.clear()
        self._transcript_event.clear()
        self._speech_done.clear()

        logger.info(f"Waiting for Sonic to speak (timeout={timeout}s)...")
        try:
            await asyncio.wait_for(self._speech_done.wait(), timeout=timeout)
            logger.info("Sonic finished speaking")
        except asyncio.TimeoutError:
            logger.warning(f"wait_for_speech_done timed out after {timeout}s — Sonic may not have spoken")

    async def wait_for_playback_done(self, timeout: float = 15.0):
        """Wait until the browser signals it has finished playing all queued audio.

        Called after wait_for_speech_done() to ensure the student has heard the
        full narration before the UI changes (slide advance, show_desktop, etc.).
        """
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
        SILENCE_GAP = 2.0  # seconds of no audio output = speech done

        while self.is_active:
            await asyncio.sleep(0.5)

            if self._last_audio_output_time == 0.0:
                continue  # No audio sent yet

            gap = time.time() - self._last_audio_output_time
            if gap >= SILENCE_GAP and not self._speech_done.is_set():
                logger.info(f"Speech done detected ({gap:.1f}s audio gap)")
                self._speech_done.set()

    async def send_text_kickstart(self, text: str = "Please begin."):
        """Send a USER text turn to trigger Sonic to start speaking.

        Follows nova_sonic_with_text.py sample exactly:
        - New UUID content name for each call
        - interactive=True so Sonic treats it as a real user turn
        - Audio content block must already be open and streaming silence
        - Sonic responds with audio output immediately
        """
        if not self.prompt_name or not self.is_active:
            logger.warning("Stream not ready for text kickstart")
            return

        text_content_name = str(uuid.uuid4())
        logger.info(f"Sending text kickstart: '{text}' (content={text_content_name[:8]}...)")

        await self.send_event(
            S2sEvent.content_start_text(self.prompt_name, text_content_name, role="USER", interactive=True)
        )
        await self.send_event(
            S2sEvent.text_input(self.prompt_name, text_content_name, text)
        )
        await self.send_event(
            S2sEvent.content_end(self.prompt_name, text_content_name)
        )

    def inject_audio_clip(self, audio_b64: str):
        """Inject a pre-generated audio clip to wake Sonic's VAD.

        Called when the student clicks the Ready button. Splits the audio
        into 100ms chunks and queues them for sending to Bedrock.
        Sonic hears real speech audio → VAD fires → Sonic starts speaking.
        """
        if not self.prompt_name or not self.audio_content_name:
            logger.warning("Stream not ready for audio injection")
            return

        import base64 as _b64
        audio_bytes = _b64.b64decode(audio_b64)
        chunk_size = 3200  # 100ms at 16kHz 16-bit mono

        chunks_sent = 0
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            if len(chunk) < chunk_size:
                chunk = chunk + b'\x00' * (chunk_size - len(chunk))
            self.audio_input_queue.put_nowait({
                "prompt_name": self.prompt_name,
                "content_name": self.audio_content_name,
                "audio_bytes": _b64.b64encode(chunk).decode('utf-8'),
            })
            chunks_sent += 1

        logger.info(f"Kickstart audio injected: {len(audio_bytes)} bytes, {chunks_sent} chunks")

    # ── Audio input processing ──────────────────────────────────────────

    async def _process_audio_input(self):
        """Consume audio queue and send to Bedrock.

        Sends real mic audio immediately. Only fills with silence after 500ms
        of no mic audio — this keeps the Bedrock connection alive without
        drowning out real speech with silence chunks.

        Key: mic chunks are ~12ms of audio. Old code sent 64ms silence every
        10ms, making speech only 15% of the stream — VAD couldn't trigger.
        Now silence only fills genuine gaps (mic off or student pausing).
        """
        import base64 as _base64
        # 100ms silence chunk — only sent after a real gap in audio
        _silence_b64 = _base64.b64encode(b'\x00' * 3200).decode('utf-8')

        _last_real_audio_time = 0.0
        _SILENCE_AFTER_GAP = 0.5  # seconds of no mic audio before sending silence

        while self.is_active:
            try:
                # Wait up to 100ms for real student audio
                try:
                    data = await asyncio.wait_for(
                        self.audio_input_queue.get(), timeout=0.1
                    )
                    _last_real_audio_time = time.time()
                except asyncio.TimeoutError:
                    # No real audio for 100ms — send silence only if gap > 500ms
                    if self.prompt_name and self.audio_content_name and self.is_active:
                        gap = time.time() - _last_real_audio_time
                        if gap >= _SILENCE_AFTER_GAP:
                            await self.send_event(
                                S2sEvent.audio_input(
                                    self.prompt_name, self.audio_content_name, _silence_b64
                                )
                            )
                    continue

                prompt_name = data.get("prompt_name")
                content_name = data.get("content_name")
                audio_bytes = data.get("audio_bytes")

                if not all([audio_bytes, prompt_name, content_name]):
                    continue

                if isinstance(audio_bytes, bytes):
                    audio_bytes = audio_bytes.decode("utf-8")

                await self.send_event(
                    S2sEvent.audio_input(prompt_name, content_name, audio_bytes)
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing audio input: {e}")
                await asyncio.sleep(0.1)

    # ── Stream health monitoring ────────────────────────────────────────

    async def _stream_watchdog(self):
        """Independently monitors stream health and force-closes if no events arrive.

        asyncio.wait_for() cannot reliably cancel the AWS SDK's await_output() coroutine
        because it uses low-level IO that ignores CancelledError. This watchdog works
        around that by cancelling the entire response_task, which does propagate.
        """
        INACTIVITY_LIMIT = 300  # 5 minutes — only kill on genuine connection failure
        CHECK_EVERY = 5        # check interval

        # Wait until the stream has started receiving events before monitoring
        await asyncio.sleep(CHECK_EVERY)

        while self.is_active:
            await asyncio.sleep(CHECK_EVERY)
            if not self.is_active:
                break

            if self._last_event_time == 0.0:
                continue  # Stream not started yet

            inactive_for = time.time() - self._last_event_time
            if inactive_for > INACTIVITY_LIMIT:
                logger.error(
                    f"Watchdog: no Bedrock events for {inactive_for:.0f}s — force-closing stream"
                )
                # Set inactive FIRST so orchestrator polling detects it
                self.is_active = False
                # Cancel the stuck response_task to unblock await_output()
                if self.response_task and not self.response_task.done():
                    self.response_task.cancel()
                break

        logger.info("Stream watchdog exited")

    # ── Response processing ─────────────────────────────────────────────

    async def _process_responses(self):
        """Process incoming responses from Bedrock.

        Two-phase error handling (separate try/except per AWS SDK call level):
        - await_output() errors  -> break (connection/session level failure)
        - receive() StopAsyncIteration -> continue (chunk ended, session alive)
        - receive() other errors -> break
        The watchdog above handles the case where await_output() hangs and
        cannot be cancelled by asyncio.wait_for.
        """
        consecutive_transient_errors = 0
        MAX_TRANSIENT_ERRORS = 3
        self._last_event_time = time.time()

        while self.is_active:
            # -- Phase 1: wait for next Bedrock event --
            try:
                output = await asyncio.wait_for(
                    self.stream.await_output(), timeout=35.0
                )
            except asyncio.TimeoutError:
                logger.error("await_output() timed out (35s) — stream is dead")
                break
            except StopAsyncIteration:
                logger.info("Stream session ended (StopAsyncIteration from await_output)")
                break
            except Exception as e:
                error_msg = str(e)
                if "unexpected error" in error_msg.lower():
                    consecutive_transient_errors += 1
                    logger.warning(
                        f"Transient Bedrock error #{consecutive_transient_errors}/{MAX_TRANSIENT_ERRORS}: {e}"
                    )
                    if consecutive_transient_errors >= MAX_TRANSIENT_ERRORS:
                        logger.error("Too many transient errors — closing stream")
                        break
                    await asyncio.sleep(1.0)
                    continue
                else:
                    logger.error(f"Fatal stream error: {e}")
                    break

            # -- Phase 2: receive event payload --
            try:
                result = await output[1].receive()
            except StopAsyncIteration:
                # Empty chunk — normal, stream continues
                continue
            except Exception as e:
                error_msg = str(e)
                if "unexpected error" in error_msg.lower():
                    consecutive_transient_errors += 1
                    logger.warning(
                        f"Transient payload error #{consecutive_transient_errors}/{MAX_TRANSIENT_ERRORS}: {e}"
                    )
                    if consecutive_transient_errors >= MAX_TRANSIENT_ERRORS:
                        logger.error("Too many transient payload errors — closing stream")
                        break
                    continue  # Try to recover
                else:
                    logger.error(f"Fatal payload error: {e}")
                    break

            # Successful receive — reset error counter and update watchdog timer
            consecutive_transient_errors = 0
            self._last_event_time = time.time()

            if not (result.value and result.value.bytes_):
                continue

            # -- Phase 3: parse and dispatch event --
            try:
                response_data = result.value.bytes_.decode("utf-8")
                json_data = json.loads(response_data)
                json_data["timestamp"] = int(time.time() * 1000)

                if "event" in json_data:
                    event_name = list(json_data["event"].keys())[0]
                    await self._handle_event(event_name, json_data)

                await self.output_queue.put(json_data)

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                continue  # Bad payload, stream may still be alive
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                continue  # Processing error, don't kill stream

        self.is_active = False
        logger.info("Sonic stream loop exited — is_active=False")

    async def _handle_event(self, event_name: str, json_data: dict):
        """Handle specific Sonic response events (voice-only, no tools)."""
        if event_name not in ("audioOutput", "textOutput"):
            logger.info(f"[SONIC EVENT] Received: {event_name}")
        event_data = json_data["event"]

        # Audio output — forward to student + track for speech completion
        if event_name == "audioOutput" and self.audio_output_callback:
            audio_data = event_data["audioOutput"]
            if isinstance(audio_data, dict):
                audio_content = audio_data.get("content", audio_data)
            else:
                audio_content = audio_data

            self._last_audio_output_time = time.time()
            self._speech_done.clear()  # Reset — still speaking
            await self.audio_output_callback(audio_content)

        # Text output (transcript) — forward to frontend + buffer for orchestrator
        elif event_name == "textOutput":
            text_data = event_data["textOutput"]
            if isinstance(text_data, dict):
                text_content = text_data.get("content", "") or text_data.get("text", "")
                text_role = text_data.get("role", "ASSISTANT")
            else:
                text_content = str(text_data)
                text_role = "ASSISTANT"

            # Only buffer USER-role text (student speech) for orchestrator
            # ASSISTANT-role text is ARIA speaking — don't capture it as student input
            # Also skip the cooldown window to avoid stale audio echo on new streams
            if text_content.strip() and text_role == "USER":
                if time.time() >= self._transcript_ready_after:
                    self._transcript_buffer.append((time.time(), text_content))
                    self._transcript_event.set()
                    logger.info(f"[SONIC TRANSCRIPT] Student said: {text_content[:100]}")
                else:
                    logger.info(f"[SONIC TRANSCRIPT] Cooldown — ignoring echo: {text_content[:80]}")

            if self.transcript_callback:
                await self.transcript_callback(text_content, text_role)

        else:
            logger.debug(f"[SONIC EVENT] Unhandled event: {event_name}")

    # ── Reconnect ───────────────────────────────────────────────────────

    async def reconnect(self, resume_context: str = "", prompt_override: str = "") -> bool:
        """Tear down the dead stream and create a fresh one.

        Args:
            resume_context: Extra instruction appended to the stored system prompt.
            prompt_override: If provided, replaces the system prompt entirely
                             (used for per-task prompts).

        Returns:
            True if reconnect succeeded, False otherwise.
        """
        if not self._session_id:
            logger.error("Cannot reconnect — no stored session ID")
            return False

        logger.info("Reconnecting Bedrock stream...")

        # -- Tear down the dead stream --
        self.is_active = False
        # Brief pause so awscrt can finish delivering any in-flight _on_body callbacks
        # before we close the stream. Without this, awscrt raises InvalidStateError
        # (CANCELLED Future) which can briefly destabilize the new stream's connection.
        await asyncio.sleep(0.3)
        if self.stream:
            try:
                await self.stream.input_stream.close()
            except Exception:
                pass
        self.stream = None

        # Cancel ALL background tasks (response, audio input, watchdog, speech monitor)
        all_tasks = list(self._background_tasks)
        if self._speech_monitor_task and self._speech_monitor_task not in all_tasks:
            all_tasks.append(self._speech_monitor_task)
        for task in all_tasks:
            if not task.done():
                task.cancel()
        for task in all_tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._background_tasks.clear()
        self.response_task = None
        self._speech_monitor_task = None
        self._last_event_time = 0.0
        self.reset_session_state()

        # -- Create a fresh stream --
        try:
            self._refresh_credentials()
            self._initialize_client()
            await self.initialize_stream()

            if prompt_override:
                prompt = prompt_override
            else:
                prompt = self._system_prompt or ""
                if resume_context:
                    prompt += f"\n\n{resume_context}"

            await self.setup_session(self._session_id, prompt)
            logger.info("Stream reconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            self.is_active = False
            return False

    # ── Cleanup ─────────────────────────────────────────────────────────

    async def close(self):
        """Close the stream and clean up."""
        if not self.is_active:
            return

        self.is_active = False
        self._drain_queue(self.audio_input_queue)
        self._drain_queue(self.output_queue)
        self.reset_session_state()

        if self.stream:
            try:
                await self.stream.input_stream.close()
            except Exception as e:
                logger.debug(f"Error closing stream: {e}")
        self.stream = None

        # Cancel ALL background tasks
        all_tasks = list(self._background_tasks)
        if self._speech_monitor_task and self._speech_monitor_task not in all_tasks:
            all_tasks.append(self._speech_monitor_task)
        for task in all_tasks:
            if not task.done():
                task.cancel()
        for task in all_tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._background_tasks.clear()
        self.response_task = None
        self._speech_monitor_task = None
        logger.info("Sonic client closed")

    @staticmethod
    def _drain_queue(q: asyncio.Queue):
        """Empty a queue without blocking."""
        while not q.empty():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                break
