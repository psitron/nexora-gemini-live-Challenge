from __future__ import annotations

"""
Hybrid AI Agent – safety classifier.

Uses ToolContracts to classify each action by risk, and determines
whether confirmation or compensating actions are required.
"""

from dataclasses import dataclass
from typing import Optional

from config.tool_contracts import RiskClass, get_risk, get_max_retries


@dataclass
class SafetyDecision:
    tool_name: str
    risk: RiskClass
    requires_confirmation: bool
    requires_compensating_action: bool
    max_auto_retries: int


class SafetyClassifier:
    """
    Minimal classifier implementing PRD rules:
    - IDEMPOTENT actions: no confirmation, no compensating action
    - SAFE actions: no confirmation, no compensating action
    - REVERSIBLE: may auto-retry, typically with TransactionManager
    - DESTRUCTIVE/UNKNOWN: always require confirmation, no auto-retry
    """

    def classify(self, tool_name: str) -> SafetyDecision:
        risk = get_risk(tool_name)
        max_retries = get_max_retries(tool_name)

        if risk in {"SAFE", "IDEMPOTENT"}:
            requires_confirmation = False
            requires_compensating = False
        elif risk == "REVERSIBLE":
            requires_confirmation = False
            requires_compensating = True
        else:  # DESTRUCTIVE or UNKNOWN
            requires_confirmation = True
            requires_compensating = True

        # PRD rule: IDEMPOTENT actions never require confirmation or compensating action.
        if risk == "IDEMPOTENT":
            requires_confirmation = False
            requires_compensating = False

        return SafetyDecision(
            tool_name=tool_name,
            risk=risk,
            requires_confirmation=requires_confirmation,
            requires_compensating_action=requires_compensating,
            max_auto_retries=max_retries,
        )

