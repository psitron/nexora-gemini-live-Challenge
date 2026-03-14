"""
Core Tutorial Execution Loop.

Proactive orchestrator-driven loop: each task reconnects Sonic with a
per-task prompt that ends with a confirmation question. After speech done,
we wait_for_student_speech on the SAME stream — no extra reconnect needed.
Only reconnect when the student asks a question or wants a repeat.
"""

import asyncio
import logging
from typing import Callable, Optional

from vta.orchestrator.gemini_live_client import GeminiLiveClient as SonicClient
from vta.orchestrator.agent_s3_client import AgentS3Client
from vta.orchestrator.brain_client import BrainClient, is_simple_yes
from vta.orchestrator.confirmation import ConfirmationManager
from vta.orchestrator.curriculum_manager import get_curriculum_manager
from vta.orchestrator.session_state import get_session_state_manager
from vta.orchestrator.execution_mode import ExecutionMode, ExecutionConfig
from vta.orchestrator.vision_loop import VisionLoop

logger = logging.getLogger(__name__)

# Lazily initialised so imports don't fail if core/ deps are missing at startup
_vision_loop: Optional[VisionLoop] = None


def _get_vision_loop() -> VisionLoop:
    global _vision_loop
    if _vision_loop is None:
        _vision_loop = VisionLoop()
    return _vision_loop


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

    # Welcome — reconnect with welcome prompt, wait for student to say ready
    welcome_prompt = (
        f"You are ARIA, a voice tutor. Read this exactly: "
        f"'Welcome to {tutorial['title']}. In this course, {tutorial.get('description', 'you will learn key concepts')}. "
        f"Say ready when you want to begin.' Then stop talking and listen."
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
            transcript = await execute_theory_task(task, sonic, brain, ws_send, is_last)
        elif task["type"] == "practical":
            transcript = await execute_practical_task(
                task, sonic, agent, brain, ws_send, exec_config, is_last
            )
        elif task["type"] == "vision_driven":
            transcript = await execute_vision_task(task, sonic, agent, brain, ws_send, is_last)
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
    complete_prompt = "You are ARIA. Tell the student they've completed the tutorial. Congratulate them briefly."
    await sonic.reconnect(prompt_override=complete_prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=30)

    await state.end_session(session_id)
    await ws_send({"event": "session_complete", "tutorial_id": tutorial_id})
    logger.info(f"Tutorial {tutorial_id} completed for session {session_id}")


async def execute_theory_task(
    task: dict,
    sonic: SonicClient,
    brain: BrainClient,
    ws_send: Callable,
    is_last: bool = False,
) -> str:
    """
    Theory task: reconnect with narration prompt, wait for speech done,
    then wait for student response on the SAME stream (no extra reconnect).

    Returns:
        Student's spoken response transcript.
    """
    await ws_send({"event": "show_slide", "page": task["slide_number"]})

    context = task.get("slide_context", "") or ""
    logger.info(f"[THEORY] {task['task_id']} slide_context ({len(context)} chars): {context[:200]}")

    if not context:
        context = f"This slide covers: {task['title']}. Explain it clearly."

    if len(context) > 1200:
        context = context[:1200] + "..."

    closing = (
        "Then ask: 'Any questions, or say ready to move on.' Then listen."
        if not is_last
        else ""
    )

    prompt = (
        f"You are ARIA, a voice tutor reading slides to a student. "
        f"Your ONLY job is to read the following text word-for-word. "
        f"Do NOT add your own words. Do NOT explain further. Do NOT teach beyond what is written. "
        f"Simply read this text aloud exactly as written:\n\n"
        f'"{context}"\n\n'
        f"{closing}"
    )

    await ws_send({"event": "aria_thinking"})
    await sonic.reconnect(prompt_override=prompt)
    await sonic.send_text_kickstart("Please begin.")
    await sonic.wait_for_speech_done(timeout=90)
    await sonic.wait_for_playback_done(timeout=15)
    logger.info(f"Theory task {task['task_id']} narration complete — listening for student")
    await ws_send({"event": "aria_listening"})

    # Listen on the SAME stream — Sonic already asked the question at the end
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
        f"You are ARIA. Read ONLY the following words exactly as written. "
        f"Do not add, change, or expand:\n\n{task_sonic_prompt}"
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
            f"You are ARIA. Read ONLY the following words exactly as written. "
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
                f"You are ARIA. Read ONLY the following words exactly as written. "
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
        f"You are ARIA. Read ONLY the following words exactly as written. "
        f"Do not add, change, or expand:\n\n"
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


async def execute_vision_task(
    task: dict,
    sonic: SonicClient,
    agent: AgentS3Client,
    brain: BrainClient,
    ws_send: Callable,
    is_last: bool = False,
) -> str:
    """
    Vision-driven task: ARIA narrates the goal, the autonomous vision loop
    executes it by watching the screen and deciding actions, then ARIA
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
        f"You are ARIA. Read ONLY the following words exactly as written. "
        f"Do not add, change, or expand:\n\n{sonic_intro}"
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
                f"You are ARIA. Read ONLY the following words exactly as written. "
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
        f"You are ARIA. Read ONLY the following words exactly as written. "
        f"Do not add, change, or expand:\n\n"
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
                f"You are ARIA. Answer this question: {answer}\n"
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
                f"You are ARIA. The student wants to hear this again. "
                f"Read the following content clearly:\n\n{slide_context}\n\n"
                f"Then ask: 'Any questions or ready to move on?' Then listen."
            )
            await ws_send({"event": "aria_thinking"})
            await sonic_speak(sonic, repeat_prompt, timeout=45)
            await ws_send({"event": "aria_listening"})
            transcript = await sonic.wait_for_student_speech(timeout=0)  # no timeout

        elif action == "wait":
            logger.info("Student needs more time — waiting for them to speak")
            wait_prompt = "You are ARIA. Say: 'Take your time.' Then listen."
            await sonic_speak(sonic, wait_prompt, timeout=20)
            await ws_send({"event": "aria_listening"})
            transcript = await sonic.wait_for_student_speech(timeout=0)  # no timeout

        else:
            return
