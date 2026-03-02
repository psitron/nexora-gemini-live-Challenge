"""
Enhanced AgentLoop with Detailed Logging

This version logs everything:
- Planning phase with LLM prompts/responses
- Every action execution
- Screenshots before/after each action
- Reflection agent analysis
- Final HTML report with all details
"""

from core.agent_loop import AgentLoop, AgentLoopResult
from core.detailed_logger import DetailedLogger
from perception.visual.screenshot import capture_selected_monitor
from PIL import Image


class AgentLoopLogged(AgentLoop):
    """AgentLoop with comprehensive detailed logging"""

    def __init__(self, log_dir: str = None):
        """Initialize with optional log directory"""
        super().__init__()
        self.logger: DetailedLogger = None
        self.log_dir = log_dir

    def run(self, goal: str, max_steps: int = 30) -> AgentLoopResult:
        """
        Run agent with detailed logging enabled.

        Creates logs directory with:
        - execution_log.txt (human-readable text log)
        - execution_log.json (machine-readable JSON)
        - execution_report.html (beautiful HTML report)
        - screenshots/ (all screenshots captured)
        """
        # Initialize logger
        self.logger = DetailedLogger(goal, self.log_dir)

        print(f"\n[DetailedLogger] Logging enabled!")
        print(f"[DetailedLogger] Logs will be saved to: {self.logger.output_dir}\n")

        try:
            # Capture initial screenshot
            initial_screenshot = self._safe_capture_screenshot()
            if initial_screenshot:
                self.logger.log_custom(
                    phase="initialization",
                    action="capture_initial_state",
                    details={"description": "Initial desktop state before task execution"},
                    success=True,
                    screenshot=initial_screenshot
                )

            # Run the actual agent loop with logging hooks
            result = self._run_with_logging(goal, max_steps)

            # Capture final screenshot
            final_screenshot = self._safe_capture_screenshot()
            if final_screenshot:
                self.logger.log_custom(
                    phase="finalization",
                    action="capture_final_state",
                    details={
                        "description": "Final desktop state after task execution",
                        "result": result.goal_status,
                        "steps_executed": result.steps_executed
                    },
                    success=True,
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
                    context={"goal": goal, "max_steps": max_steps}
                )
                self.logger.finalize()
            raise

    def _run_with_logging(self, goal: str, max_steps: int) -> AgentLoopResult:
        """Enhanced run method with logging at every step"""
        import time
        from execution.level0_programmatic import ActionResult
        from verifier.outcome_classifier import OutcomeLabel
        from core.state_model import StateModel

        # Initialize state
        state = StateModel()

        # 1. PLANNING PHASE
        print(f"[Planning task...]")
        self.logger.log_custom(
            phase="planning",
            action="start_planning",
            details={"goal": goal, "max_steps": max_steps},
            success=None
        )

        plan = self.task_planner.plan(goal)

        # Log the plan with LLM details
        self.logger.log_planning(
            plan=plan,
            llm_prompt=f"Plan this task: {goal}",
            llm_response=f"Generated plan with {len(plan.steps)} steps"
        )

        print(f"\nPlan ({len(plan.steps)} steps):")
        for i, step in enumerate(plan.steps, 1):
            print(f"  {i}. {step.description}")

        # 2. EXECUTION PHASE
        outcomes = []
        final_node_id = 0

        for step_idx, step in enumerate(plan.steps, 1):
            print(f"\n--- Step {step_idx}/{len(plan.steps)}: {step.description} ---")

            # Log step start
            self.logger.log_custom(
                phase="execution",
                action="start_step",
                details={
                    "step_number": step_idx,
                    "description": step.description,
                    "total_steps": len(plan.steps)
                },
                success=None
            )

            # Map step to actions
            action_specs = self.action_mapper.map(step.description, state)

            for action_idx, spec in enumerate(action_specs, start=1):
                print(f"  [{action_idx}] {spec.tool_name}({spec.kwargs})")

                # Capture BEFORE screenshot
                screenshot_before = self._safe_capture_screenshot()

                # EXECUTE ACTION
                result = self.exec_hierarchy.attempt(
                    spec.tool_name, state=state, **spec.kwargs
                )

                print(f"      -> {result.message} (success={result.success})")

                # Capture AFTER screenshot
                time.sleep(0.5)  # Let UI settle
                screenshot_after = self._safe_capture_screenshot()

                # LOG THE ACTION
                self.logger.log_action(
                    action_name=spec.tool_name,
                    parameters=spec.kwargs,
                    result=result,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after
                )

                # REFLECT ON ACTION
                action_desc = f"{spec.tool_name}({spec.kwargs})"
                reflection = self.reflection_agent.reflect(
                    task_goal=goal,
                    last_action=action_desc,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after
                )

                print(f"      [Reflection] {reflection.progress_assessment}: {reflection.observations[:80]}")

                # LOG THE REFLECTION
                self.logger.log_reflection(
                    reflection_result=reflection,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after
                )

                # Add to trajectory
                self.trajectory_manager.add_step(
                    step_number=final_node_id + 1,
                    action_description=action_desc,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after,
                    outcome=reflection.progress_assessment,
                    observations=reflection.observations
                )

                # Update knowledge buffer
                if reflection.observations:
                    state.add_knowledge(f"Completed: {action_desc}")
                    state.add_knowledge(f"Executed: {action_desc}")

                final_node_id += 1

                # Record outcome
                if result.success:
                    outcomes.append(OutcomeLabel.PASS)
                else:
                    outcomes.append(OutcomeLabel.WRONG_STATE)

            # Log step completion
            self.logger.log_custom(
                phase="execution",
                action="complete_step",
                details={
                    "step_number": step_idx,
                    "actions_executed": len(action_specs),
                    "description": step.description
                },
                success=True
            )

        # 3. FINALIZATION
        goal_status = "SUCCESS" if outcomes and outcomes[-1] == OutcomeLabel.PASS else "PARTIAL"

        self.logger.log_custom(
            phase="finalization",
            action="execution_complete",
            details={
                "goal_status": goal_status,
                "steps_executed": len(plan.steps),
                "total_actions": final_node_id,
                "outcomes": [o.value for o in outcomes],
                "knowledge_gained": len(state.knowledge_buffer)
            },
            success=True
        )

        # Print execution history
        print(f"\nExecution History ({final_node_id} steps):")
        history = self.trajectory_manager.get_trajectory_summary()
        for line in history.split('\n')[:20]:  # First 20 lines
            print(f"  {line}")

        # Print knowledge buffer
        if state.knowledge_buffer:
            print(f"\nKnown facts:")
            for fact in state.knowledge_buffer[:10]:  # First 10 facts
                print(f"- {fact}")

        print(f"\nResult: {goal_status}")
        print(f"Steps executed: {len(plan.steps)}")

        return AgentLoopResult(
            goal_status=goal_status,
            steps_executed=len(plan.steps),
            final_node_id=final_node_id,
            outcomes=outcomes
        )

    def _safe_capture_screenshot(self):
        """Safely capture screenshot, return None if fails"""
        try:
            return capture_selected_monitor()
        except Exception as e:
            print(f"  [Warning] Failed to capture screenshot: {e}")
            return None
