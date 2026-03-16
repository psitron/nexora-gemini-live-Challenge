"""
Autonomous Vision Loop for VTA — Gemini Computer Use + Playwright.

When a curriculum task has type "vision_driven", this loop:
  1. Takes a screenshot via Playwright browser
  2. Sends screenshot + goal to Gemini Computer Use API
  3. Parses returned function calls (click_at, type_text_at, navigate, etc.)
  4. Executes actions via Playwright (precise browser control)
  5. Takes new screenshot and sends as FunctionResponse
  6. Repeats until model returns text (done) or max steps reached

Based on Google's reference: generative-ai/gemini/computer-use/intro_computer_use.ipynb
Uses Playwright for precise browser automation (Jupyter, web apps, etc.)
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

from google import genai
from google.genai import types
from google.genai.types import (
    FunctionResponse as GFunctionResponse,
    FunctionResponseBlob,
)

logger = logging.getLogger(__name__)

MAX_STEPS = 20

# Browser viewport size — match Xvfb display (1280x800)
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900

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


class VisionLoop:
    """
    Autonomous vision-driven execution loop for VTA.

    Uses Gemini Computer Use API + Playwright for precise browser automation.
    Follows Google's reference implementation pattern exactly.
    """

    def __init__(self, model_id: str = None):
        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self._model = model_id or os.environ.get("GEMINI_COMPUTER_USE_MODEL", COMPUTER_USE_MODEL)
        self._playwright = None
        self._browser = None
        self._persistent_page = None  # Reused across subtasks
        logger.info(f"VisionLoop initialized — model: {self._model}")

    async def _ensure_browser(self):
        """Start Playwright browser if not already running."""
        if self._browser and self._browser.is_connected():
            return

        from playwright.async_api import async_playwright

        import os
        self._playwright = await async_playwright().start()

        # Use DISPLAY :1 (Xvfb) so student can see browser in noVNC
        # Fall back to headless if no display available
        display = os.environ.get("DISPLAY", "")
        if display:
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-software-rasterizer",
                ],
            )
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            )
        logger.info("Playwright browser launched")

    async def _new_page(self):
        """Create a new browser page with configured viewport."""
        await self._ensure_browser()
        page = await self._browser.new_page()
        await page.set_viewport_size({
            "width": SCREEN_WIDTH,
            "height": SCREEN_HEIGHT,
        })
        return page

    async def run(
        self,
        goal: str,
        agent,  # AgentS3Client — kept for compatibility but Playwright is primary
        ws_send: Callable,
        max_steps: int = MAX_STEPS,
    ) -> VisionLoopResult:
        """
        Run the autonomous vision loop until the goal is complete or max steps reached.

        Uses Playwright for all browser actions. Agent S3 is available as fallback
        for non-browser desktop actions.
        """
        logger.info(f"VisionLoop starting — goal: {goal}")
        await ws_send({"event": "vision_loop_started", "goal": goal})

        steps = 0
        # Reuse existing browser context — switch to the latest tab
        # (Jupyter opens notebooks in new tabs)
        if self._browser and self._browser.is_connected():
            pages = self._browser.contexts[0].pages if self._browser.contexts else []
            if pages:
                page = pages[-1]  # Use the most recent tab
                self._persistent_page = page
                logger.info(f"Using latest browser tab: {page.url}")
            else:
                page = await self._new_page()
                self._persistent_page = page
                logger.info("Created new browser page")
        else:
            await self._ensure_browser()
            page = await self._new_page()
            self._persistent_page = page
            logger.info("Created new browser page")

        try:
            # If goal contains a URL, navigate there first
            import re
            url_match = re.search(r'https?://\S+', goal)
            if url_match:
                start_url = url_match.group(0).rstrip('.')
                logger.info(f"Goal contains URL — navigating to: {start_url}")
                try:
                    await page.goto(start_url, wait_until="domcontentloaded", timeout=15000)
                    # Tell Gemini the page is already loaded so it doesn't navigate again
                    goal = goal + f"\n\nNOTE: The browser has ALREADY navigated to {start_url}. The page is loaded. Do NOT navigate again — proceed with the next action on the page."
                except Exception as e:
                    logger.warning(f"Initial navigation failed: {e}")
                await asyncio.sleep(3)

            # Create screenshots directory for debugging
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)

            # Take initial screenshot
            screenshot = await page.screenshot()
            with open(os.path.join(screenshots_dir, "step_0_initial.png"), "wb") as f:
                f.write(screenshot)
            logger.info(f"Saved screenshot: step_0_initial.png")

            # Build initial contents with goal + screenshot
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=f"""GOAL: {goal}

You are automating a browser. Use click_at to click buttons and links. Use type_text_at to type text. Use navigate only if you need to go to a new URL.

Look at the screenshot carefully. Identify the UI elements you need to interact with and click on them.

When done, respond with a short text summary.

Current screenshot:"""),
                        types.Part.from_bytes(
                            data=screenshot,
                            mime_type="image/png",
                        ),
                    ],
                ),
            ]

            # Configure Computer Use tool
            config_kwargs = {
                "tools": [
                    types.Tool(
                        computer_use=types.ComputerUse(
                            environment=types.Environment.ENVIRONMENT_BROWSER,
                            excluded_predefined_functions=["drag_and_drop"],
                        ),
                    )
                ],
            }

            # Note: thinking_config disabled — it causes the model to
            # over-analyze and navigate repeatedly instead of clicking

            try:
                config_kwargs["media_resolution"] = types.MediaResolution.MEDIA_RESOLUTION_ULTRA_HIGH
            except AttributeError:
                config_kwargs["media_resolution"] = types.MediaResolution.MEDIA_RESOLUTION_HIGH
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
                    # On API error, remove the last appended content that may be malformed
                    if len(contents) > 1:
                        contents.pop()
                    continue

                if not response.candidates:
                    logger.warning(f"Empty response from Gemini. Full response: {response}")
                    continue

                candidate = response.candidates[0]
                fr = candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'unknown'
                logger.info(f"Response finish_reason: {fr}")

                if not candidate.content:
                    logger.warning(f"No content in response. finish_reason={fr}")
                    continue

                response_content = candidate.content
                contents.append(response_content)

                # Log ALL parts for debugging
                for i, part in enumerate(response_content.parts):
                    part_type = "unknown"
                    if hasattr(part, "function_call") and part.function_call:
                        part_type = f"function_call: {part.function_call.name}({dict(part.function_call.args) if part.function_call.args else {}})"
                    elif hasattr(part, "thought") and part.thought:
                        part_type = f"thought: {part.text[:300] if part.text else ''}"
                    elif hasattr(part, "text") and part.text:
                        part_type = f"text: {part.text[:300]}"
                    elif hasattr(part, "inline_data") and part.inline_data:
                        part_type = "inline_data"
                    logger.info(f"  Part[{i}]: {part_type}")

                # Extract function calls
                function_calls = [
                    part.function_call
                    for part in response_content.parts
                    if hasattr(part, "function_call") and part.function_call
                ]

                # No function calls = model is done
                if not function_calls:
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

                # Execute function calls via Playwright
                function_response_parts = []

                for fc in function_calls:
                    fc_args = dict(fc.args) if fc.args else {}
                    description = f"{fc.name}({fc_args})"
                    logger.info(f"Computer Use action: {description}")

                    await ws_send({
                        "event": "vision_loop_step",
                        "step": steps,
                        "action": fc.name,
                        "description": description,
                    })

                    # Execute via Playwright
                    try:
                        await self._execute_playwright_action(fc.name, fc_args, page)
                    except Exception as e:
                        logger.error(f"Action '{fc.name}' failed: {e}")

                    # Wait for page to settle after action
                    if fc.name == "navigate":
                        await asyncio.sleep(3.0)
                    else:
                        await asyncio.sleep(1.0)

                    # Check if a new tab opened (e.g., Jupyter opens notebook in new tab)
                    if self._browser and self._browser.contexts:
                        all_pages = self._browser.contexts[0].pages
                        if len(all_pages) > 0 and all_pages[-1] != page:
                            page = all_pages[-1]
                            self._persistent_page = page
                            logger.info(f"Switched to new tab: {page.url}")
                            await asyncio.sleep(2.0)  # Wait for new tab to load

                    # Take new screenshot
                    new_screenshot = await page.screenshot()
                    current_url = page.url

                    # Save screenshot for debugging
                    ss_name = f"step_{steps}_{fc.name}.png"
                    with open(os.path.join(screenshots_dir, ss_name), "wb") as f:
                        f.write(new_screenshot)
                    logger.info(f"Saved screenshot: {ss_name}")

                    # Build FunctionResponse with screenshot INSIDE (exact Google pattern)
                    # If the model requested safety confirmation, acknowledge it
                    response_dict = {"url": current_url}
                    if fc_args.get("safety_decision", {}).get("decision") == "require_confirmation":
                        response_dict["safety_acknowledgement"] = True

                    function_response_parts.append(
                        types.Part(
                            function_response=GFunctionResponse(
                                name=fc.name,
                                response=response_dict,
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

                # Append function responses to conversation
                contents.append(
                    types.Content(
                        role="user",
                        parts=function_response_parts,
                    )
                )
                logger.info(f"State captured. History: {len(contents)} messages.")

        finally:
            # Keep page open for next subtask — only close on VisionLoop.close()
            pass

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

    async def _execute_playwright_action(self, name: str, args: dict, page):
        """Execute a Computer Use action via Playwright."""

        if name == "navigate":
            url = args.get("url", "")
            logger.info(f"Navigating to: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # Wait for page to fully render

        elif name == "click_at":
            px_x = _normalize_x(args.get("x", 0))
            px_y = _normalize_y(args.get("y", 0))
            logger.info(f"Clicking at ({px_x}, {px_y})")
            await page.mouse.click(px_x, px_y)

        elif name == "hover_at":
            px_x = _normalize_x(args.get("x", 0))
            px_y = _normalize_y(args.get("y", 0))
            await page.mouse.move(px_x, px_y)

        elif name == "type_text_at":
            px_x = _normalize_x(args.get("x", 0))
            px_y = _normalize_y(args.get("y", 0))
            text = args.get("text", "")
            logger.info(f"Typing '{text[:50]}' at ({px_x}, {px_y})")
            await page.mouse.click(px_x, px_y)
            await asyncio.sleep(0.1)
            await page.keyboard.type(text)
            if args.get("press_enter", False):
                await page.keyboard.press("Enter")

        elif name == "key_combination":
            keys = args.get("keys", "")
            if isinstance(keys, list):
                keys = "+".join(keys)
            # Playwright needs proper key names: Shift not shift, Control not ctrl
            key_map = {
                "shift": "Shift", "ctrl": "Control", "control": "Control",
                "alt": "Alt", "meta": "Meta", "enter": "Enter",
                "tab": "Tab", "escape": "Escape", "backspace": "Backspace",
                "delete": "Delete", "space": " ", "arrowup": "ArrowUp",
                "arrowdown": "ArrowDown", "arrowleft": "ArrowLeft",
                "arrowright": "ArrowRight",
            }
            parts = keys.split("+")
            mapped = [key_map.get(k.lower().strip(), k) for k in parts]
            keys = "+".join(mapped)
            logger.info(f"Key combo: {keys}")
            await page.keyboard.press(keys)

        elif name == "scroll_at" or name == "scroll_document":
            px_x = _normalize_x(args.get("x", SCREEN_WIDTH // 2))
            px_y = _normalize_y(args.get("y", SCREEN_HEIGHT // 2))
            direction = args.get("direction", "down")
            delta = 300 if direction == "down" else -300
            await page.mouse.wheel(0, delta)

        elif name == "open_web_browser":
            logger.info("Browser already open")

        elif name == "go_back":
            await page.go_back()

        elif name == "go_forward":
            await page.go_forward()

        elif name == "search":
            query = args.get("query", "")
            await page.goto(f"https://www.google.com/search?q={query}")

        elif name == "wait_5_seconds":
            await asyncio.sleep(5)

        else:
            logger.warning(f"Unknown action: '{name}'")

    async def close(self):
        """Clean up Playwright resources."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        logger.info("VisionLoop Playwright resources cleaned up")
