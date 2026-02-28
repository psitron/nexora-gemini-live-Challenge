from __future__ import annotations

"""
Hybrid AI Agent – verifier.outcome_classifier

Classifies an action outcome as PASS, NO_OP, WRONG_STATE, TIMEOUT, or PARTIAL.
This minimal implementation uses the presence/absence of diffs plus a flag
from expectation matching.
"""

from dataclasses import dataclass
from enum import Enum

from verifier.diff_engine import DiffResult


class OutcomeLabel(str, Enum):
    PASS = "PASS"
    NO_OP = "NO_OP"
    WRONG_STATE = "WRONG_STATE"
    TIMEOUT = "TIMEOUT"
    PARTIAL = "PARTIAL"


@dataclass
class Outcome:
    label: OutcomeLabel
    reason: str


def classify_outcome(
    diff: DiffResult,
    expected_satisfied: bool,
    timed_out: bool = False,
) -> Outcome:
    if timed_out:
        return Outcome(OutcomeLabel.TIMEOUT, "Action exceeded allowed time.")

    if expected_satisfied and diff.has_changes:
        return Outcome(OutcomeLabel.PASS, "Expected changes observed in state.")

    if not diff.has_changes:
        return Outcome(OutcomeLabel.NO_OP, "No observable change in state.")

    # Changes happened, but expectations not met.
    return Outcome(OutcomeLabel.WRONG_STATE, "State changed but did not match expectations.")

