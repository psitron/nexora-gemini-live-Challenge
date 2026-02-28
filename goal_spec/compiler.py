from __future__ import annotations

"""
Hybrid AI Agent – GoalSpec compiler (simplified v1).

Turns a natural language goal string into a small GoalSpec object that
other modules can inspect. Full NL → formal constraint compilation is
reserved for v2; here we keep it intentionally lightweight.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GoalConstraint:
    """
    Minimal representation of a constraint extracted from the goal.

    Examples:
    - type="safety", value="no destructive actions"
    - type="scope", value="only E:/projects"
    """

    type: str
    value: str


@dataclass
class GoalSpec:
    """
    Simplified goal specification:
    - raw_text: original natural language goal
    - summary: short one-line summary
    - constraints: optional list of textual constraints
    """

    raw_text: str
    summary: str
    constraints: List[GoalConstraint]


class GoalSpecCompiler:
    """
    v1 compiler:
    - For now, uses simple heuristics on the goal text to extract a
      summary and a very small set of obvious constraints.
    - In v2, this will be replaced or augmented with an LLM-backed
      compiler as described in the PRD.
    """

    def compile(self, goal_text: str) -> GoalSpec:
        goal_text = goal_text.strip()
        summary = self._summarise(goal_text)
        constraints = self._extract_constraints(goal_text)
        return GoalSpec(raw_text=goal_text, summary=summary, constraints=constraints)

    def _summarise(self, goal_text: str) -> str:
        """
        Very small heuristic summary: first sentence or truncated text.
        """
        if not goal_text:
            return ""
        # Split on common sentence delimiters.
        for sep in [".", "!", "?"]:
            if sep in goal_text:
                first = goal_text.split(sep, 1)[0]
                return first.strip()[:200]
        return goal_text[:200]

    def _extract_constraints(self, goal_text: str) -> List[GoalConstraint]:
        """
        Heuristically detect a few simple constraint phrases.
        This is intentionally conservative and only recognises obvious patterns.
        """
        constraints: List[GoalConstraint] = []
        lower = goal_text.lower()

        if "read-only" in lower or "read only" in lower:
            constraints.append(GoalConstraint(type="safety", value="read_only"))
        if "no delete" in lower or "do not delete" in lower:
            constraints.append(GoalConstraint(type="safety", value="no_delete"))
        if "do not modify" in lower or "no changes" in lower:
            constraints.append(GoalConstraint(type="safety", value="no_modify"))

        # Scope hints
        if "only in e:\\" in lower or "only under e:\\" in lower:
            constraints.append(GoalConstraint(type="scope", value="only_E_drive"))

        return constraints
