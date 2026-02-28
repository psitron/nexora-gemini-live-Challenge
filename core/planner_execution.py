from __future__ import annotations

"""
Hybrid AI Agent – Execution Planner.

In the full system this routes actions through the execution hierarchy
and Verifier. For now it provides a minimal interface that can accept
TaskPlan steps and "execute" them by printing/logging.
"""

from dataclasses import dataclass
from typing import Iterable

from core.governance_budget import GovernanceBudget
from core.goal_tracker import GoalTracker
from core.planner_task import PlannedStep


@dataclass
class ExecutionResult:
    step: PlannedStep
    success: bool
    message: str


class ExecutionPlanner:
    """
    Minimal execution planner that iterates through planned steps and
    pretends to execute them, updating GoalTracker and GovernanceBudget.
    """

    def run_plan(
        self,
        steps: Iterable[PlannedStep],
        goal_tracker: GoalTracker,
        budget: GovernanceBudget,
    ) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []

        goal_tracker.start()
        budget.start()

        for step in steps:
            if budget.exhausted or not goal_tracker.can_retry:
                results.append(
                    ExecutionResult(
                        step=step,
                        success=False,
                        message="Budget exhausted or retries exceeded; skipping remaining steps.",
                    )
                )
                break

            budget.record_step()
            # For the initial skeleton we treat every step as a success.
            results.append(
                ExecutionResult(
                    step=step,
                    success=True,
                    message=f"Executed step {step.index}: {step.description}",
                )
            )

        if results and all(r.success for r in results):
            goal_tracker.record_success()

        return results

