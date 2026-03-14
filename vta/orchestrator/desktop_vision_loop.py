"""
Desktop Vision Loop — Gemini Computer Use + Agent S3.

For desktop automation tasks (file manager, terminal UI, any GUI app).
Unlike the browser VisionLoop (Playwright), this uses Agent S3's
pyautogui/xdotool for screenshots and actions on the full Linux desktop.

Flow:
  1. Take screenshot via Agent S3 (/action/screenshot)
  2. Send screenshot to Gemini vision model
  3. AI decides next action + coordinates
  4. Execute via Agent S3 (click_position, type_text, keyboard, etc.)
  5. Take new screenshot, send back as function response
  6. Repeat until done or max steps

Based on the old AWS VisionLoop architecture (vision planner + Agent S3),
now powered by Gemini Computer Use.
"""

import asyncio
import base64
import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from google import genai
from google.genai import types

from vta.orchestrator.agent_s3_client import AgentS3Client

logger = logging.getLogger(__name__)

MAX_STEPS = 15

# Screen resolution — matches Xvfb config
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

VISION_MODEL = "gemini-3-flash-preview"


@dataclass
class DesktopVisionResult:
    success: bool
    steps_executed: int
    message: str


def _normalize_x(x: int) -> int:
    """Convert normalized x (0-1000) to pixel coordinate."""
    return int(x / 1000 * SCREEN_WIDTH)


def _normalize_y(y: int) -> int:
    """Convert normalized y (0-1000) to pixel coordinate."""
    return int(y / 1000 * SCREEN_HEIGHT)


async def _take_screenshot(agent: AgentS3Client) -> Optional[bytes]:
    """Take screenshot via Agent S3, return raw PNG bytes."""
    try:
        result = await agent.screenshot()
        if result.get("success") and result.get("image"):
            return base64.b64decode(result["image"])
        logger.warning(f"Screenshot failed: {result.get('error', 'unknown')}")
        return None
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None


async def _execute_desktop_action(
    action_name: str,
    action_args: dict,
    agent: AgentS3Client,
) -> bool:
    """Execute a Gemini Computer Use action via Agent S3 (pyautogui/xdotool)."""
    try:
        if action_name == "click_at":
            px_x = _normalize_x(action_args.get("x", 0))
            px_y = _normalize_y(action_args.get("y", 0))
            count = action_args.get("count", 1)
            button = action_args.get("button", "left")

            if button == "right":
                result = await agent.run("right_click", {"x": px_x, "y": px_y})
            elif count == 2:
                result = await agent.run("double_click", {"x": px_x, "y": px_y})
            else:
                result = await agent.run("click_position", {"x": px_x, "y": px_y})

        elif action_name == "type_text_at":
            px_x = _normalize_x(action_args.get("x", 0))
            px_y = _normalize_y(action_args.get("y", 0))
            text = action_args.get("text", "")

            await agent.run("click_position", {"x": px_x, "y": px_y})
            await asyncio.sleep(0.3)
            result = await agent.run("type_text", {"text": text})

            if action_args.get("press_enter", False):
                await asyncio.sleep(0.2)
                await agent.run("keyboard", {"keys": "enter"})

        elif action_name == "key_combination":
            keys = action_args.get("keys", "")
            if isinstance(keys, list):
                keys = "+".join(keys)
            result = await agent.run("keyboard", {"keys": keys})

        elif action_name == "hover_at":
            # Agent S3 doesn't have hover — use click instead
            px_x = _normalize_x(action_args.get("x", 0))
            px_y = _normalize_y(action_args.get("y", 0))
            result = await agent.run("click_position", {"x": px_x, "y": px_y})

        elif action_name == "scroll_at" or action_name == "scroll_document":
            direction = action_args.get("direction", "down")
            clicks = action_args.get("amount", 3)
            result = await agent.run("scroll", {"direction": direction, "clicks": clicks})

        elif action_name == "navigate":
            url = action_args.get("url", "")
            result = await agent.run("run_command", {"cmd": f"firefox '{url}' &"})

        elif action_name == "open_web_browser":
            result = await agent.run("run_command", {"cmd": "firefox &"})

        elif action_name == "wait_5_seconds":
            await asyncio.sleep(5)
            return True

        elif action_name == "screenshot":
            return True

        else:
            logger.warning(f"Unknown desktop action: '{action_name}'")
            return False

        success = result.get("result", {}).get("success", False)
        if not success:
            logger.warning(f"Desktop action '{action_name}' failed: {result}")
        return success

    except Exception as e:
        logger.error(f"Desktop action error '{action_name}': {e}")
        return False


class DesktopVisionLoop:
    """
    Vision-driven desktop automation using Gemini + Agent S3.

    Takes screenshots of the full Linux desktop via Agent S3,
    sends them to Gemini for analysis, executes actions via
    Agent S3's pyautogui/xdotool.
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
        """Run desktop vision loop until goal is complete or max steps."""
        logger.info(f"DesktopVisionLoop starting — goal: {goal}")
        await ws_send({"event": "vision_loop_started", "goal": goal})

        # Create screenshots directory
        screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        steps = 0

        # Take initial screenshot
        screenshot = await _take_screenshot(agent)
        if not screenshot:
            await asyncio.sleep(1)
            screenshot = await _take_screenshot(agent)

        if not screenshot:
            msg = "Failed to take initial screenshot"
            logger.error(msg)
            await ws_send({"event": "vision_loop_failed", "steps": 0, "reason": msg})
            return DesktopVisionResult(success=False, steps_executed=0, message=msg)

        # Save initial screenshot
        with open(os.path.join(screenshots_dir, "desktop_step_0.png"), "wb") as f:
            f.write(screenshot)

        # Build initial conversation
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=f"""You are a Linux desktop automation agent controlling an XFCE desktop.
Look at this screenshot of the desktop ({SCREEN_WIDTH}x{SCREEN_HEIGHT} pixels).

GOAL: {goal}

RULES:
- Use click_at to click on UI elements. Coordinates are normalized 0-1000.
- Use type_text_at to click a field and type text.
- Use key_combination for keyboard shortcuts.
- To open a terminal: look for terminal in the taskbar or right-click desktop.
- To run commands: click on terminal, then type_text_at with the command.
- NEVER install software. All required software is already installed.
- When the goal is complete, respond with a text summary.
- If you cannot complete the goal, respond with a text explanation.

Current screenshot:"""),
                    types.Part(
                        inline_data=types.Blob(
                            data=screenshot,
                            mime_type="image/png",
                        )
                    ),
                ],
            ),
        ]

        # Configure Computer Use tool
        computer_use_tool = types.Tool(
            computer_use=types.ComputerUse(
                environment=types.Environment.ENVIRONMENT_BROWSER,
                excluded_predefined_functions=["drag_and_drop"],
            ),
        )

        # Use highest available media resolution for Computer Use accuracy
        try:
            media_res = types.MediaResolution.MEDIA_RESOLUTION_ULTRA_HIGH
        except AttributeError:
            media_res = types.MediaResolution.MEDIA_RESOLUTION_HIGH

        config = types.GenerateContentConfig(
            tools=[computer_use_tool],
            temperature=0.1,
            media_resolution=media_res,
        )

        while steps < max_steps:
            steps += 1
            logger.info(f"DesktopVisionLoop step {steps}/{max_steps}")

            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                logger.error(f"Gemini vision call failed: {e}")
                continue

            if not response.candidates or not response.candidates[0].content:
                logger.warning("Empty response from Gemini")
                continue

            response_content = response.candidates[0].content
            contents.append(response_content)

            # Extract function calls
            function_calls = [
                part.function_call
                for part in response_content.parts
                if hasattr(part, "function_call") and part.function_call
            ]

            # Log parts
            for i, part in enumerate(response_content.parts):
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    logger.info(f"  Part[{i}]: {fc.name}({dict(fc.args) if fc.args else {}})")
                elif hasattr(part, "text") and part.text:
                    logger.info(f"  Part[{i}]: text: {part.text[:200]}")

            # No function calls = done
            if not function_calls:
                final_text = " ".join(
                    part.text for part in response_content.parts
                    if hasattr(part, "text") and part.text
                    and not (hasattr(part, "thought") and part.thought)
                )
                if final_text:
                    logger.info(f"DesktopVisionLoop complete: {final_text[:200]}")
                    await ws_send({
                        "event": "vision_loop_done",
                        "steps": steps,
                        "summary": final_text[:500],
                    })
                    return DesktopVisionResult(
                        success=True,
                        steps_executed=steps,
                        message=final_text[:500],
                    )
                else:
                    await ws_send({
                        "event": "vision_loop_done",
                        "steps": steps,
                        "summary": "Task appears complete",
                    })
                    return DesktopVisionResult(
                        success=True,
                        steps_executed=steps,
                        message="Task appears complete",
                    )

            # Execute function calls via Agent S3
            function_response_parts = []

            for fc in function_calls:
                fc_args = dict(fc.args) if fc.args else {}
                description = f"{fc.name}({fc_args})"
                logger.info(f"Desktop action: {description}")

                await ws_send({
                    "event": "vision_loop_step",
                    "step": steps,
                    "action": fc.name,
                    "description": description,
                })

                # Execute via Agent S3
                await _execute_desktop_action(fc.name, fc_args, agent)

                # Wait for UI to update
                await asyncio.sleep(1.5)

                # Take new screenshot
                new_screenshot = await _take_screenshot(agent)

                # Save screenshot
                if new_screenshot:
                    ss_name = f"desktop_step_{steps}_{fc.name}.png"
                    with open(os.path.join(screenshots_dir, ss_name), "wb") as f:
                        f.write(new_screenshot)
                    logger.info(f"Saved: {ss_name}")

                # Build function response with screenshot
                if new_screenshot:
                    function_response_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"status": "completed"},
                            ),
                        )
                    )
                    function_response_parts.append(
                        types.Part(
                            inline_data=types.Blob(
                                data=new_screenshot,
                                mime_type="image/png",
                            )
                        )
                    )
                else:
                    function_response_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"status": "completed", "note": "screenshot failed"},
                            ),
                        )
                    )

            # Append function responses
            contents.append(
                types.Content(role="user", parts=function_response_parts)
            )
            logger.info(f"State captured. History: {len(contents)} messages.")

        # Max steps
        logger.warning(f"DesktopVisionLoop max steps ({max_steps})")
        await ws_send({
            "event": "vision_loop_failed",
            "steps": steps,
            "reason": f"Reached max steps ({max_steps})",
        })
        return DesktopVisionResult(
            success=False,
            steps_executed=steps,
            message=f"Did not complete within {max_steps} steps",
        )
