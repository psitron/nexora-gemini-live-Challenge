"""
Desktop Vision Loop — Gemini Vision + Agent S3.

Uses Gemini as a vision planner (NOT Computer Use tool).
Sends screenshot → AI returns JSON action → Agent S3 executes.

This avoids Computer Use API issues (FunctionResponse format,
url requirement, timeouts) by using plain generateContent with images.
"""

import asyncio
import base64
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Callable, Optional

from google import genai
from google.genai import types

from vta.orchestrator.agent_s3_client import AgentS3Client

logger = logging.getLogger(__name__)

MAX_STEPS = 15
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
VISION_MODEL = "gemini-3-flash-preview"

PLANNING_PROMPT = """You are a Linux desktop automation agent. Look at this screenshot ({w}x{h} pixels) and decide the next action.

GOAL: {goal}

{history}

AVAILABLE ACTIONS:
- "click_position" — Click at pixel coordinates. target="x,y".
- "type_text" — Type text into the focused field. target=text to type.
- "keyboard" — Press key/combo. target=key (e.g. "enter", "ctrl+c", "shift+enter").
- "open_terminal" — Open XFCE terminal.
- "run_command" — Type command in terminal and press Enter. target=command.
- "wait" — Wait 2 seconds.
- "done" — Goal complete. target=summary.
- "fail" — Cannot complete. target=reason.

RULES:
1. LOOK at the screenshot. If a terminal is already open, do NOT open another.
2. For click_position: provide pixel coordinates in the {w}x{h} image.
3. Do EXACTLY what the goal says — no more, no less.
4. As soon as the goal is achieved, return "done".
5. NEVER install software.
6. If the goal says to type something, use "run_command" or "type_text" — do NOT click first.
7. If the same action appears in PREVIOUS ACTIONS, try a DIFFERENT approach.
8. The terminal is already focused — go straight to typing commands.

Return ONE JSON object only. No markdown, no explanation.
Format: {{"action_type":"...","target":"...","description":"..."}}"""


@dataclass
class DesktopVisionResult:
    success: bool
    steps_executed: int
    message: str


async def _take_screenshot(agent: AgentS3Client) -> Optional[bytes]:
    """Take full screenshot via Agent S3."""
    try:
        result = await agent.screenshot()
        if result.get("success") and result.get("image"):
            return base64.b64decode(result["image"])
        return None
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None


def _parse_action(response_text: str) -> Optional[dict]:
    """Parse JSON action from model response."""
    text = response_text.strip()
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    match = re.search(r'\{[^}]*\}', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


async def _execute_action(action: dict, agent: AgentS3Client) -> bool:
    """Execute a parsed action via Agent S3."""
    action_type = action.get("action_type", "").lower()
    target = action.get("target", "")

    try:
        if action_type == "click_position":
            parts = target.replace(" ", "").split(",")
            x, y = int(parts[0]), int(parts[1])
            result = await agent.run("click_position", {"x": x, "y": y})

        elif action_type == "type_text":
            result = await agent.run("type_text", {"text": target})

        elif action_type == "keyboard":
            result = await agent.run("keyboard", {"keys": target})

        elif action_type == "open_terminal":
            result = await agent.run("open_terminal", {})

        elif action_type == "run_command":
            result = await agent.run("run_command", {"cmd": target})

        elif action_type == "double_click":
            parts = target.replace(" ", "").split(",")
            x, y = int(parts[0]), int(parts[1])
            result = await agent.run("double_click", {"x": x, "y": y})

        elif action_type == "wait":
            await asyncio.sleep(2)
            return True

        else:
            logger.warning(f"Unknown action: {action_type}")
            return False

        return result.get("result", {}).get("success", False)

    except Exception as e:
        logger.error(f"Action error '{action_type}': {e}")
        return False


class DesktopVisionLoop:
    """
    Vision planner for desktop automation.
    Uses plain generateContent (not Computer Use tool) to avoid
    FunctionResponse format issues.
    """

    def __init__(self):
        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self._model = os.environ.get("GEMINI_VISION_MODEL", VISION_MODEL)
        logger.info(f"DesktopVisionLoop initialized — model: {self._model}")

    async def run(
        self,
        goal: str,
        agent: AgentS3Client,
        ws_send: Callable,
        max_steps: int = MAX_STEPS,
    ) -> DesktopVisionResult:
        """Run desktop vision loop."""
        logger.info(f"DesktopVisionLoop starting — goal: {goal}")
        await ws_send({"event": "vision_loop_started", "goal": goal})

        screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        previous_actions = []
        steps = 0

        while steps < max_steps:
            steps += 1

            # Take screenshot
            screenshot = await _take_screenshot(agent)
            if not screenshot:
                await asyncio.sleep(1)
                screenshot = await _take_screenshot(agent)
            if not screenshot:
                logger.error("Screenshot failed")
                continue

            # Save screenshot
            ss_name = f"desktop_step_{steps}.png"
            with open(os.path.join(screenshots_dir, ss_name), "wb") as f:
                f.write(screenshot)

            # Build prompt
            history = ""
            if previous_actions:
                recent = previous_actions[-6:]
                history = "PREVIOUS ACTIONS:\n" + "\n".join(
                    f"  {i+1}. {a}" for i, a in enumerate(recent)
                )

            prompt = PLANNING_PROMPT.format(
                w=SCREEN_WIDTH, h=SCREEN_HEIGHT,
                goal=goal, history=history,
            )

            logger.info(f"DesktopVisionLoop step {steps}/{max_steps}")

            # Call Gemini vision
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model,
                        contents=[
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part(text=prompt),
                                    types.Part(
                                        inline_data=types.Blob(
                                            data=screenshot,
                                            mime_type="image/png",
                                        )
                                    ),
                                ],
                            )
                        ],
                        config=types.GenerateContentConfig(
                            max_output_tokens=1024,
                            temperature=0.1,
                        ),
                    ),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                logger.error("Gemini vision timed out (30s)")
                continue
            except Exception as e:
                logger.error(f"Gemini vision error: {e}")
                continue

            if not response.text:
                logger.warning("Empty response")
                continue

            response_text = response.text.strip()
            logger.info(f"AI response: {response_text[:200]}")

            # Parse action
            action = _parse_action(response_text)
            if not action:
                logger.warning(f"Could not parse action from: {response_text[:100]}")
                continue

            action_type = action.get("action_type", "").lower()
            target = action.get("target", "")
            description = action.get("description", action_type)

            logger.info(f"Action: {action_type} → {description}")

            await ws_send({
                "event": "vision_loop_step",
                "step": steps,
                "action": action_type,
                "description": description,
            })

            # Check terminal conditions
            if action_type == "done":
                logger.info(f"DesktopVisionLoop complete: {target}")
                await ws_send({"event": "vision_loop_done", "steps": steps, "summary": target})
                return DesktopVisionResult(success=True, steps_executed=steps, message=target)

            if action_type == "fail":
                logger.warning(f"DesktopVisionLoop failed: {target}")
                await ws_send({"event": "vision_loop_failed", "steps": steps, "reason": target})
                return DesktopVisionResult(success=False, steps_executed=steps, message=target)

            # Execute action
            success = await _execute_action(action, agent)

            # Wait for UI to update
            await asyncio.sleep(1.5)

            # Record action (no reflection — too slow and causes stuck loops)
            previous_actions.append(f"{action_type}({target}): {description}")

        # Max steps
        logger.warning(f"Max steps reached ({max_steps})")
        await ws_send({"event": "vision_loop_failed", "steps": steps, "reason": "Max steps"})
        return DesktopVisionResult(success=False, steps_executed=steps, message="Max steps reached")
