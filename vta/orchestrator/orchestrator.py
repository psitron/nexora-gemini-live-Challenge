"""
Core Tutorial Execution Loop.

Proactive orchestrator-driven loop: each task reconnects Sonic with a
per-task prompt that ends with a confirmation question. After speech done,
we wait_for_student_speech on the SAME stream — no extra reconnect needed.
Only reconnect when the student asks a question or wants a repeat.
"""

import asyncio
import logging
import os
import subprocess
from typing import Callable, Optional

from vta.orchestrator.gemini_live_client import GeminiLiveClient as SonicClient
from vta.orchestrator.agent_s3_client import AgentS3Client
from vta.orchestrator.brain_client import BrainClient, is_simple_yes
from vta.orchestrator.confirmation import ConfirmationManager
from vta.orchestrator.curriculum_manager import get_curriculum_manager
from vta.orchestrator.session_state import get_session_state_manager
from vta.orchestrator.execution_mode import ExecutionMode, ExecutionConfig
from vta.orchestrator.vision_loop import VisionLoop
from vta.orchestrator.desktop_vision_loop import DesktopVisionLoop

logger = logging.getLogger(__name__)

def _extract_goal_text(task: dict) -> str:
    """Extract all goal text from a task and its subtasks."""
    parts = []
    if task.get("goal"):
        parts.append(task["goal"])
    for sub in task.get("subtasks", []):
        if sub.get("goal"):
            parts.append(sub["goal"])
    return " ".join(parts).lower()


def _is_browser_task(goal_text: str) -> bool:
    """Check if goal involves browser/web interaction."""
    browser_keywords = [
        "http://", "https://", "localhost", "127.0.0.1",
        "browser", "firefox", "chrome", "chromium",
        "jupyter", "notebook", "webpage", "website",
        "navigate to", "open url",
    ]
    return any(kw in goal_text for kw in browser_keywords)


# Slide explanation cache — prefetched in background
_slide_cache: dict[str, str] = {}  # key: "pdf_key:page_num" → explanation text
_slide_cache_tasks: dict[str, asyncio.Task] = {}  # background prefetch tasks

# Lazily initialised so imports don't fail if core/ deps are missing at startup
_vision_loop: Optional[VisionLoop] = None
_desktop_vision_loop: Optional[DesktopVisionLoop] = None


def _get_vision_loop() -> VisionLoop:
    global _vision_loop
    if _vision_loop is None:
        _vision_loop = VisionLoop()
    return _vision_loop


def _get_desktop_vision_loop() -> DesktopVisionLoop:
    global _desktop_vision_loop
    if _desktop_vision_loop is None:
        _desktop_vision_loop = DesktopVisionLoop()
    return _desktop_vision_loop


async def _reset_desktop_session():
    """
    Reset the XFCE desktop session by killing it and starting a fresh one.
    Runs via subprocess (not Agent S3) since the orchestrator is on the same machine.
    This closes all user windows (terminals, editors, browsers) and gives a clean desktop.
    Xvfb, VNC, and all VTA services remain untouched.
    """
    env = {**os.environ, "DISPLAY": ":1"}
    try:
        # Kill the XFCE session — this closes all windows under it
        logger.info("Resetting desktop: killing xfce4-session...")
        subprocess.run(["pkill", "-f", "xfce4-session"], env=env, timeout=5,
                        capture_output=True)
        await asyncio.sleep(2)  # Give it a moment to fully shut down

        # Start a fresh XFCE session
        logger.info("Resetting desktop: starting fresh xfce4-session...")
        subprocess.Popen(["startxfce4"], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(3)  # Wait for desktop to be ready
        logger.info("Desktop reset complete — clean session running")
    except Exception as e:
        logger.warning(f"Desktop reset failed (non-fatal): {e}")


async def run_tutorial(
    tutorial_id: str,
    session_id: str,
    sonic: SonicClient,
    agent: AgentS3Client,
    brain: BrainClient,
    confirmation_mgr: ConfirmationManager,
    ws_send: Callable,
    exec_config: ExecutionConfig = None,
):
    """Main loop - runs the full tutorial from start to finish."""
    curriculum = get_curriculum_manager()
    state = get_session_state_manager()

    tutorial = curriculum.load_tutorial(tutorial_id)
    tasks = tutorial["tasks"]

    await state.create_session(session_id, tutorial_id, "student")

    await ws_send({
        "event": "tutorial_loaded",
        "tutorial_id": tutorial_id,
        "title": tutorial["title"],
        "pdf_s3_key": tutorial.get("pdf_s3_key", ""),
        "pdf_url": tutorial.get("pdf_url", ""),
        "task_count": len(tasks),
    })

    mode = exec_config.mode if exec_config else ExecutionMode.DEMO_ONLY
    logger.info(f"Starting tutorial '{tutorial_id}' in mode: {mode.value}")

    # Prefetch first slide while welcome plays
    pdf_key = tutorial.get("pdf_s3_key", "")
    first_theory = next((t for t in tasks if t["type"] == "theory" and t.get("slide_number")), None)
    if first_theory and pdf_key:
        _start_prefetch(brain, pdf_key, first_theory["slide_number"])

    # Welcome — reconnect with welcome prompt, wait for student to say ready
    desc = tutorial.get('description', 'you will learn key concepts')
    welcome_prompt = (
        f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything: "
        f"Welcome to {tutorial['title']}. {desc}. "
        f"Say ready when you want to begin."
    )
    await sonic.reconnect(prompt_override=welcome_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=60)
    await sonic.wait_for_playback_done(timeout=15)
    await ws_send({"event": "aria_listening"})
    # Wait for "ready" on the SAME welcome stream — no reconnect
    welcome_transcript = await sonic.wait_for_student_speech(timeout=120)
    logger.info(f"Student welcome response: '{welcome_transcript}'")

    # Execute each task
    for i, task in enumerate(tasks):
        task_num = i + 1
        logger.info("=" * 60)
        logger.info(f"TASK {task_num}/{len(tasks)}: {task['task_id']} - {task['title']} ({task['type']})")
        logger.info("=" * 60)

        await state.update_state(session_id, task["task_id"], None, "running")
        await ws_send({"event": "task_started", "task_id": task["task_id"], "task": task})

        is_last = (i == len(tasks) - 1)

        if task["type"] == "theory":
            # Prefetch NEXT theory slide while this one is being explained
            for next_task in tasks[i+1:]:
                if next_task["type"] == "theory" and next_task.get("slide_number") and pdf_key:
                    _start_prefetch(brain, pdf_key, next_task["slide_number"])
                    break

            transcript = await execute_theory_task(
                task, sonic, brain, ws_send, is_last,
                pdf_key=pdf_key,
            )
        elif task["type"] == "practical":
            transcript = await execute_practical_task(
                task, sonic, agent, brain, ws_send, exec_config, is_last
            )
        elif task["type"] in ("vision", "vision_driven", "desktop_vision"):
            # Auto-detect: browser vs desktop based on goal content
            goal_text = _extract_goal_text(task)
            if _is_browser_task(goal_text):
                logger.info(f"Auto-detected: BROWSER vision (goal contains URL/web keywords)")
                transcript = await execute_vision_task(task, sonic, agent, brain, ws_send, is_last)
            else:
                logger.info(f"Auto-detected: DESKTOP vision (no browser keywords)")
                transcript = await execute_desktop_vision_task(task, sonic, agent, brain, ws_send, is_last)
        else:
            transcript = ""

        await state.update_state(session_id, task["task_id"], None, "completed")
        await ws_send({"event": "task_completed", "task_id": task["task_id"]})

        # Classify student response and handle questions/repeats
        # (skip for last task — no need to confirm after final task)
        if not is_last:
            task_context = f"Task: {task['title']} ({task['type']})"
            await handle_student_response(transcript, task, task_context, sonic, brain, ws_send)

    # Tutorial complete
    complete_prompt = "You are Nexora. Tell the student they've completed the tutorial. Congratulate them briefly."
    await sonic.reconnect(prompt_override=complete_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=30)

    # Close Playwright browser if it was used during the session
    global _vision_loop
    if _vision_loop is not None:
        try:
            await _vision_loop.close()
        except Exception as e:
            logger.warning(f"Vision loop cleanup failed (non-fatal): {e}")
        _vision_loop = None

    # Reset the Linux desktop by restarting the XFCE session directly via subprocess.
    # This kills all windows (terminals, editors, browsers) and gives a clean desktop.
    # No Agent S3 involved — orchestrator runs on the same machine.
    await _reset_desktop_session()

    await state.end_session(session_id)
    await ws_send({"event": "session_complete", "tutorial_id": tutorial_id})
    logger.info(f"Tutorial {tutorial_id} completed for session {session_id}")


async def _prefetch_slide(brain: BrainClient, pdf_key: str, slide_number: int):
    """Background task: analyze a slide and cache the explanation."""
    from vta.orchestrator.pdf_utils import get_pdf_path, extract_slide_image

    cache_key = f"{pdf_key}:{slide_number}"
    if cache_key in _slide_cache:
        return  # Already cached

    pdf_path = get_pdf_path(pdf_key)
    if not pdf_path:
        return

    slide_image = extract_slide_image(pdf_path, slide_number)
    if not slide_image:
        return

    logger.info(f"[PREFETCH] Analyzing slide {slide_number} in background...")
    explanation = await brain.explain_slide(slide_image)
    _slide_cache[cache_key] = explanation
    logger.info(f"[PREFETCH] Slide {slide_number} cached ({len(explanation)} chars)")


def _start_prefetch(brain: BrainClient, pdf_key: str, slide_number: int):
    """Start prefetching a slide explanation in the background."""
    if not pdf_key or not slide_number:
        return
    cache_key = f"{pdf_key}:{slide_number}"
    if cache_key in _slide_cache or cache_key in _slide_cache_tasks:
        return
    task = asyncio.create_task(_prefetch_slide(brain, pdf_key, slide_number))
    _slide_cache_tasks[cache_key] = task


async def execute_theory_task(
    task: dict,
    sonic: SonicClient,
    brain: BrainClient,
    ws_send: Callable,
    is_last: bool = False,
    pdf_key: str = "",
) -> str:
    """
    Theory task: show slide to student, send slide IMAGE to Gemini so it
    can SEE and explain it naturally. Falls back to text if no PDF.

    Returns:
        Student's spoken response transcript.
    """
    from vta.orchestrator.pdf_utils import get_pdf_path, extract_slide_image

    slide_number = task.get("slide_number")
    if slide_number:
        await ws_send({"event": "show_slide", "page": slide_number})

    # Try to extract slide as image for vision-based explanation
    slide_image = None
    if pdf_key and slide_number:
        pdf_path = get_pdf_path(pdf_key)
        if pdf_path:
            slide_image = extract_slide_image(pdf_path, slide_number)
            if slide_image:
                logger.info(f"[THEORY] {task['task_id']} — sending slide {slide_number} image to Gemini ({len(slide_image)} bytes)")

    closing = (
        "After explaining, ask: 'Any questions, or say ready to move on.'"
        if not is_last
        else ""
    )

    if slide_image:
        # Check cache first (may have been prefetched)
        cache_key = f"{pdf_key}:{slide_number}"
        if cache_key in _slide_cache:
            explanation = _slide_cache.pop(cache_key)
            logger.info(f"[THEORY] Using CACHED explanation for slide {slide_number} ({len(explanation)} chars)")
        else:
            # Wait for prefetch if in progress
            if cache_key in _slide_cache_tasks:
                logger.info(f"[THEORY] Waiting for prefetch of slide {slide_number}...")
                await _slide_cache_tasks[cache_key]
                _slide_cache_tasks.pop(cache_key, None)
                explanation = _slide_cache.pop(cache_key, "")
            else:
                # No prefetch — analyze now
                logger.info(f"[THEORY] Analyzing slide {slide_number} (no prefetch)...")
                explanation = await brain.explain_slide(slide_image, task.get("title", ""))

        if not explanation:
            explanation = f"This slide covers: {task.get('title', 'the topic')}."

        logger.info(f"[THEORY] Explanation ({len(explanation)} chars): {explanation[:200]}")
        prompt = f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything:\n\n{explanation}\n\n{closing}"
    else:
        # Fallback: use text context if no image available
        context = task.get("slide_context", "") or f"This slide covers: {task['title']}."
        if len(context) > 1200:
            context = context[:1200] + "..."
        prompt = f"Explain the following to the student:\n\n{context}\n\n{closing}"

    await ws_send({"event": "aria_thinking"})
    await sonic.reconnect(prompt_override=prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=90)
    await sonic.wait_for_playback_done(timeout=15)
    logger.info(f"Theory task {task['task_id']} narration complete — listening")
    await ws_send({"event": "aria_listening"})

    transcript = await sonic.wait_for_student_speech(timeout=120)
    logger.info(f"Student response after {task['task_id']}: '{transcript}'")
    return transcript


async def execute_practical_task(
    task: dict,
    sonic: SonicClient,
    agent: AgentS3Client,
    brain: BrainClient,
    ws_send: Callable,
    exec_config: ExecutionConfig = None,
    is_last: bool = False,
) -> str:
    """
    Practical task: intro narration → execute actions → summary narration.
    Returns student's spoken response from the summary stream.
    """
    mode = exec_config.mode if exec_config else ExecutionMode.DEMO_ONLY

    await ws_send({"event": "show_desktop"})

    subtasks = task.get("subtasks", [])
    subtask_names = [s["title"] for s in subtasks]

    # 1. Intro narration — use exact sonic_prompt from curriculum
    task_sonic_prompt = task.get("sonic_prompt", "")
    if not task_sonic_prompt:
        task_sonic_prompt = "Watch your screen."

    intro_prompt = (
        f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything:\n\n{task_sonic_prompt}"
    )

    await sonic.reconnect(prompt_override=intro_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=45)

    # 2. Execute subtask actions — narrate BEFORE each action
    for j, subtask in enumerate(subtasks):
        subtask_id = subtask["subtask_id"]
        action = subtask.get("action")
        params = subtask.get("params", {})
        sonic_prompt = subtask.get("sonic_prompt", "") or subtask["title"]

        await ws_send({"event": "subtask_started", "subtask_id": subtask_id})

        step_narration_prompt = (
            f"You are Nexora. Read ONLY the following words exactly as written. "
            f"Do not add, change, or expand:\n\n{sonic_prompt}"
        )
        await sonic.reconnect(prompt_override=step_narration_prompt)
        await sonic.send_text_kickstart("Please begin.")
        await sonic.wait_for_speech_done(timeout=30)
        await sonic.wait_for_playback_done(timeout=10)

        # Execute the action after narration
        if action:
            logger.info(f"Executing {subtask_id}: {action} {params}")
            result = await agent.run(action=action, params=params)
            logger.info(f"Subtask {subtask_id} result: {result}")

        await ws_send({"event": "subtask_completed", "subtask_id": subtask_id})

        if mode == ExecutionMode.FOLLOW_ALONG_PACED:
            step_prompt = (
                f"You are Nexora. Read ONLY the following words exactly as written. "
                f"Do not add, change, or expand:\n\n"
                f"Your turn. Try it on your computer. Say ready when done."
            )
            await sonic.reconnect(prompt_override=step_prompt)
            await sonic.send_text_kickstart("Please begin.")
            await sonic.wait_for_speech_done(timeout=30)
            step_transcript = await sonic.wait_for_student_speech(timeout=120)
            logger.info(f"Student response after subtask {subtask_id}: '{step_transcript}'")
        elif j < len(subtasks) - 1:
            await asyncio.sleep(0.5)

    # 3. Summary narration — minimal, exact words only
    closing = "Any questions, or say ready to continue." if not is_last else ""
    summary_prompt = (
        f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything:\n\n"
        f"That completes the demonstration. {closing}"
    )
    await ws_send({"event": "aria_thinking"})
    await sonic.reconnect(prompt_override=summary_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=30)
    await sonic.wait_for_playback_done(timeout=15)
    await ws_send({"event": "aria_listening"})

    # Listen on the SAME stream — no extra reconnect
    transcript = await sonic.wait_for_student_speech(timeout=120)
    logger.info(f"Student response after practical {task['task_id']}: '{transcript}'")
    return transcript


async def execute_desktop_vision_task(
    task: dict,
    sonic: SonicClient,
    agent: AgentS3Client,
    brain: BrainClient,
    ws_send: Callable,
    is_last: bool = False,
) -> str:
    """
    Desktop vision task: AI sees the desktop screen via Agent S3 screenshots
    and interacts with any desktop application (file manager, terminal, etc.)
    using pyautogui/xdotool through Agent S3.

    Curriculum format:
        {
            "type": "desktop_vision",
            "title": "...",
            "goal": "Open the file manager and navigate to /home",
            "sonic_prompt": "Watch as I navigate the desktop."
        }
    """
    subtasks = task.get("subtasks", [])
    sonic_intro = task.get("sonic_prompt") or f"Watch carefully. I will now demonstrate {task.get('title', 'this task')}."

    await ws_send({"event": "show_desktop"})

    # Intro narration
    intro_prompt = f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything:\n\n{sonic_intro}"
    await sonic.reconnect(prompt_override=intro_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=30)

    desktop_loop = _get_desktop_vision_loop()

    if subtasks:
        for subtask in subtasks:
            subtask_id = subtask["subtask_id"]
            subtask_goal = subtask.get("goal", subtask["title"])

            await ws_send({"event": "subtask_started", "subtask_id": subtask_id})

            # Skip per-subtask narration — go straight to action (faster)
            logger.info(f"Desktop vision: {subtask_id} — {subtask_goal}")
            result = await desktop_loop.run(goal=subtask_goal, agent=agent, ws_send=ws_send)
            logger.info(f"Subtask {subtask_id}: success={result.success} — {result.message}")

            await ws_send({"event": "subtask_completed", "subtask_id": subtask_id})
    else:
        goal = task.get("goal", task.get("title", "complete the task"))
        logger.info(f"Desktop vision: {goal}")
        result = await desktop_loop.run(goal=goal, agent=agent, ws_send=ws_send)

    # Summary
    closing = "Any questions, or say ready to continue." if not is_last else ""
    summary_prompt = (
        f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything:\n\n"
        f"That completes the demonstration. {closing}"
    )
    await ws_send({"event": "aria_thinking"})
    await sonic.reconnect(prompt_override=summary_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=30)
    await ws_send({"event": "aria_listening"})

    transcript = await sonic.wait_for_student_speech(timeout=120)
    logger.info(f"Student response after desktop vision {task.get('task_id')}: '{transcript}'")
    return transcript


async def execute_vision_task(
    task: dict,
    sonic: SonicClient,
    agent: AgentS3Client,
    brain: BrainClient,
    ws_send: Callable,
    is_last: bool = False,
) -> str:
    """
    Vision-driven task: Nexora narrates the goal, the autonomous vision loop
    executes it by watching the screen and deciding actions, then Nexora
    narrates the outcome and waits for the student.

    Curriculum format:
        {
            "type": "vision_driven",
            "title": "...",
            "goal": "Open Firefox and navigate to google.com",
            "sonic_prompt": "Watch as I demonstrate this."   # optional
        }
    """
    subtasks = task.get("subtasks", [])
    sonic_intro = task.get("sonic_prompt") or f"Watch carefully. I will now demonstrate {task.get('title', 'this task')}."

    await ws_send({"event": "show_desktop"})

    # 1. Task intro narration
    intro_prompt = (
        f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything:\n\n{sonic_intro}"
    )
    await sonic.reconnect(prompt_override=intro_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=30)
    await sonic.wait_for_playback_done(timeout=10)

    vision_loop = _get_vision_loop()

    if subtasks:
        # 2a. Run each subtask: narrate then vision loop
        for subtask in subtasks:
            subtask_id = subtask["subtask_id"]
            subtask_goal = subtask.get("goal", subtask["title"])
            subtask_prompt = subtask.get("sonic_prompt", subtask["title"])

            await ws_send({"event": "subtask_started", "subtask_id": subtask_id})

            narration_prompt = (
                f"You are Nexora. Read ONLY the following words exactly as written. "
                f"Do not add, change, or expand:\n\n{subtask_prompt}"
            )
            await sonic.reconnect(prompt_override=narration_prompt)
            await sonic.send_text_kickstart("Please begin.")
            await sonic.wait_for_speech_done(timeout=30)
            await sonic.wait_for_playback_done(timeout=10)

            logger.info(f"Vision loop for subtask {subtask_id}: {subtask_goal}")
            result = await vision_loop.run(goal=subtask_goal, agent=agent, ws_send=ws_send)
            logger.info(f"Subtask {subtask_id} result: success={result.success} — {result.message}")

            await ws_send({"event": "subtask_completed", "subtask_id": subtask_id})
    else:
        # 2b. Single goal (no subtasks) — original behaviour
        goal = task.get("goal", task.get("title", "complete the task"))
        logger.info(f"Starting vision loop for goal: {goal}")
        result = await vision_loop.run(goal=goal, agent=agent, ws_send=ws_send)

    # 3. Summary narration
    closing = "Any questions, or say ready to continue." if not is_last else ""
    summary_prompt = (
        f"Speak ONLY these exact words, nothing more. Do not elaborate, ask questions, or add anything:\n\n"
        f"That completes the demonstration. {closing}"
    )
    await ws_send({"event": "aria_thinking"})
    await sonic.reconnect(prompt_override=summary_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=30)
    await sonic.wait_for_playback_done(timeout=15)
    await ws_send({"event": "aria_listening"})

    transcript = await sonic.wait_for_student_speech(timeout=120)
    logger.info(f"Student response after vision task {task.get('task_id')}: '{transcript}'")
    return transcript


async def sonic_speak(sonic: SonicClient, prompt: str, timeout: int = 60, retries: int = 3):
    """
    Reconnect Sonic with a prompt and wait until it finishes speaking.
    Retries up to `retries` times if Sonic fails to start (VAD issue).
    Only advances when Sonic actually spoke — never silently skips.
    """
    for attempt in range(retries):
        await sonic.reconnect(prompt_override=prompt)
        await sonic.send_text_kickstart("Please begin.")
        await sonic.wait_for_speech_done(timeout=timeout)
        if sonic._last_audio_output_time > 0:
            return  # Sonic spoke — success
        logger.warning(f"Sonic didn't speak (attempt {attempt + 1}/{retries}) — retrying")

    logger.error("Sonic failed to speak after all retries")


async def handle_student_response(
    transcript: str,
    task: dict,
    task_context: str,
    sonic: SonicClient,
    brain: BrainClient,
    ws_send: Callable,
):
    """
    Loop until student says ready to move on.
    Handles unlimited questions — never advances on timeout alone.
    """
    # Empty transcript means Sonic stream died and student never spoke.
    # Don't silently advance — wait for student to actually respond.
    if not transcript:
        logger.info("No student response — waiting for student to speak")
        transcript = await sonic.wait_for_student_speech(timeout=0)  # no timeout
        if not transcript:
            return

    while True:
        # Simple yes/ready → done, move to next task
        if is_simple_yes(transcript):
            logger.info(f"Student confirmed ('{transcript}') — moving to next task")
            return

        intent = await brain.classify_intent(transcript, task_context)
        action = intent.get("action", "continue")
        logger.info(f"Brain intent for '{transcript[:60]}': {intent}")

        if action in ("continue", "skip"):
            return

        elif action == "question":
            question_text = intent.get("question_text") or transcript
            answer = await brain.answer_question(question_text, task_context)
            answer_prompt = (
                f"You are Nexora. Answer this question: {answer}\n"
                f"Then ask: 'Any more questions or ready to move on?' Then listen."
            )
            await ws_send({"event": "aria_thinking"})
            await sonic_speak(sonic, answer_prompt, timeout=45)
            await ws_send({"event": "aria_listening"})
            transcript = await sonic.wait_for_student_speech(timeout=0)  # no timeout

        elif action == "repeat":
            logger.info(f"Student requested repeat of {task['task_id']}")
            # Re-read the full slide content, not just a summary
            slide_context = task.get("slide_context", "") or task.get("title", "")
            if len(slide_context) > 1200:
                slide_context = slide_context[:1200] + "..."
            repeat_prompt = (
                f"You are Nexora. The student wants to hear this again. "
                f"Read the following content clearly:\n\n{slide_context}\n\n"
                f"Then ask: 'Any questions or ready to move on?' Then listen."
            )
            await ws_send({"event": "aria_thinking"})
            await sonic_speak(sonic, repeat_prompt, timeout=45)
            await ws_send({"event": "aria_listening"})
            transcript = await sonic.wait_for_student_speech(timeout=0)  # no timeout

        elif action == "wait":
            logger.info("Student needs more time — waiting for them to speak")
            wait_prompt = "You are Nexora. Say: 'Take your time.' Then listen."
            await sonic_speak(sonic, wait_prompt, timeout=20)
            await ws_send({"event": "aria_listening"})
            transcript = await sonic.wait_for_student_speech(timeout=0)  # no timeout

        else:
            return
