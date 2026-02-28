from __future__ import annotations

"""
Hybrid AI Agent – GoalSpec validator (simplified v1).

Checks that a GoalSpec is structurally sound before execution. In later
versions this will enforce detailed formal constraints; for now it
performs basic sanity checks.
"""

from dataclasses import dataclass
from typing import List

from goal_spec.compiler import GoalSpec, GoalConstraint


@dataclass
class ValidationIssue:
    """
    Represents a non-fatal issue with a GoalSpec.
    """

    message: str


@dataclass
class ValidationResult:
    """
    Result of validating a GoalSpec.
    """

    ok: bool
    issues: List[ValidationIssue]


class GoalSpecValidator:
    """
    Minimal validator:
    - Ensures raw_text and summary are non-empty
    - Flags obviously contradictory constraints (best-effort)
    """

    def validate(self, spec: GoalSpec) -> ValidationResult:
        issues: List[ValidationIssue] = []

        if not spec.raw_text.strip():
            issues.append(ValidationIssue("Goal text is empty."))
        if not spec.summary.strip():
            issues.append(ValidationIssue("Goal summary is empty."))

        # Very small example of constraint consistency checking.
        has_read_only = any(
            c.type == "safety" and c.value == "read_only" for c in spec.constraints
        )
        has_no_modify = any(
            c.type == "safety" and c.value == "no_modify" for c in spec.constraints
        )
        if has_read_only and not has_no_modify:
            issues.append(
                ValidationIssue(
                    "read_only safety constraint present without explicit no_modify; "
                    "this is acceptable but may be redundant."
                )
            )

        ok = not any(msg.message.startswith("Goal text is empty") for msg in issues)
        return ValidationResult(ok=ok, issues=issues)
