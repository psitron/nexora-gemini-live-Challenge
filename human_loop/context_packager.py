from __future__ import annotations

"""
Hybrid AI Agent – human_loop.context_packager

Builds a compact context payload to show a human when the agent
escalates to the interactive loop.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from core.state_model import StateModel
from core.planner_task import TaskPlan
from verifier.outcome_classifier import Outcome


@dataclass
class HumanContext:
    goal: str
    plan_steps: List[str]
    last_outcome: str
    last_reason: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_human_context(
    goal: str,
    plan: TaskPlan,
    state: StateModel,
    last_outcome: Outcome | None,
    notes: str = "",
) -> HumanContext:
    """
    Construct a HumanContext from the current goal, plan, state, and last outcome.
    """
    plan_descriptions = [step.description for step in plan.steps]

    if last_outcome is None:
        outcome_label = "NONE"
        outcome_reason = ""
    else:
        outcome_label = last_outcome.label.value
        outcome_reason = last_outcome.reason

    return HumanContext(
        goal=goal,
        plan_steps=plan_descriptions,
        last_outcome=outcome_label,
        last_reason=outcome_reason,
        notes=notes,
    )

