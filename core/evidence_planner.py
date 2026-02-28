from __future__ import annotations

"""
Hybrid AI Agent – EvidencePlanner.

Decides what evidence to capture for a given action outcome.
This minimal version only returns a simple plan describing whether
to save a screenshot and/or structured diff.
"""

from dataclasses import dataclass

from verifier.outcome_classifier import Outcome, OutcomeLabel


@dataclass
class EvidencePlan:
    capture_screenshot: bool
    capture_diff: bool


class EvidencePlanner:
    def plan(self, outcome: Outcome) -> EvidencePlan:
        """
        Simple strategy:
        - PASS: capture diff only
        - NO_OP: capture nothing
        - WRONG_STATE / TIMEOUT / PARTIAL: capture screenshot + diff
        """
        if outcome.label == OutcomeLabel.PASS:
            return EvidencePlan(capture_screenshot=False, capture_diff=True)
        if outcome.label == OutcomeLabel.NO_OP:
            return EvidencePlan(capture_screenshot=False, capture_diff=False)
        # Problems or ambiguity
        return EvidencePlan(capture_screenshot=True, capture_diff=True)
