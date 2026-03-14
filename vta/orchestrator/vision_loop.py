"""
Autonomous Vision Loop for VTA — Gemini Computer Use.

When a curriculum task has type "vision_driven", this loop:
  1. Takes a screenshot via Agent S3
  2. Sends screenshot + goal to Gemini Computer Use API
  3. Parses returned function calls (click_at, type_text_at, etc.)
  4. Executes actions via Agent S3
  5. Takes new screenshot and sends as FunctionResponse
  6. Repeats until model returns text (done) or max steps reached

Based on Google's reference: generative-ai/gemini/computer-use/intro_computer_use.ipynb
"""

import asyncio
import base64
import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from google import genai
from google.genai import types
from google.genai.types import (
    FunctionResponse as GFunctionResponse,
    FunctionResponseBlob,
)

from vta.orchestrator.agent_s3_client import AgentS3Client

logger = logging.getLogger(__name__)

MAX_STEPS = 15

# Screen resolution — matches Xvfb config
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# Gemini Computer Use model
COMPUTER_USE_MODEL = "gemini-3-flash-preview"


def _normalize_x(x: int) -> int:
    """Convert normalized x (0-1000) to pixel coordinate."""
    return int(x / 1000 * SCREEN_WIDTH)


def _normalize_y(y: int) -> int:
    """Convert normalized y (0-1000) to pixel coordinate."""
    return int(y / 1000 * SCREEN_HEIGHT)


@dataclass
class VisionLoopResult:
    success: bool
    steps_executed: int
    message: str


async def _take_screenshot_bytes(agent: AgentS3Client) -> Optional[bytes]:
    """Take a screenshot via Agent S3 and return as raw PNG bytes."""
    try:
        result = await agent.screenshot()
        if result.get("success") and result.get("image"):
            return base64.b64decode(result["image"])
        logger.warning(f"Screenshot failed: {result.get('error', 'unknown')}")
        return None
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None


async def _execute_action(
    function_call,
    agent: AgentS3Client,
) -> bool:
    """Execute a Gemini Computer Use function call via Agent S3.

    Handles the predefined functions: click_at, type_text_at, navigate,
    open_web_browser, key_combination, scroll.
    """
    name = function_call.name
    args = dict(function_call.args) if function_call.args else {}

    try:
        if name == "click_at":
            px_x = _normalize_x(args.get("x", 0))
            px_y = _normalize_y(args.get("y", 0))
            button = args.get("button", "left")
            count = args.get("count", 1)

            if button == "right":
                result = await agent.run("right_click", {"x": px_x, "y": px_y})
            elif count == 2:
                result = await agent.run("double_click", {"x": px_x, "y": px_y})
            else:
                result = await agent.run("click_position", {"x": px_x, "y": px_y})

        elif name == "type_text_at":
            px_x = _normalize_x(args.get("x", 0))
            px_y = _normalize_y(args.get("y", 0))
            text = args.get("text", "")

            # Click at position first
            await agent.run("click_position", {"x": px_x, "y": px_y})
            await asyncio.sleep(0.3)

            # Type the text
            result = await agent.run("type_text", {"text": text})

            # Press enter if requested
            if args.get("press_enter", False):
                await asyncio.sleep(0.2)
                await agent.run("keyboard", {"keys": "enter"})

        elif name == "key_combination":
            keys = args.get("keys", "")
            if isinstance(keys, list):
                keys = "+".join(keys)
            result = await agent.run("keyboard", {"keys": keys})

        elif name == "scroll":
            direction = "down" if args.get("direction", "down") == "down" else "up"
            clicks = args.get("amount", 3)
            result = await agent.run("scroll", {"direction": direction, "clicks": clicks})

        elif name == "navigate":
            url = args.get("url", "")
            result = await agent.run("run_command", {"cmd": f"firefox '{url}' &"})

        elif name == "open_web_browser":
            result = await agent.run("run_command", {"cmd": "firefox &"})

        elif name == "wait":
            await asyncio.sleep(args.get("duration", 2))
            return True

        elif name == "screenshot":
            return True

        else:
            logger.warning(f"Unknown Computer Use function: '{name}'")
            return False

        success = result.get("result", {}).get("success", False)
        if not success:
            logger.warning(f"Action '{name}' reported failure: {result}")
        return success

    except Exception as e:
        logger.error(f"Action execution error for '{name}': {e}")
        return False


class VisionLoop:
    """
    Autonomous vision-driven execution loop for VTA.

    Uses Gemini Computer Use API — single model handles planning,
    grounding, and reflection in one unified loop.

    Follows Google's reference implementation pattern:
    screenshot → model → function_calls → execute → screenshot → repeat
    """

    def __init__(self):
        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self._model = os.environ.get("GEMINI_COMPUTER_USE_MODEL", COMPUTER_USE_MODEL)
        logger.info(f"VisionLoop initialized — model: {self._model}")

    async def run(
        self,
        goal: str,
        agent: AgentS3Client,
        ws_send: Callable,
        max_steps: int = MAX_STEPS,
    ) -> VisionLoopResult:
        """
        Run the autonomous vision loop until the goal is complete or max steps reached.
        """
        logger.info(f"VisionLoop starting — goal: {goal}")
        await ws_send({"event": "vision_loop_started", "goal": goal})

        steps = 0

        # Take initial screenshot
        screenshot_bytes = await _take_screenshot_bytes(agent)
        if screenshot_bytes is None:
            await asyncio.sleep(1)
            screenshot_bytes = await _take_screenshot_bytes(agent)

        if screenshot_bytes is None:
            msg = "Failed to take initial screenshot"
            logger.error(msg)
            await ws_send({"event": "vision_loop_failed", "steps": 0, "reason": msg})
            return VisionLoopResult(success=False, steps_executed=0, message=msg)

        # Build initial contents with goal + screenshot
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=f"""You are a Linux desktop automation agent controlling an XFCE desktop.

GOAL: {goal}

RULES:
- To open an application: prefer running commands (e.g., open terminal, type command)
- NEVER install software. Do NOT run pip install, apt install, or any package manager.
- All required software is already installed.
- When the goal is complete, respond with a text message summarizing what was done.
- If you cannot complete the goal, respond with a text message explaining why.

Here is the current screenshot of the desktop:"""),
                    types.Part.from_bytes(
                        data=screenshot_bytes,
                        mime_type="image/png",
                    ),
                ],
            ),
        ]

        # Configure Computer Use tool — use BROWSER environment
        # (only option available) but exclude browser-specific functions
        # since we're automating a full Linux desktop, not just a browser
        computer_use_tool = types.Tool(
            computer_use=types.ComputerUse(
                environment=types.Environment.ENVIRONMENT_BROWSER,
                excluded_predefined_functions=["drag_and_drop"],
            ),
        )

        # Build config — add thinking for Gemini 3+
        config_kwargs = {
            "tools": [computer_use_tool],
            "temperature": 0.1,
        }
        try:
            model_version = float(self._model.split("-")[1])
            if model_version >= 3:
                config_kwargs["thinking_config"] = types.ThinkingConfig(
                    include_thoughts=True
                )
        except (IndexError, ValueError):
            pass

        config = types.GenerateContentConfig(**config_kwargs)

        while steps < max_steps:
            steps += 1
            logger.info(f"VisionLoop step {steps}/{max_steps}")

            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                logger.error(f"Gemini Computer Use call failed: {e}")
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

            # Log any thinking/reasoning
            for part in response_content.parts:
                if hasattr(part, "thought") and part.thought and part.text:
                    logger.info(f"[GEMINI THOUGHT] {part.text[:200]}")

            if not function_calls:
                # No function calls = model is done (returned text)
                final_text = " ".join(
                    part.text
                    for part in response_content.parts
                    if hasattr(part, "text") and part.text
                    and not (hasattr(part, "thought") and part.thought)
                )

                if final_text:
                    logger.info(f"VisionLoop complete: {final_text[:200]}")
                    await ws_send({
                        "event": "vision_loop_done",
                        "steps": steps,
                        "summary": final_text[:500],
                    })
                    return VisionLoopResult(
                        success=True,
                        steps_executed=steps,
                        message=final_text[:500],
                    )
                else:
                    logger.warning("No function calls and no text — treating as done")
                    await ws_send({
                        "event": "vision_loop_done",
                        "steps": steps,
                        "summary": "Task appears complete",
                    })
                    return VisionLoopResult(
                        success=True,
                        steps_executed=steps,
                        message="Task appears complete",
                    )

            # Execute function calls and build responses
            function_response_parts = []

            for fc in function_calls:
                description = f"{fc.name}({dict(fc.args) if fc.args else {}})"
                logger.info(f"Computer Use action: {description}")

                await ws_send({
                    "event": "vision_loop_step",
                    "step": steps,
                    "action": fc.name,
                    "description": description,
                })

                # Execute the action
                await _execute_action(fc, agent)

                # Wait for UI to update
                await asyncio.sleep(1.5)

                # Take new screenshot
                new_screenshot = await _take_screenshot_bytes(agent)

                # Build FunctionResponse with screenshot INSIDE (Google's exact pattern)
                # Screenshot goes in FunctionResponse.parts as FunctionResponseBlob
                if new_screenshot:
                    function_response_parts.append(
                        types.Part(
                            function_response=GFunctionResponse(
                                name=fc.name,
                                response={"status": "completed"},
                                parts=[
                                    types.Part(
                                        inline_data=FunctionResponseBlob(
                                            mime_type="image/png",
                                            data=new_screenshot,
                                        )
                                    )
                                ],
                            ),
                        )
                    )
                else:
                    function_response_parts.append(
                        types.Part(
                            function_response=GFunctionResponse(
                                name=fc.name,
                                response={"status": "completed", "error": "screenshot failed"},
                            ),
                        )
                    )

            # Append function responses to conversation
            contents.append(
                types.Content(
                    role="user",
                    parts=function_response_parts,
                )
            )

        # Max steps reached
        logger.warning(f"VisionLoop reached max steps ({max_steps})")
        await ws_send({
            "event": "vision_loop_failed",
            "steps": steps,
            "reason": f"Reached maximum steps ({max_steps})",
        })
        return VisionLoopResult(
            success=False,
            steps_executed=steps,
            message=f"Did not complete within {max_steps} steps",
        )
