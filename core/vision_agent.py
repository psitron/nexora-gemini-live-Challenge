"""
Vision-Driven Reactive Agent

Architecture:
  1. Take screenshot of PRIMARY_MONITOR
  2. Send resized screenshot to Vision AI Model (Gemini/Nova/etc.)
  3. AI returns next action + approximate pixel coordinates (hint_x, hint_y)
  4. Scale hint coordinates from resized image to actual screen coordinates
  5. Use OCR + hint position to find the EXACT element (disambiguates duplicates)
  6. Draw red box annotation precisely on the target element
  7. Execute the action (click, type, keyboard)
  8. Repeat until goal is complete

PRECISE ANNOTATIONS: The AI provides approximate coordinates for where
each action targets on screen. These are used as "hints" for OCR to
find the correct element when the same text appears multiple times
(e.g., "Search" in the taskbar vs. "Search" in a browser). This ensures
annotations always appear on the RIGHT element.

MULTI-MODEL SUPPORT: Supports multiple vision AI providers (Gemini, Amazon Nova)
via a pluggable adapter pattern. Switch providers via VISION_PROVIDER in .env.
"""

from __future__ import annotations

import json
import re
import time
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from PIL import Image

from config.settings import get_settings
from core.monitor_utils import get_selected_monitor
from core.vision_models import create_vision_model, VisionModel, VisionModelResponse
from perception.visual.screenshot import capture_selected_monitor
from execution.educational_mouse_controller import EducationalMouseController


@dataclass
class VisionAction:
    action_type: str
    target: str
    description: str
    highlight_text: str = ""
    hint_x: int = -1
    hint_y: int = -1


@dataclass
class VisionAgentResult:
    success: bool
    steps_executed: int
    message: str


class VisionAgent:
    MAX_STEPS = 30
    SCREENSHOT_MAX_WIDTH = 1024

    def __init__(self):
        self._settings = get_settings()
        self._monitor_rect = get_selected_monitor()
        self._action_history: List[str] = []
        self._scale = 1.0
        self._monitor_offset = (0, 0)
        self._current_screenshot: Optional[Image.Image] = None  # Store current screenshot for OCR
        if self._monitor_rect:
            self._monitor_offset = (self._monitor_rect[0], self._monitor_rect[1])
        
        # Initialize vision model based on config
        provider = self._settings.models.vision_provider
        if provider == "gemini":
            self._vision_model = create_vision_model(
                "gemini",
                api_key=self._settings.models.gemini_api_key,
                model_name=self._settings.models.gemini_vision_model
            )
        elif provider == "nova":
            self._vision_model = create_vision_model(
                "nova",
                region_name=self._settings.models.nova_region,
                model_id=self._settings.models.nova_model_id
            )
        elif provider == "bedrock":
            self._vision_model = create_vision_model(
                "bedrock",
                region_name=self._settings.models.bedrock_region,
                model_id=self._settings.models.bedrock_vision_model_id
            )
        else:
            raise ValueError(f"Unknown vision provider: {provider}. Set VISION_PROVIDER to 'gemini', 'nova', or 'bedrock' in .env")
        
        print(f"[Vision Model] Using: {self._vision_model.get_model_name()}")

        # Educational mouse controller for visible movements
        # Enable educational mode by default (set to False for fast mode)
        educational_mode = os.getenv("EDUCATIONAL_MODE", "true").lower() == "true"
        self._mouse_controller = EducationalMouseController(educational_mode=educational_mode)
        if educational_mode:
            print(f"[Educational Mode] ENABLED - Students will see mouse movements")
            print(f"  Movement duration: {self._mouse_controller.MOVEMENT_DURATION}s")
            print(f"  Pause before click: {self._mouse_controller.PAUSE_BEFORE_CLICK}s")
            print(f"  Pause after click: {self._mouse_controller.PAUSE_AFTER_CLICK}s")
        else:
            print(f"[Educational Mode] DISABLED - Using fast direct movements")

        # Debug mode setup
        self._debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self._debug_dir = None
        self._debug_log = None
        if self._debug_mode:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self._debug_dir = Path("E:/ui-agent/debug_sessions") / timestamp
                self._debug_dir.mkdir(parents=True, exist_ok=True)
                print(f"[DEBUG] Session logs: {self._debug_dir}")
                
                # Create debug log file
                self._debug_log = self._debug_dir / "session.log"
                with open(self._debug_log, "w", encoding="utf-8") as f:
                    f.write(f"Vision Agent Debug Session\n")
                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Model: {self._vision_model.get_model_name()}\n")
                    f.write(f"Monitor: {self._monitor_rect}\n")
                    f.write(f"="*70 + "\n\n")
            except Exception as e:
                print(f"[DEBUG] Failed to setup debug mode: {e}")
                self._debug_mode = False
        self._verify_save_count = 0  # for saving verification crops in debug

    def _resize_screenshot(self, img: Image.Image) -> Image.Image:
        max_w = self.SCREENSHOT_MAX_WIDTH
        if img.width > max_w:
            ratio = max_w / img.width
            self._scale = img.width / max_w
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        else:
            self._scale = 1.0
        return img

    def _scale_hint_to_screen(self, hint_x: int, hint_y: int) -> Tuple[int, int]:
        """Convert Gemini's image coordinates to actual screen coordinates."""
        screen_x = int(hint_x * self._scale) + self._monitor_offset[0]
        screen_y = int(hint_y * self._scale) + self._monitor_offset[1]
        return screen_x, screen_y

    def run(self, goal: str) -> VisionAgentResult:
        # No API key check needed - model is already initialized in __init__
        print(f"\nGoal: {goal}")
        print(f"Monitor: {self._monitor_rect}")
        print()
        
        # Log the task at the start
        if self._debug_mode:
            self._log_debug(
                f"TASK: {goal}\n"
                f"Vision Model: {self._vision_model.get_model_name()}\n"
                f"Monitor Bounds: {self._monitor_rect}\n"
                f"Screen Scale Factor: {self._scale:.2f}x\n"
                f"Max Steps Allowed: {self.MAX_STEPS}",
                section="TASK INITIALIZATION"
            )

        steps = 0
        consecutive_failures = 0
        previous_actions: List[str] = []
        last_action_summary = ""  # Track what happened last for self-assessment

        while steps < self.MAX_STEPS:
            steps += 1

            print(f"\n{'='*60}")
            print(f"Step {steps}: Capturing screen...")
            screenshot = capture_selected_monitor()
            self._current_screenshot = screenshot  # Store for OCR (avoid re-capture)
            small_screenshot = self._resize_screenshot(screenshot)
            
            # Debug: save screenshots
            if self._debug_mode:
                screenshot.save(self._debug_dir / f"step_{steps:02d}_full.png")
                small_screenshot.save(self._debug_dir / f"step_{steps:02d}_resized.png")
                self._log_debug(f"Step {steps}: Screenshots saved")

            print(f"Step {steps}: AI analyzing (scale={self._scale:.2f}x)...")
            action = self._ask_vision_ai(
                small_screenshot, goal, previous_actions,
                step_num=steps, last_action_summary=last_action_summary
            )

            if action is None:
                consecutive_failures += 1
                if self._debug_mode:
                    self._log_debug(
                        f"AI Analysis Failed (attempt {consecutive_failures}/3)\n"
                        f"Reason: AI returned None (likely API error or parse failure)",
                        section=f"Step {steps} - AI FAILURE"
                    )
                if consecutive_failures >= 3:
                    print(f"Step {steps}: AI failed {consecutive_failures}x in a row, stopping")
                    if self._debug_mode:
                        self._log_debug(
                            f"Task Aborted: AI Failed Repeatedly\n"
                            f"Consecutive Failures: {consecutive_failures}\n"
                            f"Steps Completed: {steps}",
                            section="TASK ABORTED"
                        )
                    return VisionAgentResult(False, steps, "AI repeatedly failed to analyze screen")
                print(f"Step {steps}: AI failed ({consecutive_failures}/3), retrying...")
                time.sleep(1)
                continue
            consecutive_failures = 0

            # Scale hint coordinates from resized image to screen coordinates
            # (Agent S3 pattern: log full coordinate transformation trace)
            if action.hint_x >= 0 and action.hint_y >= 0:
                raw_hx, raw_hy = action.hint_x, action.hint_y
                action.hint_x, action.hint_y = self._scale_hint_to_screen(
                    action.hint_x, action.hint_y
                )
                if self._debug_mode:
                    self._log_debug(
                        f"COORDINATE TRANSFORMATION:\n"
                        f"  AI image coords: ({raw_hx}, {raw_hy}) in {small_screenshot.size[0]}x{small_screenshot.size[1]}\n"
                        f"  Scale factor: {self._scale:.4f}x\n"
                        f"  Monitor offset: {self._monitor_offset}\n"
                        f"  Screen coords: ({action.hint_x}, {action.hint_y})\n"
                        f"  Calc: x={raw_hx}*{self._scale:.2f}+{self._monitor_offset[0]}={action.hint_x}  "
                        f"y={raw_hy}*{self._scale:.2f}+{self._monitor_offset[1]}={action.hint_y}"
                    )

            print(f"Step {steps}: {action.action_type} -> {action.description}")
            if action.hint_x >= 0:
                print(f"  AI hint position: ({action.hint_x},{action.hint_y})")

            if action.action_type == "done":
                print(f"\n[DONE] {action.description}")
                if self._debug_mode:
                    self._log_debug(
                        f"Task Completed Successfully\n"
                        f"Total Steps: {steps}\n"
                        f"Final Message: {action.description}\n"
                        f"Actions Taken: {len(previous_actions)}",
                        section="TASK COMPLETION"
                    )
                    self._log_debug("\nAction History:\n" + "\n".join([f"  {i+1}. {a}" for i, a in enumerate(previous_actions)]))
                return VisionAgentResult(True, steps, action.description)

            # Loop detection - catch repeated identical actions
            action_key = f"{action.action_type}:{action.target}"
            recent = self._action_history[-5:]
            repeat_count = sum(1 for a in recent if a == action_key)
            
            # Also detect "same type of action with similar target" (e.g. type_text with same path twice)
            recent_types = [a.split(":")[0] for a in recent]
            type_repeat = sum(1 for t in recent_types if t == action.action_type)
            
            if action.action_type == "open_search" and repeat_count >= 1:
                print(f"  [LOOP] open_search repeated {repeat_count+1}x, closing search and re-assessing")
                import pyautogui
                pyautogui.press("escape")
                time.sleep(0.5)
                self._action_history.append("keyboard:escape")
                previous_actions.append("keyboard(escape): Close search overlay (loop recovery)")
                last_action_summary = "keyboard(escape) - succeeded. Closed search overlay due to loop detection."
                continue
            elif action.action_type == "type_text" and repeat_count >= 1:
                # Same text typed again - skip and press Enter instead
                print(f"  [LOOP] type_text repeated with same text, pressing Enter instead")
                import pyautogui
                pyautogui.press("enter")
                time.sleep(0.5)
                self._action_history.append("keyboard:enter")
                previous_actions.append("keyboard(enter): Press Enter (type_text loop recovery)")
                last_action_summary = "keyboard(enter) - succeeded. Pressed Enter instead of retyping same text."
                continue
            elif action.action_type == "click_position" and repeat_count >= 1:
                print(f"  [LOOP] Click position repeated, trying keyboard action instead")
                if any("cell" in str(a).lower() or "jupyter" in str(a).lower() for a in previous_actions[-3:]):
                    action = VisionAction("type_text", "# Continue...", "Type placeholder to exit loop")
                else:
                    action = VisionAction("keyboard", "tab", "Press Tab (loop recovery)")
                action_key = f"{action.action_type}:{action.target}"
            elif repeat_count >= 2:
                print(f"  [LOOP] Repeated 3x, trying Escape to break out")
                action = VisionAction("keyboard", "escape", "Press Escape (loop recovery)")
                action_key = "keyboard:escape"
            
            self._action_history.append(action_key)

            previous_actions.append(
                f"{action.action_type}({action.target}): {action.description}"
            )

            # Execute action with detailed logging
            if self._debug_mode:
                self._log_debug(
                    f"Executing: {action.action_type}\n"
                    f"Target: {action.target}\n"
                    f"Description: {action.description}\n"
                    f"Hint Coordinates: ({action.hint_x}, {action.hint_y})",
                    section=f"Step {steps} - EXECUTING ACTION"
                )
            
            exec_start = time.time()
            success = self._execute_action(action)
            exec_duration = time.time() - exec_start

            # Build last_action_summary for next step's self-assessment
            status_word = "succeeded" if success else "FAILED"
            last_action_summary = f"{action.action_type}({action.target}) - {status_word}. {action.description}"

            if self._debug_mode:
                status = "[OK] SUCCESS" if success else "[X] FAILED"
                self._log_debug(
                    f"EXECUTION RESULT:\n"
                    f"  Status: {status}\n"
                    f"  Action: {action.action_type}({action.target})\n"
                    f"  Duration: {exec_duration:.2f}s\n"
                    f"  Step: {steps}/{self.MAX_STEPS}\n"
                    f"  Actions so far: {len(previous_actions)}",
                    section=f"Step {steps} - RESULT"
                )

            if not success:
                print(f"  [X] Action FAILED: {action.action_type}({action.target[:50]})")
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    print(f"  [ABORT] Too many consecutive failures ({consecutive_failures})")
                    if self._debug_mode:
                        self._log_debug(
                            f"Task Aborted: Too many execution failures\n"
                            f"Consecutive Failures: {consecutive_failures}",
                            section="TASK ABORTED"
                        )
                    return VisionAgentResult(False, steps, f"Too many failures ({consecutive_failures})")
            else:
                consecutive_failures = 0

            if action.action_type == "wait":
                time.sleep(2)
            elif action.action_type in ("open_search", "run_command"):
                time.sleep(1)
            elif action.action_type in ("click_text", "click_position"):
                time.sleep(0.8)
            else:
                time.sleep(0.5)

        if self._debug_mode:
            self._log_debug(
                f"Task Failed: Reached Maximum Steps\n"
                f"Max Steps Allowed: {self.MAX_STEPS}\n"
                f"Steps Taken: {steps}\n"
                f"Total Actions: {len(previous_actions)}",
                section="TASK FAILED - MAX STEPS"
            )
            self._log_debug("\nAction History:\n" + "\n".join([f"  {i+1}. {a}" for i, a in enumerate(previous_actions)]))
        
        return VisionAgentResult(False, steps, f"Reached max steps ({self.MAX_STEPS})")

    # ---- Vision AI ----

    def _ask_vision_ai(
        self, screenshot: Image.Image, goal: str, previous_actions: List[str],
        step_num: int = 0, last_action_summary: str = ""
    ) -> Optional[VisionAction]:
        """Ask the vision AI model to decide the next action."""
        try:
            # Extract knowledge buffer from previous_actions if present
            known_facts = ""
            action_history = []
            for action in previous_actions:
                if action.startswith("KNOWN FACTS:"):
                    known_facts = action
                else:
                    action_history.append(action)

            # Build history section with knowledge buffer prominently displayed
            history = ""
            if known_facts:
                history += f"\n\n[FACTS] {known_facts}"
                history += "\n[WARNING] DO NOT REPEAT these completed actions. Move to the next step!"

            if action_history:
                recent = action_history[-6:]
                history += "\n\nActions already taken:\n" + "\n".join(
                    f"  {i+1}. {a}" for i, a in enumerate(recent)
                )

            # Self-assessment prompt (inspired by Claude Computer Use)
            assessment = ""
            if last_action_summary:
                assessment = f"""

SELF-ASSESSMENT (do this BEFORE choosing next action):
Your last action was: {last_action_summary}
Look at this screenshot carefully. Did your last action succeed?
- If YES: move on to the NEXT step toward the goal. Do NOT repeat the same action.
- If NO: try a DIFFERENT approach. Do not repeat what failed.
- If you see the SAME screen as last time, your action probably FAILED - try something different!
- If UNSURE: look for visual clues (new window opened? text appeared? dialog changed?)"""

            img_w, img_h = screenshot.size

            prompt = f"""You are a Windows PC automation agent. Analyze this screenshot ({img_w}x{img_h} pixels) and decide the next action.

GOAL: {goal}
{history}{assessment}

SCREENING RULES:
- NEVER click text from console/terminal/debug output (e.g. "Step N:", "AI analyzing", "Result")
- If goal says "open X", FIRST action MUST be open_search with app name X
- To navigate to a folder path, use "run_command" with the path (faster than File Explorer)
- ONLY interact with real desktop: taskbar, apps, files, windows

Return ONE JSON object. No markdown, no code blocks, no explanation.

Format: {{"action_type":"...","target":"...","description":"...","highlight_text":"...","hint_x":N,"hint_y":N}}

action_types:
- "open_search" - Open Windows search and search for an app. target=app name. hint_x/hint_y=taskbar search area.
- "run_command" - Run a shell command (Win+R). target=command string (e.g. "explorer E:\\folder" or "notepad"). hint_x/hint_y=-1,-1. Use this for opening folders or running programs directly.
- "click_text" - Click visible text on screen. target=exact text. hint_x/hint_y=center of that text.
- "click_position" - Click at coordinates. target="x,y" (in this {img_w}x{img_h} image). hint_x/hint_y=same.
- "drag" - Click-and-drag. target="x1,y1,x2,y2" (in this image). hint_x/hint_y=start position.
- "keyboard" - Press keys. target=keys like "escape","enter","ctrl+s","f5". hint_x/hint_y=element being activated.
- "type_text" - Type into focused field. target=text to type. hint_x/hint_y=position of input field.
- "scroll" - Scroll up or down. target="up" or "down". hint_x/hint_y=area to scroll.
- "wait" - Wait for loading. target=reason. hint_x=-1,hint_y=-1.
- "done" - Goal complete. target=summary. hint_x=-1,hint_y=-1.

RULES:
1. To open ANY app, use "open_search" with app name. Never click "Search" text.
2. If goal says "open X", FIRST action MUST be "open_search" with that app.
3. To navigate to a folder/file path, prefer "run_command" with "explorer <path>".
4. IGNORE console/terminal/debug text. Only interact with real desktop and apps.
5. If a popup/dialog blocks, close it first (keyboard: escape, or click its X/OK).
6. If same action tried and failed, try something DIFFERENT. Try keyboard shortcuts!
7. NEVER repeat the same action more than once.
8. hint_x/hint_y MUST be pixel coordinates in this {img_w}x{img_h} image.
9. PREFER KEYBOARD SHORTCUTS over clicking when available:
   - Ctrl+N = New document/workbook/file (Excel, Word, Notepad, etc.)
   - Ctrl+S = Save
   - Ctrl+O = Open file
   - Ctrl+W = Close tab/window
   - Tab = Move to next cell/field
   - Enter = Confirm/submit
   If clicking a button fails, ALWAYS try the keyboard shortcut next.
10. JUPYTER NOTEBOOK WORKFLOW (if goal mentions "notebook" or "jupyter"):
   - After launching Jupyter, you see a FILE BROWSER (not a notebook yet!)
   - To create NEW notebook: Click "New" button (top right) -> Click "Python 3" from dropdown
   - Do NOT try to click "Untitled.ipynb" before creating it!
   - Only click existing .ipynb files if they're already listed in the browser

JSON only:"""

            # Debug: save the prompt sent to AI
            if self._debug_mode:
                self._log_debug(f"\n{'='*70}\nStep {step_num} - PROMPT SENT TO AI\n{'='*70}\n{prompt}\n")

            # Use the vision model abstraction
            response = self._vision_model.generate_content(
                prompt=prompt,
                image=screenshot,
                max_tokens=2048,
                temperature=0.1
            )

            # Handle empty responses
            if not response.text:
                if response.finish_reason:
                    print(f"  [AI] Empty response (finish_reason: {response.finish_reason})")
                    if self._debug_mode:
                        self._log_debug(f"Step {step_num} - Empty response. Finish reason: {response.finish_reason}")
                else:
                    print(f"  [AI] Empty response")
                return None

            text = response.text.strip()
            
            # Debug: save AI response
            if self._debug_mode:
                self._log_debug(f"\nStep {step_num} - AI Response:\n{text}\n")

            data = self._extract_json(text)
            if data is None:
                print(f"  [AI] Could not parse: {text[:200]}")
                if self._debug_mode:
                    self._log_debug(f"Step {step_num} - JSON PARSE FAILED")
                return None
            
            # Debug: log parsed action
            if self._debug_mode:
                self._log_debug(f"Step {step_num} - Parsed Action: {json.dumps(data, indent=2)}")
            
            # Validate action: block clicking console/agent text
            action_type = data.get("action_type", "wait")
            target = data.get("target", "").lower()
            
            # Block patterns that indicate agent/console UI
            blocked_patterns = [
                "step ", "ai analyzing", "capturing screen", "executing",
                "click on the suggested", "suggested action", "command output",
                "terminal", "console", "debug", "session", "result:", "success", "failed"
            ]
            
            if action_type == "click_text":
                for pattern in blocked_patterns:
                    if pattern in target:
                        print(f"  [FILTER] Blocked click_text on agent/console text: '{target[:50]}'")
                        if self._debug_mode:
                            self._log_debug(f"Step {step_num} - BLOCKED: click_text contains pattern '{pattern}'")
                        return None  # Force AI to retry with a different action

            # CRITICAL FIX: Validate and clamp hint coordinates to image bounds
            hint_x = int(data.get("hint_x", -1))
            hint_y = int(data.get("hint_y", -1))

            # Validate coordinates are within the image bounds that AI analyzed
            if hint_x >= 0 and hint_y >= 0:
                if hint_x >= img_w or hint_y >= img_h:
                    print(f"  [WARNING] AI gave coordinates ({hint_x},{hint_y}) outside image bounds ({img_w}x{img_h})")
                    print(f"  [WARNING] This usually means AI is confused about image size")
                    # Clamp to valid range
                    hint_x = max(0, min(hint_x, img_w - 1))
                    hint_y = max(0, min(hint_y, img_h - 1))
                    print(f"  [WARNING] Clamped to ({hint_x},{hint_y})")
                    if self._debug_mode:
                        self._log_debug(f"Step {step_num} - COORDINATE CLAMPED: ({data.get('hint_x')},{data.get('hint_y')}) -> ({hint_x},{hint_y})")

            return VisionAction(
                action_type=action_type,
                target=data.get("target", ""),
                description=data.get("description", ""),
                highlight_text=data.get("highlight_text", ""),
                hint_x=hint_x,
                hint_y=hint_y,
            )

        except KeyboardInterrupt:
            raise
        except Exception as e:
            import traceback
            err_str = str(e)
            print(f"  [AI] ERROR: {err_str}")
            if self._debug_mode:
                self._log_debug(f"Step {step_num} - AI EXCEPTION:\n{traceback.format_exc()}")
            # Print more details to console for troubleshooting
            print(f"  Full error: {err_str}")
            print(f"  Error type: {type(e).__name__}")
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """Extract JSON from AI response, handling code fences and truncation."""
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()

        # Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find complete { ... } block
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Find nested { ... } block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Handle truncated JSON - try to complete it intelligently
        if text.startswith("{"):
            # Try to extract what we have
            at_match = re.search(r'"action_type"\s*:\s*"([^"]+)"', text)
            tgt_match = re.search(r'"target"\s*:\s*"([^"]*)', text)
            desc_match = re.search(r'"description"\s*:\s*"([^"]*)', text)
            ht_match = re.search(r'"highlight_text"\s*:\s*"([^"]*)', text)
            hx_match = re.search(r'"hint_x"\s*:\s*(-?\d+)', text)
            hy_match = re.search(r'"hint_y"\s*:\s*(-?\d+)', text)
            
            if at_match:
                result = {
                    "action_type": at_match.group(1),
                    "target": tgt_match.group(1) if tgt_match else "",
                    "description": desc_match.group(1) if desc_match else "",
                    "highlight_text": ht_match.group(1) if ht_match else "",
                    "hint_x": int(hx_match.group(1)) if hx_match else -1,
                    "hint_y": int(hy_match.group(1)) if hy_match else -1,
                }
                return result

        return None

    # ---- Action dispatch ----

    def _execute_action(self, action: VisionAction) -> bool:
        if action.action_type == "open_search":
            return self._do_open_search(action)
        elif action.action_type == "run_command":
            return self._do_run_command(action)
        elif action.action_type == "click_text":
            return self._do_click_text(action)
        elif action.action_type == "click_position":
            return self._do_click_position(action)
        elif action.action_type == "drag":
            return self._do_drag(action)
        elif action.action_type == "keyboard":
            return self._do_keyboard(action)
        elif action.action_type == "type_text":
            return self._do_type_text(action)
        elif action.action_type == "scroll":
            return self._do_scroll(action)
        elif action.action_type == "wait":
            print(f"  Waiting: {action.target}")
            return True
        elif action.action_type == "done":
            return True
        else:
            print(f"  Unknown action: {action.action_type}")
            return False

    # ---- open_search ----

    def _do_open_search(self, action: VisionAction) -> bool:
        """Open Windows search, type query, and click best result.

        Strategy:
        1. Try Win+S to open search (with retry)
        2. Type the query
        3. Try vision detection to find the best result
        4. If vision fails, try OCR
        5. If both fail, press Enter for best match
        """
        import pyautogui
        from core.visual_annotator_adapter import highlight_bbox

        query = action.target
        hint = (action.hint_x, action.hint_y) if action.hint_x >= 0 else None

        if self._debug_mode:
            self._log_debug(
                f"Action: open_search\n"
                f"Query: '{query}'\n"
                f"AI Hint Position: {hint}",
                section="ACTION: open_search"
            )

        # Annotate the taskbar search area
        taskbar_bbox = self._find_taskbar_search_bbox()
        if taskbar_bbox:
            highlight_bbox(taskbar_bbox, duration=0.6, fade_out_seconds=0.8)

        # Try to open search with retry (Win+S sometimes fails)
        for attempt in range(2):
            if attempt == 0:
                print(f"  Opening search (Win+S)...")
                pyautogui.hotkey("win", "s")
            else:
                print(f"  Retrying search open (Win key)...")
                pyautogui.press("win")
            time.sleep(1.2)

            # Check if search opened by taking a screenshot and looking for search UI
            check_screenshot = capture_selected_monitor()
            self._current_screenshot = check_screenshot
            # If we got here, assume search is open (we can't reliably detect it without vision)
            break

        # Type the query character by character
        print(f"  Typing '{query}'...")
        for char in query:
            pyautogui.write(char, interval=0)
            time.sleep(0.05)
        time.sleep(1.5)

        # Strategy: Press Enter to launch the top search result
        # This is the MOST RELIABLE approach - Windows search auto-selects the best match
        # Trying to click a specific result is error-prone (vision/OCR often miss)
        print(f"  Pressing Enter to launch top result for '{query}'...")
        pyautogui.press("enter")
        time.sleep(2.0)  # Wait for app to launch
        return True

    # ---- run_command ----

    def _do_run_command(self, action: VisionAction) -> bool:
        """Run a shell command via Win+R (Run dialog), OR type into open terminal.

        CRITICAL FIX: Detects if a terminal window is already active and types
        directly into it instead of opening Win+R.
        """
        import pyautogui
        from core.visual_annotator_adapter import highlight_bbox

        command = action.target
        print(f"  Running command: {command}")

        if self._debug_mode:
            self._log_debug(
                f"Action: run_command\n"
                f"Command: {command}",
                section="ACTION: run_command"
            )

        # CRITICAL FIX: Check if we're already in a terminal window
        try:
            import pygetwindow as gw
            active_window = gw.getActiveWindow()
            if active_window:
                title = active_window.title.lower()
                terminal_keywords = ["prompt", "powershell", "terminal", "bash", "cmd", "anaconda"]
                if any(term in title for term in terminal_keywords):
                    print(f"  [DETECTED] Terminal window already active: '{active_window.title}'")
                    print(f"  [TYPING] Typing command into terminal instead of opening Win+R")

                    # Type directly into the terminal
                    for char in command:
                        pyautogui.write(char, interval=0)
                        time.sleep(0.03)

                    time.sleep(0.3)
                    pyautogui.press('enter')
                    time.sleep(1.5)
                    return True
        except Exception as e:
            print(f"  [WARNING] Could not detect active window: {e}")
            # Fall through to Win+R method

        # Original Win+R method for standalone commands
        print(f"  [INFO] No terminal detected, using Win+R dialog")

        # Annotate the taskbar area to show we're using Win+R
        taskbar_bbox = self._find_taskbar_search_bbox()
        if taskbar_bbox:
            highlight_bbox(taskbar_bbox, duration=0.6, fade_out_seconds=0.8)

        # Open Run dialog
        pyautogui.hotkey("win", "r")
        time.sleep(1.0)
        
        # Annotate the Run dialog (appears roughly center-left of screen)
        if self._monitor_rect:
            left, top, right, bottom = self._monitor_rect
            cx = left + (right - left) // 2
            cy = top + (bottom - top) // 2
            # Highlight the Run dialog area
            highlight_bbox(
                f"{cx - 200},{cy - 30},{400},{60}",
                duration=0.8, fade_out_seconds=1.0,
            )
            # Move mouse visibly to the Run dialog
            self._smooth_click(cx, cy)
            time.sleep(0.3)
        
        # Type the command character by character (visible for training)
        for char in command:
            pyautogui.write(char, interval=0)
            time.sleep(0.03)
        
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True

    # ---- scroll ----

    def _do_scroll(self, action: VisionAction) -> bool:
        """Scroll up or down at a position, with visible annotation."""
        import pyautogui
        from core.visual_annotator_adapter import highlight_bbox
        
        direction = action.target.lower().strip()
        clicks = 5 if direction == "down" else -5
        
        # Annotate the scroll area
        if action.hint_x >= 0 and action.hint_y >= 0:
            pad = 30
            highlight_bbox(
                f"{action.hint_x - pad},{action.hint_y - pad},{pad * 2},{pad * 2}",
                duration=0.5, fade_out_seconds=0.8,
            )
            # Move mouse visibly to scroll position (educational mode)
            self._mouse_controller.move_to(action.hint_x, action.hint_y, show_path=True)
        
        print(f"  Scrolling {direction}")
        pyautogui.scroll(clicks)
        return True

    # ---- click_text ----

    def _do_click_text(self, action: VisionAction) -> bool:
        """Find text on screen using VISION-BASED DETECTION, draw red box, then click."""
        import pyautogui
        from core.visual_annotator_adapter import highlight_bbox

        text = action.target
        hint = (action.hint_x, action.hint_y) if action.hint_x >= 0 else None

        print(f"  Finding '{text}' with vision-based detection...")

        # NEW: Try vision-based element detection FIRST (more accurate than OCR)
        bbox = self._find_element_with_vision(
            element_description=f"{text} (clickable element)",
            hint_pos=hint
        )

        # CRITICAL FIX: Properly handle vision detection failure
        if bbox is None:
            print(f"  [FAILED] Vision detection returned None for '{text}'")
            print(f"  [FALLBACK] Trying OCR detection...")
            # Fall through to OCR fallback below
        elif bbox:
            x, y, w, h = bbox
            print(f"  [OK] Vision found '{text}' at ({x},{y}) size {w}x{h}")

            # Draw red box around element
            highlight_bbox(
                f"{x},{y},{w},{h}",
                duration=0.8, fade_out_seconds=1.0
            )

            # Click strategy: if bbox is suspiciously large, click upper-center
            # (vision models often return oversized bboxes that extend below the element)
            if h > 200 or w > 300:
                # Oversized bbox: click upper-third center
                cx = x + w // 2
                cy = y + h // 4  # upper quarter, not center
                print(f"  [INFO] Large bbox detected, clicking upper portion at ({cx},{cy})")
            else:
                cx, cy = x + w // 2, y + h // 2

            self._smooth_click(cx, cy)
            return True

        # Fallback: Try OCR (may still work for simple text)
        if bbox is None:
            print(f"  Vision detection failed, trying OCR fallback...")
        all_matches = self._find_all_text_matches(text, hint_pos=hint)

        if not all_matches:
            # Last resort: AI hint coordinates (least accurate)
            # BUT ONLY if coordinates are reasonable (not far outside screen)
            if action.hint_x >= 0 and action.hint_y >= 0:
                # Validate hint coordinates are within reasonable bounds
                if (action.hint_x < self._monitor_rect[2] + 100 and
                    action.hint_y < self._monitor_rect[3] + 100):
                    print(f"  OCR also failed, using AI hint ({action.hint_x},{action.hint_y})")
                    pad = 15
                    highlight_bbox(
                        f"{action.hint_x-pad},{action.hint_y-pad},{pad*2},{pad*2}",
                        duration=0.6, fade_out_seconds=0.8,
                    )
                    self._smooth_click(action.hint_x, action.hint_y)
                    return True
                else:
                    print(f"  [X] AI hint coordinates ({action.hint_x},{action.hint_y}) outside valid screen bounds")

            # LAST RESORT: Keyboard fallback for common dropdown patterns
            # CRITICAL: We try keyboard actions but return False because we can't verify success
            text_lower = text.lower()
            print(f"  [FALLBACK] All detection methods failed. Trying keyboard as last resort...")

            # Common dropdown patterns (Jupyter, VS Code, etc.)
            if "python 3" in text_lower or "python3" in text_lower:
                print(f"  [KEYBOARD] Attempting Down+Enter for Python 3 dropdown")
                print(f"  [WARNING] Cannot verify if dropdown is open - this may fail")
                import pyautogui
                time.sleep(0.3)
                pyautogui.press('down')  # Navigate to Python 3 (IF dropdown is open)
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(0.5)
                print(f"  [X] Keyboard action attempted but SUCCESS UNCERTAIN - returning False")
                return False  # HONEST: We don't know if it worked

            elif "notebook" in text_lower and "new" in action.description.lower():
                print(f"  [KEYBOARD] Attempting Down+Enter for new notebook")
                print(f"  [WARNING] Cannot verify if dropdown is open - this may fail")
                import pyautogui
                time.sleep(0.3)
                pyautogui.press('down')
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(0.5)
                print(f"  [X] Keyboard action attempted but SUCCESS UNCERTAIN - returning False")
                return False  # HONEST: We don't know if it worked

            elif any(keyword in text_lower for keyword in ["file", "folder", "text file"]):
                print(f"  [KEYBOARD] Attempting Down+Enter for file/folder dropdown")
                print(f"  [WARNING] Cannot verify if dropdown is open - this may fail")
                import pyautogui
                time.sleep(0.3)
                pyautogui.press('down')
                time.sleep(0.2)
                pyautogui.press('enter')
                time.sleep(0.5)
                print(f"  [X] Keyboard action attempted but SUCCESS UNCERTAIN - returning False")
                return False  # HONEST: We don't know if it worked

            print(f"  [X] FAILED: '{text}' not found by any method (vision, OCR, hint, or keyboard)")
            return False

        # If OCR found matches, use them
        print(f"  [OK] OCR found {len(all_matches)} match(es) for '{text}'")

        # If multiple matches found, use visual verification
        if len(all_matches) > 1:
            print(f"  Found {len(all_matches)} matches for '{text}', verifying...")
            bbox = self._verify_correct_match(text, all_matches, action.description)
            if not bbox:
                print(f"  [X] Could not verify correct '{text}'")
                bbox = all_matches[0]  # Fallback to first match
        else:
            bbox = all_matches[0]

        x, y, w, h = bbox
        print(f"  Verified match at ({x},{y}) {w}x{h}")

        pad = 4
        highlight_bbox(
            f"{x-pad},{y-pad},{w+pad*2},{h+pad*2}",
            duration=0.8, fade_out_seconds=1.2,
        )
        self._smooth_click(x + w // 2, y + h // 2)
        return True

    # ---- click_position ----

    def _do_click_position(self, action: VisionAction) -> bool:
        from core.visual_annotator_adapter import highlight_bbox

        # Use hint coordinates (already scaled to screen)
        if action.hint_x >= 0 and action.hint_y >= 0:
            x, y = action.hint_x, action.hint_y
        else:
            try:
                parts = action.target.split(",")
                ix, iy = int(parts[0].strip()), int(parts[1].strip())
                x, y = self._scale_hint_to_screen(ix, iy)
            except (ValueError, IndexError):
                print(f"  [X] Bad position: {action.target}")
                return False

        # Try to annotate nearby text element
        if action.highlight_text:
            hint = (x, y)
            bbox = self._find_text_on_monitor(action.highlight_text, hint_pos=hint)
            if bbox:
                bx, by, bw, bh = bbox
                pad = 4
                highlight_bbox(
                    f"{bx-pad},{by-pad},{bw+pad*2},{bh+pad*2}",
                    duration=0.6, fade_out_seconds=0.8,
                )
            else:
                pad = 15
                highlight_bbox(
                    f"{x-pad},{y-pad},{pad*2},{pad*2}",
                    duration=0.6, fade_out_seconds=0.8,
                )
        else:
            pad = 15
            highlight_bbox(
                f"{x-pad},{y-pad},{pad*2},{pad*2}",
                duration=0.6, fade_out_seconds=0.8,
            )

        self._smooth_click(x, y)
        return True

    # ---- drag ----

    def _do_drag(self, action: VisionAction) -> bool:
        """Click-and-drag from start to end (for Paint drawing, etc)."""
        import pyautogui
        from core.visual_annotator_adapter import highlight_bbox

        try:
            parts = action.target.split(",")
            x1, y1, x2, y2 = [int(p.strip()) for p in parts]
            # Scale from image coordinates to screen coordinates
            x1, y1 = self._scale_hint_to_screen(x1, y1)
            x2, y2 = self._scale_hint_to_screen(x2, y2)
        except (ValueError, IndexError):
            print(f"  [X] Bad drag coordinates: {action.target}")
            return False

        # Annotate the drag path with a line-like box
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        w, h = max_x - min_x + 20, max_y - min_y + 20
        highlight_bbox(
            f"{min_x-10},{min_y-10},{w},{h}",
            duration=0.5, fade_out_seconds=0.8,
        )

        print(f"  Dragging from ({x1},{y1}) to ({x2},{y2})")

        # Use educational mouse controller for visible drag
        result = self._mouse_controller.drag_to(x1, y1, x2, y2)
        if result.success:
            print(f"  Drag complete")
            return True
        else:
            print(f"  [X] Drag failed: {result.message}")
            return False

    # ---- keyboard ----

    def _do_keyboard(self, action: VisionAction) -> bool:
        import pyautogui
        from core.visual_annotator_adapter import highlight_bbox

        keys = [k.strip() for k in action.target.split("+")]
        keys_str = "+".join(keys)
        print(f"  Pressing: {keys_str}")

        # Annotate the element being activated
        annotated = False
        if action.highlight_text and action.hint_x >= 0:
            hint = (action.hint_x, action.hint_y)
            bbox = self._find_text_on_monitor(action.highlight_text, hint_pos=hint)
            if bbox:
                bx, by, bw, bh = bbox
                pad = 4
                highlight_bbox(
                    f"{bx-pad},{by-pad},{bw+pad*2},{bh+pad*2}",
                    duration=0.5, fade_out_seconds=0.8,
                )
                annotated = True
        
        # If no text annotation, show a small indicator at hint position
        if not annotated and action.hint_x >= 0 and action.hint_y >= 0:
            pad = 20
            highlight_bbox(
                f"{action.hint_x - pad},{action.hint_y - pad},{pad * 2},{pad * 2}",
                duration=0.4, fade_out_seconds=0.6,
            )

        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            print(f"  [X] Key press failed: {e}")
            return False

    # ---- type_text ----

    def _do_type_text(self, action: VisionAction) -> bool:
        import pyautogui
        from core.visual_annotator_adapter import highlight_bbox

        # Ensure focus: click at hint or at highlighted text so the target field/window gets focus
        if action.hint_x >= 0 and action.hint_y >= 0:
            if action.highlight_text:
                hint = (action.hint_x, action.hint_y)
                bbox = self._find_text_on_monitor(action.highlight_text, hint_pos=hint)
                if bbox:
                    bx, by, bw, bh = bbox
                    pad = 4
                    highlight_bbox(
                        f"{bx-pad},{by-pad},{bw+pad*2},{bh+pad*2}",
                        duration=0.5, fade_out_seconds=0.8,
                    )
                    self._smooth_click(bx + bw // 2, by + bh // 2)
                    time.sleep(0.2)
                else:
                    highlight_bbox(
                        f"{action.hint_x-15},{action.hint_y-15},{30},{30}",
                        duration=0.4, fade_out_seconds=0.6,
                    )
                    self._smooth_click(action.hint_x, action.hint_y)
                    time.sleep(0.2)
            else:
                highlight_bbox(
                    f"{action.hint_x-15},{action.hint_y-15},{30},{30}",
                    duration=0.4, fade_out_seconds=0.6,
                )
                self._smooth_click(action.hint_x, action.hint_y)
                time.sleep(0.2)

        text = action.target
        print(f"  Typing: {text}")
        try:
            # pyautogui.write() only supports ASCII by default; for other chars use pyperclip or key down
            for char in text:
                pyautogui.write(char, interval=0)
                time.sleep(0.04)

            # Auto-press Enter if description mentions it (common pattern in Excel/forms)
            if action.description and ("press enter" in action.description.lower() or "press Enter" in action.description):
                print(f"  (Auto-pressing Enter as mentioned in description)")
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(0.3)

            return True
        except Exception as e:
            print(f"  [X] Typing failed: {e}")
            return False

    # ---- Helpers ----

    def _find_text_on_monitor(
        self, text: str, hint_pos: Tuple[int, int] | None = None
    ) -> Tuple[int, int, int, int] | None:
        """Find text on the selected monitor using OCR with hint disambiguation."""
        from core.ocr_finder import find_text_on_screen

        if self._monitor_rect:
            left, top, right, bottom = self._monitor_rect
            region = (left, top, right - left, bottom - top)
            return find_text_on_screen(text, region=region, timeout=2.0, hint_pos=hint_pos)
        return find_text_on_screen(text, timeout=2.0, hint_pos=hint_pos)

    def _find_all_text_matches(
        self, text: str, hint_pos: Tuple[int, int] | None = None
    ) -> List[Tuple[int, int, int, int]]:
        """
        Find ALL occurrences of text using OCR on the CURRENT screenshot.

        KEY FIX: Uses self._current_screenshot (same image Gemini analyzed)
        instead of re-capturing, eliminating timing gaps.
        """
        from core.ocr_finder import find_all_text_in_image

        if not self._current_screenshot:
            print("  [WARNING] No current screenshot available, falling back to screen capture")
            from core.ocr_finder import find_all_text_on_screen
            if self._monitor_rect:
                left, top, right, bottom = self._monitor_rect
                region = (left, top, right - left, bottom - top)
                return find_all_text_on_screen(text, region=region, timeout=2.0, hint_pos=hint_pos)
            return find_all_text_on_screen(text, timeout=2.0, hint_pos=hint_pos)

        # Use the screenshot Gemini already analyzed
        region = None
        if self._monitor_rect:
            left, top, right, bottom = self._monitor_rect
            region = (left, top, right - left, bottom - top)

        return find_all_text_in_image(self._current_screenshot, text, hint_pos=hint_pos, region=region)

    def _validate_bbox_in_image(
        self, bx: int, by: int, bw: int, bh: int, img_w: int, img_h: int, label: str = ""
    ) -> Optional[Tuple[int, int, int, int]]:
        """Validate and sanitize a bounding box against image dimensions.

        Applies Agent-S3-style coordinate clamping and sanity checks:
        - Rejects explicit "not found" (-1, -1)
        - Rejects full-screen boxes (area > 50% of image)
        - Clamps coordinates that exceed image bounds
        - Rejects boxes that are impossibly large or small

        Returns sanitized (bx, by, bw, bh) or None if invalid.
        """
        prefix = f"  [BBOX-VALIDATE{' ' + label if label else ''}]"

        # Check explicit "not found" signal
        if bx < 0 or by < 0:
            print(f"{prefix} REJECTED: negative coords ({bx},{by}) = 'not found'")
            if self._debug_mode:
                self._log_debug(f"BBOX REJECTED (not found): ({bx},{by},{bw},{bh})")
            return None

        if bw <= 0 or bh <= 0:
            print(f"{prefix} REJECTED: zero/negative size w={bw}, h={bh}")
            if self._debug_mode:
                self._log_debug(f"BBOX REJECTED (zero size): ({bx},{by},{bw},{bh})")
            return None

        # Check if coordinates are wildly outside image bounds (vision confused about space)
        if bx >= img_w * 1.5 or by >= img_h * 1.5:
            print(f"{prefix} REJECTED: coords ({bx},{by}) far outside image ({img_w}x{img_h})")
            if self._debug_mode:
                self._log_debug(f"BBOX REJECTED (out of image): ({bx},{by},{bw},{bh}) vs image {img_w}x{img_h}")
            return None

        # Clamp coordinates to image bounds (Agent S3 pattern)
        orig_bx, orig_by = bx, by
        bx = max(0, min(bx, img_w - 1))
        by = max(0, min(by, img_h - 1))
        bw = max(1, min(bw, img_w - bx))
        bh = max(1, min(bh, img_h - by))
        if bx != orig_bx or by != orig_by:
            print(f"{prefix} CLAMPED: ({orig_bx},{orig_by}) -> ({bx},{by})")

        # Reject full-screen / oversized boxes (vision couldn't pinpoint element)
        bbox_area = bw * bh
        img_area = img_w * img_h
        area_ratio = bbox_area / img_area if img_area > 0 else 1.0

        if area_ratio > 0.50:
            print(f"{prefix} REJECTED: bbox covers {area_ratio:.0%} of image (full-screen detection failure)")
            if self._debug_mode:
                self._log_debug(f"BBOX REJECTED (full-screen): ({bx},{by},{bw},{bh}) area_ratio={area_ratio:.2%}")
            return None

        # Reject impossibly small boxes (< 3px in any dimension)
        if bw < 3 or bh < 3:
            print(f"{prefix} REJECTED: too small ({bw}x{bh})")
            return None

        print(f"{prefix} VALID: ({bx},{by},{bw},{bh}) area={area_ratio:.1%} of image")
        return (bx, by, bw, bh)

    def _find_element_with_vision(
        self, element_description: str, hint_pos: Tuple[int, int] = None
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Use vision model to find a UI element by asking for its bounding box directly.

        Two-pass approach (following Agent S3 patterns):
        1. Ask vision model for precise bounding box of the element
        2. If that fails and hint_pos provided, ask vision model to refine the hint
        3. Validate all coordinates at every stage

        Args:
            element_description: What to find (e.g., "Blank workbook button")
            hint_pos: Optional approximate location (in SCREEN coordinates)

        Returns:
            (x, y, w, h) bounding box in SCREEN coordinates, or None if not found
        """
        if not self._current_screenshot:
            print("  [WARNING] No current screenshot for vision detection")
            return None

        img_w, img_h = self._current_screenshot.size

        # Use the resized screenshot for the vision model (same as AI sees)
        resized = self._resize_screenshot(self._current_screenshot.copy())
        r_w, r_h = resized.size

        if self._debug_mode:
            self._log_debug(
                f"Vision Element Detection\n"
                f"  Target: {element_description}\n"
                f"  Original image: {img_w}x{img_h}\n"
                f"  Resized image: {r_w}x{r_h}\n"
                f"  Scale factor: {self._scale:.4f}x\n"
                f"  Monitor offset: {self._monitor_offset}\n"
                f"  Hint position: {hint_pos}",
                section="VISION DETECTION START"
            )

        # Pass 1: Ask vision model for bounding box directly
        prompt = f"""Look at this {r_w}x{r_h} screenshot. Find: "{element_description}"

Return bounding box as: {{"x":LEFT,"y":TOP,"w":WIDTH,"h":HEIGHT}}
Coordinates MUST be within 0-{r_w} for x/w and 0-{r_h} for y/h.
If not visible: {{"x":-1,"y":-1,"w":0,"h":0}}
ONLY output the JSON object, no other text."""

        try:
            response = self._vision_model.generate_content(
                prompt=prompt,
                image=resized,
                max_tokens=1024
            )

            response_text = response.text if hasattr(response, 'text') else str(response)
            response_text = response_text.strip()
            finish_reason = response.finish_reason if hasattr(response, 'finish_reason') else None

            print(f"  [VISION] Raw response ({len(response_text)} chars): {response_text[:200]}")
            if finish_reason:
                print(f"  [VISION] Finish reason: {finish_reason}")

            if self._debug_mode:
                self._log_debug(f"Vision element detection response: {response_text}")

            bbox = self._parse_bbox_response(response_text)

            if bbox:
                bx, by, bw, bh = bbox

                # CRITICAL: Validate bbox against resized image dimensions
                validated = self._validate_bbox_in_image(bx, by, bw, bh, r_w, r_h, label="Pass1")

                if validated:
                    bx, by, bw, bh = validated
                    # Scale from resized image to screen coordinates
                    sx = int(bx * self._scale) + self._monitor_offset[0]
                    sy = int(by * self._scale) + self._monitor_offset[1]
                    sw = int(bw * self._scale)
                    sh = int(bh * self._scale)

                    if self._debug_mode:
                        self._log_debug(
                            f"Coordinate Transformation:\n"
                            f"  Image coords: ({bx},{by},{bw},{bh})\n"
                            f"  Scale: {self._scale:.4f}x | Offset: {self._monitor_offset}\n"
                            f"  Screen coords: ({sx},{sy},{sw},{sh})\n"
                            f"  Calc: sx={bx}*{self._scale:.2f}+{self._monitor_offset[0]}={sx}  "
                            f"sy={by}*{self._scale:.2f}+{self._monitor_offset[1]}={sy}"
                        )

                    print(f"  [OK] Vision found element at ({sx},{sy}) size {sw}x{sh}")

                    # Save debug image
                    if self._debug_dir:
                        from PIL import ImageDraw
                        debug_img = resized.copy()
                        draw = ImageDraw.Draw(debug_img)
                        draw.rectangle([bx, by, bx + bw, by + bh], outline=(255, 0, 0), width=3)
                        safe_desc = element_description.replace(' ', '_')[:20]
                        debug_img.save(self._debug_dir / f"vision_found_{safe_desc}.png")

                    return (sx, sy, sw, sh)
                else:
                    print(f"  [INFO] Vision bbox rejected by validation")
            else:
                print(f"  [INFO] Vision model says element not found (returned -1 or unparseable)")

        except Exception as e:
            print(f"  [ERROR] Vision element detection failed: {e}")
            if self._debug_mode:
                import traceback
                self._log_debug(f"Vision detection exception:\n{traceback.format_exc()}")

        # Pass 2: If hint available, ask vision model to refine the hint area
        if hint_pos and hint_pos[0] >= 0 and hint_pos[1] >= 0:
            print(f"  [INFO] Trying hint refinement around ({hint_pos[0]},{hint_pos[1]})...")

            # Convert hint from screen coords to resized image coords
            hint_img_x = int((hint_pos[0] - self._monitor_offset[0]) / self._scale)
            hint_img_y = int((hint_pos[1] - self._monitor_offset[1]) / self._scale)

            # Clamp hint to image bounds (Agent S3 pattern)
            hint_img_x = max(0, min(hint_img_x, r_w - 1))
            hint_img_y = max(0, min(hint_img_y, r_h - 1))

            # Crop a region around the hint for focused analysis
            crop_size = 200  # pixels in resized image
            crop_left = max(0, hint_img_x - crop_size)
            crop_top = max(0, hint_img_y - crop_size)
            crop_right = min(r_w, hint_img_x + crop_size)
            crop_bottom = min(r_h, hint_img_y + crop_size)

            cropped = resized.crop((crop_left, crop_top, crop_right, crop_bottom))
            c_w, c_h = cropped.size

            if self._debug_mode:
                self._log_debug(
                    f"Hint Refinement Pass 2:\n"
                    f"  Screen hint: {hint_pos}\n"
                    f"  Image hint: ({hint_img_x},{hint_img_y})\n"
                    f"  Crop region: ({crop_left},{crop_top})-({crop_right},{crop_bottom})\n"
                    f"  Crop size: {c_w}x{c_h}"
                )

            refine_prompt = f"""This is a {c_w}x{c_h} cropped screenshot. Find: "{element_description}"

Return bounding box as: {{"x":LEFT,"y":TOP,"w":WIDTH,"h":HEIGHT}}
Coordinates MUST be within 0-{c_w} for x/w and 0-{c_h} for y/h.
If not visible: {{"x":-1,"y":-1,"w":0,"h":0}}
ONLY output the JSON object."""

            try:
                response2 = self._vision_model.generate_content(
                    prompt=refine_prompt,
                    image=cropped,
                    max_tokens=1024
                )

                response2_text = response2.text if hasattr(response2, 'text') else str(response2)
                print(f"  [VISION] Refinement response ({len(response2_text)} chars): {response2_text.strip()[:200]}")
                bbox2 = self._parse_bbox_response(response2_text.strip())

                if bbox2:
                    bx, by, bw, bh = bbox2

                    # Validate bbox against CROP dimensions
                    validated2 = self._validate_bbox_in_image(bx, by, bw, bh, c_w, c_h, label="Pass2-Crop")

                    if validated2:
                        bx, by, bw, bh = validated2
                        # Map from crop coords to screen coords
                        sx = int((bx + crop_left) * self._scale) + self._monitor_offset[0]
                        sy = int((by + crop_top) * self._scale) + self._monitor_offset[1]
                        sw = int(bw * self._scale)
                        sh = int(bh * self._scale)
                        print(f"  [OK] Vision refined hint to ({sx},{sy}) size {sw}x{sh}")

                        if self._debug_mode:
                            self._log_debug(
                                f"Pass 2 Success:\n"
                                f"  Crop coords: ({bx},{by},{bw},{bh})\n"
                                f"  Screen coords: ({sx},{sy},{sw},{sh})"
                            )
                        return (sx, sy, sw, sh)

            except Exception as e:
                print(f"  [ERROR] Hint refinement failed: {e}")

        # All passes failed - return None (do NOT fabricate a box around hint)
        print(f"  [FAILED] Vision could not find '{element_description}' in any pass")
        if self._debug_mode:
            self._log_debug(f"Vision Detection FAILED for: {element_description}")
        return None

    def _parse_bbox_response(self, response_text: str) -> Optional[Tuple[int, int, int, int]]:
        """Parse bounding box from vision model response.

        Handles multiple formats:
        1. Complete JSON: {"x": 148, "y": 339, "w": 100, "h": 60}
        2. Partial/truncated JSON: {"x": 148, "y": 339
        3. Comma-separated: 148, 339, 100, 60
        4. Space-separated: 148 339 100 60

        NOTE: Validation against image bounds is done by _validate_bbox_in_image().
        This method only parses; the caller validates.
        """
        import json
        import re

        text = response_text.strip()

        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        result = None

        # Strategy 1: Try complete JSON
        match = re.search(r'\{[^}]*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                x = int(data.get('x', -1))
                y = int(data.get('y', -1))
                w = int(data.get('w', 0))
                h = int(data.get('h', 0))
                result = (x, y, w, h)
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        # Strategy 2: Extract named values from partial JSON (handles truncated responses)
        if result is None:
            x_match = re.search(r'"x"\s*:\s*(-?\d+)', text)
            y_match = re.search(r'"y"\s*:\s*(-?\d+)', text)
            w_match = re.search(r'"w"\s*:\s*(-?\d+)', text)
            h_match = re.search(r'"h"\s*:\s*(-?\d+)', text)

            if x_match and y_match:
                x = int(x_match.group(1))
                y = int(y_match.group(1))
                w = int(w_match.group(1)) if w_match else 80  # default size
                h = int(h_match.group(1)) if h_match else 50
                result = (x, y, w, h)

        # Strategy 3: Look for 4 comma-separated or space-separated numbers
        if result is None:
            nums = re.findall(r'-?\d+', text)
            if len(nums) >= 4:
                result = (int(nums[0]), int(nums[1]), int(nums[2]), int(nums[3]))
            elif len(nums) >= 2:
                x, y = int(nums[0]), int(nums[1])
                w = int(nums[2]) if len(nums) > 2 else 80
                h = int(nums[3]) if len(nums) > 3 else 50
                result = (x, y, w, h)

        if result:
            if self._debug_mode:
                self._log_debug(f"Parsed bbox: {result} from response: {text[:100]}")
            return result

        print(f"  [WARNING] Could not parse coordinates from: {text[:200]}")
        return None

    def _verify_correct_match(
        self, text: str, all_matches: List[Tuple[int, int, int, int]], context: str
    ) -> Tuple[int, int, int, int] | None:
        """
        Ask Gemini to verify which match is correct by showing numbered crops.
        Each crop has a clear number label (0, 1, 2...) with a colored border.
        """
        from PIL import Image, ImageDraw, ImageFont
        
        print(f"  Verifying {len(all_matches)} candidates with Gemini...")
        
        # Take full screenshot once
        full_screenshot = capture_selected_monitor()
        
        # Create numbered crops with borders
        numbered_crops = []
        for i, (x, y, w, h) in enumerate(all_matches):
            pad = 50
            crop = full_screenshot.crop((
                max(0, x - pad),
                max(0, y - pad),
                min(full_screenshot.width, x + w + pad),
                min(full_screenshot.height, y + h + pad)
            ))
            
            # Add numbered border and label
            border_width = 8
            label_height = 40
            
            # Create new image with space for border and label
            new_width = crop.width + border_width * 2
            new_height = crop.height + border_width * 2 + label_height
            numbered = Image.new('RGB', (new_width, new_height), (255, 255, 255))
            
            # Draw colored border (different color for each option for clarity)
            draw = ImageDraw.Draw(numbered)
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 165, 0), 
                      (255, 0, 255), (0, 255, 255), (255, 255, 0), (128, 0, 128)]
            border_color = colors[i % len(colors)]
            
            # Draw thick border
            for b in range(border_width):
                draw.rectangle(
                    [b, label_height + b, new_width - 1 - b, new_height - 1 - b],
                    outline=border_color
                )
            
            # Paste original crop inside border
            numbered.paste(crop, (border_width, label_height + border_width))
            
            # Draw large number label at top
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except:
                font = ImageFont.load_default()
            
            label_text = f"Option {i}"
            bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (new_width - text_width) // 2
            
            # Background for label
            draw.rectangle([0, 0, new_width, label_height], fill=(240, 240, 240))
            draw.text((text_x, 5), label_text, fill=(0, 0, 0), font=font)
            
            numbered_crops.append((i, numbered, (x, y, w, h)))
        
        # Debug: save individual numbered crops
        if self._debug_dir:
            self._verify_save_count += 1
            n = self._verify_save_count
            for i, crop, bbox in numbered_crops:
                crop.save(self._debug_dir / f"verify_{n:02d}_crop_{i}_numbered.png")
        
        # Create composite: arrange crops in a grid (max 3 per row for clarity)
        crops_per_row = 3
        rows = (len(numbered_crops) + crops_per_row - 1) // crops_per_row
        
        max_width_per_crop = max(c[1].width for c in numbered_crops)
        max_height_per_crop = max(c[1].height for c in numbered_crops)
        
        composite_width = max_width_per_crop * min(len(numbered_crops), crops_per_row)
        composite_height = max_height_per_crop * rows
        
        composite = Image.new('RGB', (composite_width, composite_height), (255, 255, 255))
        
        for idx, (i, crop, bbox) in enumerate(numbered_crops):
            row = idx // crops_per_row
            col = idx % crops_per_row
            x_pos = col * max_width_per_crop
            y_pos = row * max_height_per_crop
            composite.paste(crop, (x_pos, y_pos))
        
        # Resize if too large (keep readable)
        if composite.width > 1200 or composite.height > 800:
            ratio = min(1200 / composite.width, 800 / composite.height)
            composite = composite.resize(
                (int(composite.width * ratio), int(composite.height * ratio)), 
                Image.LANCZOS
            )
        
        # Debug: save composite
        if self._debug_dir:
            composite.save(self._debug_dir / f"verify_{n:02d}_composite_numbered.png")
            self._log_debug(f"\n--- Verification #{n} (text='{text}') ---")
            self._log_debug(f"  Matches: {len(all_matches)} candidates")
        
        prompt = f"""Look at this image showing {len(all_matches)} options for "{text}".
Context: {context}

Each option is clearly labeled (Option 0, Option 1, Option 2, etc) with a colored border.

Which option shows the CORRECT "{text}" to click? Consider:
- Exact application name (not similar apps like "{text}++")
- The user wants to open "{text}", not a web search or similar tool
- Ignore search suggestions or input boxes

Return ONLY the option number (0, 1, 2, etc) or -1 if none match.
Reply with exactly one number on the first line. No explanation, no markdown, no other text."""
        
        if self._debug_dir:
            self._log_debug(
                f"Visual Verification Request:\n"
                f"  Query: '{text}'\n"
                f"  Candidates: {len(all_matches)}\n"
                f"  Composite Image: verify_{n:02d}_composite_numbered.png\n"
                f"  Context: {context}",
                section="VISUAL VERIFICATION"
            )
            self._log_debug(f"Prompt to AI:\n{prompt}\n")

        try:
            # Use vision model abstraction for verification
            response = self._vision_model.generate_content(
                prompt=prompt,
                image=composite,
                max_tokens=32,
                temperature=0
            )
            
            # Check if response has content
            if not response.text:
                if self._debug_dir:
                    self._log_debug(f"AI Response: EMPTY (finish_reason: {response.finish_reason})")
                print(f"  AI returned empty response (finish_reason: {response.finish_reason})")
                return None
            
            answer = response.text.strip()
            if self._debug_dir:
                self._log_debug(f"AI Response: {answer!r}")
            
            # Parse choice: AI may return "4" or "4\n\n**Explanation:** ..." - take first integer
            choice = None
            match = re.search(r'-?\d+', answer)
            if match:
                choice = int(match.group())
            
            if choice is not None and 0 <= choice < len(all_matches):
                print(f"  AI chose option {choice}")
                if self._debug_dir:
                    selected_bbox = all_matches[choice]
                    self._log_debug(
                        f"AI Selection Result:\n"
                        f"  Chosen Option: {choice}\n"
                        f"  Bounding Box: {selected_bbox}\n"
                        f"  [OK] Valid choice"
                    )
                return all_matches[choice]
            else:
                if self._debug_dir:
                    self._log_debug(
                        f"AI returned invalid choice: {choice!r} (need integer in range 0-{len(all_matches)-1})"
                    )
        except Exception as e:
            print(f"  Verification failed: {e}")
            if self._debug_dir:
                import traceback
                self._log_debug(f"Verification Error:\n{traceback.format_exc()}")
        
        # Verification failed - return None so caller can fall back to Enter
        return None

    def _smart_filter_best_match(
        self, query: str, all_matches: List[Tuple[int, int, int, int]]
    ) -> Tuple[int, int, int, int] | None:
        """
        Smart OCR-based filter to pick the best match when Gemini verification fails.

        Windows Search layout:
        - Search panel appears on RIGHT side of screen
        - Results are in BOTTOM-RIGHT quadrant
        - Title bars and VS Code text are in LEFT/UPPER areas

        Strategy: Filter matches to only those in the search results area.
        """
        print(f"  Smart filter: analyzing {len(all_matches)} matches for '{query}'...")

        if not self._monitor_rect:
            # No monitor info, fall back to first match
            return all_matches[0] if all_matches else None

        left, top, right, bottom = self._monitor_rect
        screen_width = right - left
        screen_height = bottom - top

        # Windows search panel is typically in the RIGHT 40% of screen, BOTTOM 80%
        search_panel_left = left + int(screen_width * 0.60)  # Right 40%
        search_panel_top = top + int(screen_height * 0.20)   # Skip top 20% (title bars)

        # Filter matches to only those in search results area
        results_area_matches = []
        for i, (x, y, w, h) in enumerate(all_matches):
            # Check if match is in search panel area
            in_search_panel = (x >= search_panel_left and y >= search_panel_top)

            if in_search_panel:
                results_area_matches.append((x, y, w, h))
                print(f"    Match {i} at ({x},{y}): IN search panel -> KEEP")
            else:
                print(f"    Match {i} at ({x},{y}): Outside search panel (probably VS Code/title bar) -> SKIP")

        if not results_area_matches:
            print(f"    No matches in search panel area, using ALL matches as fallback")
            results_area_matches = all_matches

        # Take screenshot to analyze match context
        full_screenshot = capture_selected_monitor()
        from PIL import Image, ImageDraw

        scored_matches = []

        for i, (x, y, w, h) in enumerate(results_area_matches):
            score = 0

            # Crop region around match for context analysis
            pad = 100
            crop = full_screenshot.crop((
                max(0, x - pad),
                max(0, y - pad),
                min(full_screenshot.width, x + w + pad),
                min(full_screenshot.height, y + h + pad)
            ))

            # Convert to grayscale for analysis
            gray = crop.convert('L')
            pixels = list(gray.getdata())
            avg_brightness = sum(pixels) / len(pixels)

            # Rule 1: Prefer matches in "Apps" or "Best match" sections (darker backgrounds)
            if avg_brightness < 80:  # Dark background (app tiles)
                score += 50
                print(f"    Match {i} at ({x},{y}): Dark background (+50) -> score={score}")

            # Rule 2: Penalize very bright backgrounds (search suggestions, headers)
            if avg_brightness > 150:
                score -= 30
                print(f"    Match {i} at ({x},{y}): Bright background (-30) -> score={score}")

            # Rule 3: Prefer matches in bottom half of search panel (where app results are)
            if self._monitor_rect:
                _, top, _, bottom = self._monitor_rect
                mid_y = (top + bottom) // 2
                if y > mid_y:
                    score += 20
                    print(f"    Match {i} at ({x},{y}): Bottom half (+20) -> score={score}")
            
            # Rule 4: Penalize matches at top (likely category headers or search box)
            if y < 150:
                score -= 40
                print(f"    Match {i} at ({x},{y}): Top region (-40) -> score={score}")
            
            # Rule 5: Prefer larger bounding boxes (app tiles vs small text)
            area = w * h
            if area > 5000:
                score += 15
                print(f"    Match {i} at ({x},{y}): Large area {area} (+15) -> score={score}")
            
            scored_matches.append((score, i, (x, y, w, h)))
        
        # Sort by score (highest first)
        scored_matches.sort(reverse=True, key=lambda x: x[0])
        
        if scored_matches and scored_matches[0][0] > 0:
            best_score, best_i, best_bbox = scored_matches[0]
            print(f"  Smart filter: chose match {best_i} with score {best_score}")
            return best_bbox
        
        print(f"  Smart filter: no good matches found")
        return None

    def _ensure_window_focus_at(self, x: int, y: int) -> None:
        """
        Ensure the window at coordinates (x, y) is the foreground window.
        This is CRITICAL on Windows - clicks only work on the focused window.
        """
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # Set proper ctypes signatures (WindowFromPoint takes POINT by value)
            user32.WindowFromPoint.argtypes = [wintypes.POINT]
            user32.WindowFromPoint.restype = wintypes.HWND
            user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
            user32.GetAncestor.restype = wintypes.HWND
            user32.GetForegroundWindow.restype = wintypes.HWND
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.SetForegroundWindow.restype = wintypes.BOOL

            # Get the window at the click position
            point = wintypes.POINT(x, y)
            hwnd_at_point = user32.WindowFromPoint(point)

            if not hwnd_at_point:
                return

            # Get the top-level ancestor (the actual app window)
            GA_ROOT = 2
            hwnd_root = user32.GetAncestor(hwnd_at_point, GA_ROOT)
            if hwnd_root:
                hwnd_at_point = hwnd_root

            # Check if it's already the foreground window
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd == hwnd_at_point:
                return  # Already focused

            # Bring the window to front
            user32.SetForegroundWindow(hwnd_at_point)
            time.sleep(0.3)  # Wait for focus transition

            # Verify focus was acquired
            new_fg = user32.GetForegroundWindow()
            if new_fg == hwnd_at_point:
                print(f"  [FOCUS] Activated window at ({x},{y})")
            else:
                # Fallback: Alt-tab trick to force focus
                # Windows blocks SetForegroundWindow unless current process owns focus
                # Pressing Alt first tricks Windows into allowing the focus change
                import pyautogui
                pyautogui.keyDown('alt')
                time.sleep(0.05)
                user32.SetForegroundWindow(hwnd_at_point)
                pyautogui.keyUp('alt')
                time.sleep(0.2)
                print(f"  [FOCUS] Force-activated window at ({x},{y})")

        except Exception as e:
            # Non-critical: if focus fails, try clicking anyway
            print(f"  [FOCUS] Could not activate window: {e}")

    def _smooth_click(self, x: int, y: int, retries: int = 2) -> None:
        """
        Move cursor smoothly to position and click.
        Ensures target window has focus first.
        Retries if click has no effect (screenshot unchanged).
        """
        # CRITICAL: Ensure target window is focused before clicking
        self._ensure_window_focus_at(x, y)

        for attempt in range(retries + 1):
            result = self._mouse_controller.click_at(x, y, show_movement=(attempt == 0))
            if result.success:
                if attempt == 0:
                    print(f"  Clicked ({x},{y})")
                else:
                    print(f"  Retry click #{attempt} at ({x},{y})")
                return
            else:
                print(f"  [Warning] Click attempt {attempt+1} failed: {result.message}")
                if attempt < retries:
                    time.sleep(0.3)

        print(f"  [Warning] All click attempts failed at ({x},{y})")

    def _find_taskbar_search_bbox(self) -> str | None:
        """Find the Windows taskbar search area using Win32 API."""
        try:
            import ctypes
            import sys
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            taskbar_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if not taskbar_hwnd:
                return self._estimate_search_bbox()

            rect = wintypes.RECT()
            user32.GetWindowRect(taskbar_hwnd, ctypes.byref(rect))

            tb_left = rect.left
            tb_top = rect.top
            tb_right = rect.right
            tb_bottom = rect.bottom
            tb_width = tb_right - tb_left
            tb_height = tb_bottom - tb_top

            win_build = sys.getwindowsversion().build

            if win_build >= 22000:
                # Windows 11: taskbar icons are CENTERED by default.
                # Search icon is just right of the Start button, near the center.
                center = tb_left + tb_width // 2
                search_x = center - 30
                search_w = 60
            else:
                # Windows 10: search box is on the left side of taskbar
                search_x = tb_left + int(tb_width * 0.03)
                search_w = int(tb_width * 0.20)

            search_y = tb_top
            search_h = tb_height

            return f"{search_x},{search_y},{search_w},{search_h}"
        except Exception:
            return self._estimate_search_bbox()

    def _estimate_search_bbox(self) -> str | None:
        """Fallback: estimate search area from monitor rect."""
        if not self._monitor_rect:
            return None
        left, top, right, bottom = self._monitor_rect
        width = right - left
        # Default to center (Windows 11 style)
        center = left + width // 2
        x = center - 30
        y = bottom - 48
        w = 60
        h = 48
        return f"{x},{y},{w},{h}"

    def _find_all_text_in_results_area(
        self, text: str, hint_pos: Tuple[int, int] | None = None
    ) -> List[Tuple[int, int, int, int]]:
        """
        Find ALL occurrences of text in the upper 70% of the monitor
        (search results area). Used to disambiguate e.g. "Notepad" app
        vs "Notepad" in an open window's title bar.

        Uses current screenshot (no re-capture).
        """
        from core.ocr_finder import find_all_text_in_image

        if not self._current_screenshot:
            print("  [WARNING] No current screenshot, falling back to screen capture")
            from core.ocr_finder import find_all_text_on_screen
            if self._monitor_rect:
                left, top, right, bottom = self._monitor_rect
                height = bottom - top
                results_region = (left, top, right - left, int(height * 0.70))
                matches = find_all_text_on_screen(text, region=results_region, timeout=2.0, hint_pos=hint_pos)
                result_band = [m for m in matches if m[1] >= 80]
                return result_band if result_band else matches
            return find_all_text_on_screen(text, timeout=2.0, hint_pos=hint_pos)

        if self._monitor_rect:
            left, top, right, bottom = self._monitor_rect
            height = bottom - top
            results_region = (left, top, right - left, int(height * 0.70))
            matches = find_all_text_in_image(self._current_screenshot, text, hint_pos=hint_pos, region=results_region)
            # Drop title-bar matches (y < 80)
            result_band = [m for m in matches if m[1] >= 80]
            return result_band if result_band else matches

        return find_all_text_in_image(self._current_screenshot, text, hint_pos=hint_pos)

    def _find_text_in_results_area(
        self, text: str
    ) -> Tuple[int, int, int, int] | None:
        """
        Find text in the upper 70% of the monitor only.
        This avoids matching the typed query in the search input bar
        (which sits near the bottom) instead of the actual search result.
        """
        from core.ocr_finder import find_text_on_screen

        if self._monitor_rect:
            left, top, right, bottom = self._monitor_rect
            height = bottom - top
            # Only search upper 70% of screen (where results appear)
            results_region = (left, top, right - left, int(height * 0.70))
            bbox = find_text_on_screen(text, region=results_region, timeout=2.0)
            if bbox:
                return bbox
            # If not found in upper area, try full screen as fallback
            full_region = (left, top, right - left, height)
            return find_text_on_screen(text, region=full_region, timeout=1.0)
        return find_text_on_screen(text, timeout=2.0)

    def _log_debug(self, message: str, section: str = None) -> None:
        """Write debug message to log file with optional section headers."""
        if self._debug_mode and self._debug_log:
            with open(self._debug_log, "a", encoding="utf-8") as f:
                if section:
                    f.write(f"\n{'='*70}\n")
                    f.write(f"{section}\n")
                    f.write(f"{'='*70}\n")
                f.write(f"{message}\n")
    
    def _log_action_execution(self, step: int, action_type: str, target: str, success: bool, details: str = ""):
        """Log detailed action execution results."""
        if self._debug_mode:
            status = "[OK] SUCCESS" if success else "✗ FAILED"
            self._log_debug(
                f"Action: {action_type}\n"
                f"Target: {target}\n"
                f"Status: {status}\n"
                f"Details: {details}",
                section=f"Step {step} - EXECUTION RESULT"
            )
