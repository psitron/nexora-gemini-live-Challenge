"""
Autonomous Vision Loop for VTA — Gemini Computer Use.

When a curriculum task has type "vision_driven", this loop:
  1. Takes a screenshot via Agent S3
  2. Sends screenshot + goal to Gemini Computer Use API
  3. Parses returned tool calls (click, type, key combo, etc.)
  4. Executes actions via Agent S3
  5. Takes new screenshot and sends as tool response
  6. Repeats until model returns text (done) or max steps reached
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
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# Gemini Computer Use model
COMPUTER_USE_MODEL = "gemini-3-flash-preview"


@dataclass
class VisionLoopResult:
    success: bool
    steps_executed: int
    message: str


async def _take_screenshot_b64(agent: AgentS3Client) -> Optional[str]:
    """Take a screenshot via Agent S3 and return as base64 PNG string."""
    try:
        result = await agent.screenshot()
        if result.get("success") and result.get("image"):
            return result["image"]
        logger.warning(f"Screenshot failed: {result.get('error', 'unknown')}")
        return None
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None


async def _execute_computer_use_action(
    action_name: str,
    action_args: dict,
    agent: AgentS3Client,
) -> bool:
    """Execute a Gemini Computer Use action via Agent S3.

    Gemini Computer Use returns normalized coordinates (0-1000 range).
    Convert to pixel coordinates based on screen resolution.
    """
    try:
        if action_name == "click":
            # Gemini sends x, y in 0-1000 normalized coords
            nx = action_args.get("x", 0)
            ny = action_args.get("y", 0)
            px_x = int(nx * SCREEN_WIDTH / 1000)
            px_y = int(ny * SCREEN_HEIGHT / 1000)
            button = action_args.get("button", "left")

            if button == "right":
                result = await agent.run("right_click", {"x": px_x, "y": px_y})
            elif action_args.get("count", 1) == 2:
                result = await agent.run("double_click", {"x": px_x, "y": px_y})
            else:
                result = await agent.run("click_position", {"x": px_x, "y": px_y})

        elif action_name == "type":
            text = action_args.get("text", "")
            # If coordinates provided, click first
            if "x" in action_args and "y" in action_args:
                nx = action_args["x"]
                ny = action_args["y"]
                px_x = int(nx * SCREEN_WIDTH / 1000)
                px_y = int(ny * SCREEN_HEIGHT / 1000)
                await agent.run("click_position", {"x": px_x, "y": px_y})
                await asyncio.sleep(0.3)

            result = await agent.run("type_text", {"text": text})

            if action_args.get("press_enter", False):
                await asyncio.sleep(0.2)
                await agent.run("keyboard", {"keys": "enter"})

        elif action_name == "key":
            keys = action_args.get("keys", "")
            if isinstance(keys, list):
                keys = "+".join(keys)
            result = await agent.run("keyboard", {"keys": keys})

        elif action_name == "scroll":
            nx = action_args.get("x", SCREEN_WIDTH // 2)
            ny = action_args.get("y", SCREEN_HEIGHT // 2)
            direction = "down" if action_args.get("direction", "down") == "down" else "up"
            clicks = action_args.get("amount", 3)
            result = await agent.run("scroll", {"direction": direction, "clicks": clicks})

        elif action_name == "wait":
            await asyncio.sleep(action_args.get("duration", 2))
            return True

        elif action_name == "screenshot":
            # Model requesting a screenshot — handled by the main loop
            return True

        else:
            logger.warning(f"Unknown Computer Use action: '{action_name}'")
            return False

        success = result.get("result", {}).get("success", False)
        if not success:
            logger.warning(f"Action '{action_name}' reported failure: {result}")
        return success

    except Exception as e:
        logger.error(f"Action execution error for '{action_name}': {e}")
        return False


class VisionLoop:
    """
    Autonomous vision-driven execution loop for VTA.

    Uses Gemini Computer Use API — single model handles planning,
    grounding, and reflection in one unified loop.
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

        Uses Gemini Computer Use: send screenshot + goal, get back tool calls,
        execute them, send new screenshot as tool response, repeat.
        """
        logger.info(f"VisionLoop starting — goal: {goal}")
        await ws_send({"event": "vision_loop_started", "goal": goal})

        steps = 0

        # Take initial screenshot
        screenshot_b64 = await _take_screenshot_b64(agent)
        if screenshot_b64 is None:
            await asyncio.sleep(1)
            screenshot_b64 = await _take_screenshot_b64(agent)

        if screenshot_b64 is None:
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
- To open an application: prefer running commands (e.g., click terminal, type command)
- NEVER install software. Do NOT run pip install, apt install, or any package manager.
- All required software is already installed.
- When the goal is complete, respond with a text message summarizing what was done.
- If you cannot complete the goal, respond with a text message explaining why.

Here is the current screenshot of the desktop:"""),
                    types.Part.from_bytes(
                        data=base64.b64decode(screenshot_b64),
                        mime_type="image/png",
                    ),
                ],
            ),
        ]

        # Configure Computer Use tool
        computer_use_tool = types.Tool(
            computer_use=types.ComputerUse(
                environment=types.Environment.ENVIRONMENT_SCREEN_ONLY,
            ),
        )
        config = types.GenerateContentConfig(
            tools=[computer_use_tool],
            thinking_config=types.ThinkingConfig(include_thoughts=True),
            temperature=0.1,
        )

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

            # Check if model returned tool calls (actions to execute)
            has_tool_calls = False
            tool_responses = []

            for part in response_content.parts:
                # Log thinking
                if hasattr(part, 'thought') and part.thought:
                    logger.info(f"[GEMINI THOUGHT] {part.text[:200] if part.text else ''}")
                    continue

                # Handle function calls from Computer Use
                if part.function_call:
                    has_tool_calls = True
                    fc = part.function_call
                    action_name = fc.name
                    action_args = dict(fc.args) if fc.args else {}

                    description = f"{action_name}({action_args})"
                    logger.info(f"Computer Use action: {description}")

                    await ws_send({
                        "event": "vision_loop_step",
                        "step": steps,
                        "action": action_name,
                        "description": description,
                    })

                    # Execute the action
                    success = await _execute_computer_use_action(
                        action_name, action_args, agent
                    )

                    # Wait for UI to update
                    await asyncio.sleep(1.5)

                    # Take new screenshot
                    new_screenshot_b64 = await _take_screenshot_b64(agent)

                    if new_screenshot_b64:
                        tool_responses.append(
                            types.Part.from_function_response(
                                name=action_name,
                                response={
                                    "success": success,
                                    "screenshot": "see attached image",
                                },
                            )
                        )
                        tool_responses.append(
                            types.Part.from_bytes(
                                data=base64.b64decode(new_screenshot_b64),
                                mime_type="image/png",
                            )
                        )
                    else:
                        tool_responses.append(
                            types.Part.from_function_response(
                                name=action_name,
                                response={
                                    "success": success,
                                    "error": "Failed to take screenshot after action",
                                },
                            )
                        )

            if has_tool_calls and tool_responses:
                # Send tool responses back to model
                contents.append(
                    types.Content(
                        role="user",
                        parts=tool_responses,
                    )
                )
                continue

            # No tool calls = model is done (returned text)
            # Extract completion message
            completion_text = ""
            for part in response_content.parts:
                if part.text and not (hasattr(part, 'thought') and part.thought):
                    completion_text += part.text

            if completion_text:
                logger.info(f"VisionLoop complete: {completion_text[:200]}")
                await ws_send({
                    "event": "vision_loop_done",
                    "steps": steps,
                    "summary": completion_text[:500],
                })
                return VisionLoopResult(
                    success=True,
                    steps_executed=steps,
                    message=completion_text[:500],
                )
            else:
                # Empty response with no tool calls — treat as done
                logger.warning("VisionLoop: no tool calls and no text — treating as done")
                await ws_send({
                    "event": "vision_loop_done",
                    "steps": steps,
                    "summary": "Task appears complete (no further actions needed)",
                })
                return VisionLoopResult(
                    success=True,
                    steps_executed=steps,
                    message="Task appears complete",
                )

        # Max steps reached
        logger.warning(f"VisionLoop reached max steps ({max_steps}) without completing goal")
        await ws_send({
            "event": "vision_loop_failed",
            "steps": steps,
            "reason": f"Reached maximum steps ({max_steps}) without completing goal",
        })
        return VisionLoopResult(
            success=False,
            steps_executed=steps,
            message=f"Did not complete within {max_steps} steps",
        )
