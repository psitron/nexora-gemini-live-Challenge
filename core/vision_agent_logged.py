"""
Vision Agent with Detailed Logging

This is a wrapper around VisionAgent that adds comprehensive logging:
- Every step with screenshots
- Every action with before/after images
- Every LLM interaction
- HTML report generation

Usage:
    from core.vision_agent_logged import VisionAgentLogged
    agent = VisionAgentLogged()
    result = agent.run("Your task here")
"""

from __future__ import annotations

import time
import os
from pathlib import Path
from PIL import Image
from typing import List, Dict

from core.vision_agent import VisionAgent, VisionAgentResult
from core.detailed_logger import DetailedLogger
from perception.visual.screenshot import capture_selected_monitor
from core.reflection_agent import ReflectionAgent
from core.state_model import StateModel


class VisionAgentLogged(VisionAgent):
    """VisionAgent with comprehensive detailed logging + reflection + self-correction"""

    def __init__(self, log_dir: str = None):
        """
        Initialize VisionAgent with detailed logging, reflection, and self-correction.

        Args:
            log_dir: Optional directory for logs (default: logs/YYYYMMDD_HHMMSS/)
        """
        super().__init__()
        self.logger: DetailedLogger = None
        self.log_dir = log_dir
        self._step_screenshots = {}  # Store screenshots for each step

        # NEW: Reflection and memory systems
        self.reflection_agent = ReflectionAgent()
        self.state = StateModel()
        self._structured_history: List[Dict] = []  # Structured action history with success/failure
        self._consecutive_failures = 0  # Track consecutive failed actions
        self._max_consecutive_failures = 5  # Stop if 5 actions fail in a row

    def run(self, goal: str) -> VisionAgentResult:
        """
        Run vision agent with detailed logging enabled.

        Creates logs directory with:
        - execution_log.txt (human-readable text log)
        - execution_log.json (machine-readable JSON)
        - execution_report.html (beautiful HTML report)
        - screenshots/ (all screenshots captured)
        """
        # Initialize logger
        self.logger = DetailedLogger(goal, self.log_dir)

        # Enable debug directory for visual verification crops
        # This ensures numbered crops (verify_01_crop_0.png, etc.) are saved
        self._debug_dir = self.logger.screenshots_dir

        print(f"\n[DetailedLogger] Logging enabled!")
        print(f"[DetailedLogger] Logs will be saved to: {self.logger.output_dir}")
        print(f"[DetailedLogger] Debug screenshots (visual verification crops) will be saved to: {self._debug_dir}\n")

        try:
            # Capture initial screenshot
            initial_screenshot = self._safe_capture_screenshot()
            if initial_screenshot:
                self.logger.log_custom(
                    phase="initialization",
                    action="capture_initial_state",
                    details={
                        "description": "Initial desktop state before task execution",
                        "goal": goal,
                        "max_steps": self.MAX_STEPS,
                        "vision_model": self._vision_model.get_model_name(),
                        "educational_mode": self._mouse_controller.educational_mode
                    },
                    success=True,
                    screenshot=initial_screenshot
                )

            # Override the parent's run to add logging hooks
            result = self._run_with_logging(goal)

            # Capture final screenshot
            final_screenshot = self._safe_capture_screenshot()
            if final_screenshot:
                self.logger.log_custom(
                    phase="finalization",
                    action="capture_final_state",
                    details={
                        "description": "Final desktop state after task execution",
                        "result": "SUCCESS" if result.success else "INCOMPLETE",
                        "steps_executed": result.steps_executed,
                        "message": result.message
                    },
                    success=result.success,
                    screenshot=final_screenshot
                )

            # Finalize and generate report
            report_path = self.logger.finalize()

            print(f"\n{'='*70}")
            print(f"DETAILED LOGS AVAILABLE:")
            print(f"{'='*70}")
            print(f"Open this file in your browser to see everything:")
            print(f"  {report_path}")
            print(f"{'='*70}\n")

            return result

        except Exception as e:
            if self.logger:
                self.logger.log_error(
                    error_type="execution_failure",
                    error_message=str(e),
                    context={"goal": goal, "max_steps": self.MAX_STEPS}
                )
                self.logger.finalize()
            raise

    def _is_stuck_in_loop(self, action_key: str, recent_count: int = 5, threshold: int = 3) -> bool:
        """
        Detect if we're repeating the same action too many times.

        Args:
            action_key: Current action key (e.g., "click_position:37,318")
            recent_count: How many recent actions to check
            threshold: How many repeats indicate a loop

        Returns:
            True if stuck in loop
        """
        if len(self._action_history) < threshold:
            return False

        recent = self._action_history[-recent_count:]
        repeat_count = recent.count(action_key)
        return repeat_count >= threshold

    def _validate_and_clamp_coordinates(self, x: int, y: int) -> tuple[int, int]:
        """
        Validate coordinates are within monitor bounds and clamp if needed.

        Args:
            x, y: Screen coordinates

        Returns:
            Clamped (x, y) coordinates
        """
        if not self._monitor_rect:
            return x, y

        mx, my, mw, mh = self._monitor_rect

        # Clamp to monitor bounds
        clamped_x = max(mx, min(x, mx + mw - 1))
        clamped_y = max(my, min(y, my + mh - 1))

        if clamped_x != x or clamped_y != y:
            print(f"  [Coordinate Clamp] ({x}, {y}) -> ({clamped_x}, {clamped_y})")

        return clamped_x, clamped_y

    def _format_structured_history(self) -> str:
        """
        Format structured history for AI with success/failure indicators.

        Returns:
            Formatted history string
        """
        if not self._structured_history:
            return "No previous actions yet."

        lines = []
        for i, entry in enumerate(self._structured_history[-6:], 1):  # Last 6 actions
            status_icon = "[OK]" if entry["success"] else "[X]"
            action_desc = entry["description"]

            # Add reflection if available
            if entry.get("reflection_summary"):
                lines.append(f"{status_icon} Step {entry['step']}: {action_desc}")
                lines.append(f"   -> {entry['reflection_summary']}")
            else:
                lines.append(f"{status_icon} Step {entry['step']}: {action_desc}")

        return "\n".join(lines)

    def _run_with_logging(self, goal: str) -> VisionAgentResult:
        """
        Run parent's logic but with logging at every step.

        This reimplements the parent's run() with logging hooks.
        """
        from perception.visual.screenshot import capture_selected_monitor

        # Log start
        self.logger.log_custom(
            phase="planning",
            action="start_vision_loop",
            details={
                "goal": goal,
                "max_steps": self.MAX_STEPS,
                "vision_model": self._vision_model.get_model_name()
            },
            success=None
        )

        print(f"\nGoal: {goal}")
        print(f"Monitor: {self._monitor_rect}")
        print()

        steps = 0
        consecutive_failures = 0
        previous_actions = []
        last_action_summary = ""

        while steps < self.MAX_STEPS:
            steps += 1

            print(f"\n{'='*60}")
            print(f"Step {steps}: Capturing screen...")

            # Capture BEFORE screenshot
            screenshot_before = self._safe_capture_screenshot()

            # Capture and process screenshot for AI
            screenshot = capture_selected_monitor()
            self._current_screenshot = screenshot  # ← FIX: Store for OCR (avoid re-capture)
            print(f"\n[SCREENSHOT INFO]:")
            print(f"   Original size: {screenshot.width} x {screenshot.height}")

            small_screenshot = self._resize_screenshot(screenshot)

            print(f"   Resized to: {small_screenshot.width} x {small_screenshot.height}")
            print(f"   Scale factor calculated: {self._scale:.4f}x")
            print(f"   (AI sees resized image, coordinates scaled back by {self._scale:.4f}x)")

            # Save full and resized screenshots for debugging
            if self._debug_dir:
                screenshot.save(self._debug_dir / f"step_{steps:02d}_full.png")
                small_screenshot.save(self._debug_dir / f"step_{steps:02d}_resized.png")

            print(f"\nStep {steps}: AI analyzing (scale={self._scale:.2f}x)...")

            # Prepare context for AI with structured history and knowledge
            knowledge_summary = self.state.get_knowledge_summary()
            formatted_history = self._format_structured_history()

            print(f"\n[CONTEXT FOR AI]:")
            print(f"  Knowledge buffer: {len(self.state.knowledge_buffer)} facts")
            print(f"  Recent actions: {len(self._structured_history)} steps")

            # Add knowledge buffer to previous_actions so AI can see accumulated facts
            actions_with_knowledge = previous_actions.copy()
            if self.state.knowledge_buffer:
                actions_with_knowledge.insert(0, f"KNOWN FACTS: {', '.join(self.state.knowledge_buffer[:5])}")

            # Ask AI with enhanced context
            action = self._ask_vision_ai(
                small_screenshot, goal, actions_with_knowledge,
                step_num=steps, last_action_summary=last_action_summary
            )

            if action is None:
                consecutive_failures += 1
                self.logger.log_custom(
                    phase="execution",
                    action="ai_analysis_failed",
                    details={
                        "step_number": steps,
                        "consecutive_failures": consecutive_failures,
                        "reason": "AI returned None"
                    },
                    success=False,
                    screenshot=screenshot_before
                )
                if consecutive_failures >= 3:
                    return VisionAgentResult(False, steps, "AI repeatedly failed to analyze screen")
                print(f"Step {steps}: AI failed ({consecutive_failures}/3), retrying...")
                time.sleep(1)
                continue

            consecutive_failures = 0

            # Scale hint coordinates WITH DETAILED LOGGING
            print(f"\n{'-'*60}")
            print(f"[COORDINATE TRANSFORMATION - Step {steps}]")
            print(f"{'-'*60}")

            # Store raw coordinates BEFORE any transformation
            raw_hint_x = action.hint_x if action.hint_x >= 0 else None
            raw_hint_y = action.hint_y if action.hint_y >= 0 else None

            if action.hint_x >= 0 and action.hint_y >= 0:
                print(f"  [ORIGINAL] AI coordinates on 1024px image:")
                print(f"     hint_x = {raw_hint_x}")
                print(f"     hint_y = {raw_hint_y}")
                print(f"\n  [SCALE FACTORS]:")
                print(f"     self._scale = {self._scale:.4f}x")
                print(f"     self._monitor_offset = {self._monitor_offset}")
                print(f"     self._monitor_rect = {self._monitor_rect}")

                # Apply scaling
                action.hint_x, action.hint_y = self._scale_hint_to_screen(
                    action.hint_x, action.hint_y
                )

                print(f"\n  [SCALED] Actual screen coordinates:")
                print(f"     screen_x = {action.hint_x}")
                print(f"     screen_y = {action.hint_y}")
                print(f"\n  [CALCULATION]:")
                print(f"     screen_x = {raw_hint_x} * {self._scale:.4f} + {self._monitor_offset[0]} = {action.hint_x}")
                print(f"     screen_y = {raw_hint_y} * {self._scale:.4f} + {self._monitor_offset[1]} = {action.hint_y}")

                # Validate and clamp coordinates to monitor bounds
                clamped_x, clamped_y = self._validate_and_clamp_coordinates(
                    action.hint_x, action.hint_y
                )

                # Store if clamping occurred
                was_clamped = (clamped_x != action.hint_x or clamped_y != action.hint_y)
                action.hint_x, action.hint_y = clamped_x, clamped_y

                if self._monitor_rect:
                    mx, my, mw, mh = self._monitor_rect
                    print(f"\n  [OK] Coordinates validated and within bounds: ({action.hint_x}, {action.hint_y})")
            else:
                print(f"  [WARNING] No hint coordinates (hint_x={action.hint_x}, hint_y={action.hint_y})")
                was_clamped = False

            print(f"{'-'*60}\n")

            print(f"Step {steps}: {action.action_type} -> {action.description}")
            if action.hint_x >= 0:
                print(f"  AI hint position: ({action.hint_x},{action.hint_y})")

            # Check if done
            if action.action_type == "done":
                screenshot_after = self._safe_capture_screenshot()
                self.logger.log_custom(
                    phase="completion",
                    action="task_completed",
                    details={
                        "step_number": steps,
                        "total_actions": len(previous_actions),
                        "message": action.description
                    },
                    success=True,
                    screenshot=screenshot_after
                )
                return VisionAgentResult(True, steps, action.description)

            # IMPROVED Loop detection
            action_key = f"{action.action_type}:{action.target}"

            if self._is_stuck_in_loop(action_key, recent_count=5, threshold=3):
                print(f"\n[LOOP] LOOP DETECTED: Repeated '{action_key}' 3 times in last 5 actions")
                print(f"  Recent history: {self._action_history[-5:]}")
                print(f"  Attempting to break loop...")

                # Try to break loop
                if action.action_type == "open_search":
                    print(f"  Closing search and continuing...")
                    import pyautogui
                    pyautogui.press("escape")
                    time.sleep(0.3)
                    continue
                elif action.action_type in ["click_text", "click_position"]:
                    print(f"  Skipping repeated click, trying next action...")
                    # Add failed action to history
                    self._action_history.append(f"SKIPPED:{action_key}")
                    self._structured_history.append({
                        "step": steps,
                        "action_type": action.action_type,
                        "description": f"SKIPPED: {action.description} (loop detected)",
                        "success": False,
                        "reflection_summary": "Loop detected - skipped to avoid infinite loop"
                    })
                    continue
                else:
                    print(f"  WARNING: Loop detected but no break strategy defined. Aborting task.")
                    return VisionAgentResult(False, steps, f"Stuck in loop - repeated '{action_key}' too many times")

            # Execute action
            action_success = self._execute_action(action)

            # Wait for UI to settle (action-specific timing)
            if action.action_type == "wait":
                time.sleep(2)
            elif action.action_type in ("open_search", "run_command"):
                time.sleep(1)
            elif action.action_type in ("click_text", "click_position"):
                time.sleep(0.8)
            else:
                time.sleep(0.5)

            # Capture AFTER screenshot
            screenshot_after = self._safe_capture_screenshot()

            # REFLECTION: Analyze if action succeeded and we're making progress
            print(f"\n[REFLECTION] Analyzing action result...")
            reflection = self.reflection_agent.reflect(
                task_goal=goal,
                last_action=action.description,
                screenshot_before=screenshot_before,
                screenshot_after=screenshot_after
            )

            print(f"  Action succeeded: {reflection.action_succeeded}")
            print(f"  State changed: {reflection.state_changed}")
            print(f"  Progress: {reflection.progress_assessment}")
            print(f"  Observations: {reflection.observations}")
            if reflection.next_action_guidance:
                print(f"  Guidance: {reflection.next_action_guidance}")

            # LOG REFLECTION RESULTS to file (not just console)
            self.logger.log_reflection(
                reflection_result=reflection,
                screenshot_before=screenshot_before,
                screenshot_after=screenshot_after
            )

            # Update knowledge buffer with observations
            if reflection.action_succeeded and reflection.observations:
                self.state.add_knowledge(reflection.observations)

            # Determine if this step should count as a failure
            # Only count ONCE per step (avoid double-counting failed+stuck)
            step_failed = False
            if not reflection.action_succeeded:
                action_success = False
                step_failed = True
                print(f"  [WARNING] Reflection determined action FAILED")
            elif reflection.progress_assessment == "stuck":
                step_failed = True
                print(f"  [WARNING] Agent appears STUCK - {reflection.observations}")

            if step_failed:
                self._consecutive_failures += 1
                print(f"  Consecutive failures: {self._consecutive_failures}/{self._max_consecutive_failures}")

                if self._consecutive_failures >= self._max_consecutive_failures:
                    print(f"\n[FAIL] STOPPING: {self._consecutive_failures} consecutive failures detected")
                    # Show only actually failed steps
                    failed_steps = [h for h in self._structured_history[-6:] if not h.get("success")]
                    for h in failed_steps[-self._max_consecutive_failures:]:
                        print(f"    - Step {h['step']}: {h['description']} -> {h.get('reflection_summary', 'N/A')}")

                    self.logger.log_custom(
                        phase="error",
                        action="consecutive_failures",
                        details={
                            "consecutive_failures": self._consecutive_failures,
                            "last_actions": self._structured_history[-self._consecutive_failures:]
                        },
                        success=False
                    )

                    return VisionAgentResult(
                        success=False,
                        steps_executed=steps,
                        message=f"Stopped due to {self._consecutive_failures} consecutive failures. Agent appears stuck."
                    )
            else:
                # Reset failure counter on success
                self._consecutive_failures = 0

            # Calculate annotation box position (40x40 box centered on click point)
            annotation_bbox = None
            if action.hint_x >= 0 and action.hint_y >= 0:
                box_size = 40
                annotation_bbox = {
                    "x": action.hint_x - box_size // 2,
                    "y": action.hint_y - box_size // 2,
                    "w": box_size,
                    "h": box_size,
                    "center_x": action.hint_x,
                    "center_y": action.hint_y,
                    "bbox_string": f"{action.hint_x - box_size//2},{action.hint_y - box_size//2},{box_size},{box_size}"
                }

            # LOG THE ACTION with full details including coordinate transformation AND reflection
            action_details = {
                "step_number": steps,
                "action_type": action.action_type,
                "target": action.target,
                "description": action.description,
                # Coordinate tracking: BOTH raw AI output AND final screen coordinates
                "coordinates": {
                    "raw_x": raw_hint_x,  # AI output in 1024px space
                    "raw_y": raw_hint_y,
                    "scaled_x": action.hint_x,  # Final screen coordinate
                    "scaled_y": action.hint_y,
                    "was_clamped": was_clamped,
                    "scale_factor": self._scale,
                    "monitor_offset": self._monitor_offset
                },
                # Annotation position (where red box appeared)
                "annotation": annotation_bbox,
                # Reflection analysis
                "reflection": {
                    "action_succeeded": reflection.action_succeeded,
                    "state_changed": reflection.state_changed,
                    "progress": reflection.progress_assessment,
                    "observations": reflection.observations,
                    "next_action_guidance": reflection.next_action_guidance
                },
                # Knowledge buffer state
                "knowledge_buffer": self.state.knowledge_buffer.copy() if self.state.knowledge_buffer else [],
                # Keep legacy fields for backward compatibility
                "hint_x": action.hint_x,
                "hint_y": action.hint_y,
                "success": action_success
            }

            # Create a result object
            result_obj = type('ActionResult', (), {
                'success': action_success,
                'message': action.description,
                'data': action_details
            })()

            # Log the action with before/after screenshots
            self.logger.log_action(
                action_name=action.action_type,
                parameters=action_details,
                result=result_obj,
                screenshot_before=screenshot_before,
                screenshot_after=screenshot_after
            )

            # Add to structured history with reflection
            self._structured_history.append({
                "step": steps,
                "action_type": action.action_type,
                "target": action.target,
                "description": action.description,
                "success": reflection.action_succeeded,
                "reflection_summary": reflection.observations[:100],  # Truncate for readability
                "progress": reflection.progress_assessment
            })

            # Add to action history (for loop detection)
            self._action_history.append(action_key)

            # Update simple history for backward compatibility
            status_icon = "[OK]" if reflection.action_succeeded else "[X]"
            action_summary = f"{status_icon} {action.description}"
            if reflection.observations:
                action_summary += f" -> {reflection.observations[:80]}"
            previous_actions.append(action_summary)

            # Update last action summary with reflection insights
            last_action_summary = f"{action.action_type} on {action.target}: "
            last_action_summary += "success" if reflection.action_succeeded else "failed"
            last_action_summary += f" ({reflection.progress_assessment})"

            # Update knowledge buffer if action succeeded
            if reflection.action_succeeded and action.action_type in ["open_search", "click_text", "type_text"]:
                fact = f"Successfully completed: {action.description}"
                self.state.add_knowledge(fact[:100])  # Keep facts concise

        # Max steps reached
        self.logger.log_custom(
            phase="timeout",
            action="max_steps_reached",
            details={
                "max_steps": self.MAX_STEPS,
                "actions_executed": len(previous_actions)
            },
            success=False
        )

        return VisionAgentResult(False, steps, f"Reached max steps ({self.MAX_STEPS})")

    def _safe_capture_screenshot(self):
        """Safely capture screenshot, return None if fails"""
        try:
            return capture_selected_monitor()
        except Exception as e:
            print(f"  [Warning] Failed to capture screenshot: {e}")
            return None
