from __future__ import annotations

"""
Hybrid AI Agent – AgentLoop.

Synchronous loop that:
- Plans steps for a goal using LLM
- Maps each step to concrete tool actions
- Executes actions through the hierarchy (L0-L5)
- Waits for apps to load between steps
- Captures state and verifies outcomes
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import time

from config.settings import get_settings
from core.state_model import StateModel
from core.goal_tracker import GoalTracker
from core.governance_budget import BudgetConfig, GovernanceBudget
from core.planner_task import TaskPlanner, TaskPlan
from core.action_mapper import ActionMapper, ActionSpec
from core.reflection_agent import ReflectionAgent
from core.trajectory_manager import TrajectoryManager
from execution.hierarchy import ExecutionHierarchy
from verifier.outcome_classifier import Outcome, OutcomeLabel
from perception.visual.screenshot import capture_selected_monitor
from PIL import Image


@dataclass
class AgentLoopResult:
    goal_status: str
    steps_executed: int
    final_node_id: int
    outcomes: List[Outcome]


class AgentLoop:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.task_planner = TaskPlanner()
        self.exec_hierarchy = ExecutionHierarchy()
        self._action_mapper = ActionMapper(self.settings)

        # New Agent S3-inspired components
        self.reflection_agent = ReflectionAgent()
        self.trajectory_manager = TrajectoryManager(max_images=8)

    def run(self, goal: str) -> AgentLoopResult:
        state = StateModel()
        state.clear_knowledge()  # Start fresh
        self.trajectory_manager.clear()  # Clear trajectory

        goal_tracker = GoalTracker(description=goal, max_retries=3)
        budget_cfg = BudgetConfig(
            max_steps=self.settings.runtime.max_steps_per_run,
            max_seconds=self.settings.runtime.max_seconds_per_run,
            max_llm_tokens=self.settings.runtime.max_llm_tokens_per_run,
        )
        budget = GovernanceBudget(config=budget_cfg)

        plan: TaskPlan = self.task_planner.plan(goal)
        outcomes: List[Outcome] = []

        print(f"\nPlan ({len(plan.steps)} steps):")
        for step in plan.steps:
            print(f"  {step.index}. {step.description}")
        print()

        # Add initial knowledge
        state.add_knowledge(f"Goal: {goal}")
        state.add_knowledge(f"Plan has {len(plan.steps)} steps")

        for idx, step in enumerate(plan.steps, start=1):
            if budget.exhausted:
                print(f"\n  [BUDGET] Step budget exhausted after {budget.steps_used} steps")
                break

            print(f"\n--- Step {idx}/{len(plan.steps)}: {step.description} ---")

            action_specs: List[ActionSpec] = self._action_mapper.map_step(step, goal)

            if not action_specs:
                print(f"  [SKIP] Could not map step to actions")
                budget.record_step()
                continue

            step_success = True
            for action_idx, spec in enumerate(action_specs, start=1):
                print(f"  [{action_idx}] {spec.tool_name}({spec.kwargs})")

                # Capture BEFORE screenshot for reflection
                screenshot_before = self._safe_capture_screenshot()

                # Execute action
                result = self.exec_hierarchy.attempt(
                    spec.tool_name, state=state, **spec.kwargs
                )
                print(f"      -> {result.message} (success={result.success})")

                # Capture AFTER screenshot
                time.sleep(0.5)  # Let UI settle
                screenshot_after = self._safe_capture_screenshot()

                # Reflect on action - CRITICAL FIX: Pass execution result
                action_desc = f"{spec.tool_name}({spec.kwargs})"
                reflection = self.reflection_agent.reflect(
                    task_goal=goal,
                    last_action=action_desc,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after,
                    execution_result=result.success,
                    execution_message=result.message
                )

                print(f"      [Reflection] {reflection.progress_assessment}: {reflection.observations[:80]}")

                # Add to trajectory
                self.trajectory_manager.add_step(
                    step_number=idx * 10 + action_idx,  # Unique step number
                    action_description=action_desc,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after,
                    outcome="success" if result.success else "failure",
                    observations=reflection.observations
                )

                # Update knowledge buffer with discoveries
                if result.success:
                    state.add_knowledge(f"Completed: {action_desc}")
                    if reflection.state_changed:
                        state.add_knowledge(reflection.observations[:100])  # Add key observations

                if not result.success:
                    step_success = False

                # After opening an app, move it to PRIMARY_MONITOR and wait
                if result.success and spec.tool_name == "desktop_click":
                    print(f"  [WAIT] Waiting for application to load...")
                    state.add_knowledge("Application launched - waiting for load")
                    time.sleep(3)
                    try:
                        from execution.window_manager import move_foreground_to_primary_monitor
                        move_foreground_to_primary_monitor()
                    except Exception as e:
                        print(f"  [Window move failed: {e}]")
                elif result.success and spec.tool_name in ("keyboard_shortcut", "keyboard_press"):
                    time.sleep(1)

                state.invalidate()

            outcome = Outcome(
                label=OutcomeLabel.PASS if step_success else OutcomeLabel.NO_OP,
                reason=f"Step {idx} executed",
            )
            outcomes.append(outcome)
            budget.record_step()

        # Mark goal as complete if we executed all steps
        if budget.steps_used >= len(plan.steps):
            goal_tracker.record_success()

        # Print trajectory summary
        print(f"\n{self.trajectory_manager.get_text_summary()}")
        print(f"\n{state.get_knowledge_summary()}")

        return AgentLoopResult(
            goal_status=goal_tracker.status.value,
            steps_executed=budget.steps_used,
            final_node_id=0,
            outcomes=outcomes,
        )

    def _safe_capture_screenshot(self) -> Optional[Image.Image]:
        """Safely capture screenshot, returning None on failure."""
        try:
            return capture_selected_monitor()
        except Exception as e:
            print(f"[Screenshot capture failed: {e}]")
            return None

