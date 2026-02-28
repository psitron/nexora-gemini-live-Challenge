from __future__ import annotations

"""
Hybrid AI Agent – GoalTracker.

Tracks success criteria, retry counts, and overall task status.
This is a minimal implementation aligned with the PRD, sufficient
for early integration with planners and governance budgets.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GoalStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class GoalTracker:
    """Tracks current goal, success criteria, and retries."""

    description: str
    max_retries: int = 3
    attempts: int = 0
    status: GoalStatus = GoalStatus.PENDING
    last_error: Optional[str] = None

    def start(self) -> None:
        if self.status is GoalStatus.PENDING:
            self.status = GoalStatus.IN_PROGRESS

    def record_success(self) -> None:
        self.status = GoalStatus.SUCCESS
        self.last_error = None

    def record_failure(self, error: Optional[str] = None) -> None:
        self.attempts += 1
        self.last_error = error
        if self.attempts >= self.max_retries:
            self.status = GoalStatus.FAILED
        else:
            self.status = GoalStatus.IN_PROGRESS

    def cancel(self, reason: Optional[str] = None) -> None:
        self.status = GoalStatus.CANCELLED
        self.last_error = reason

    @property
    def can_retry(self) -> bool:
        return self.attempts < self.max_retries and self.status not in {
            GoalStatus.SUCCESS,
            GoalStatus.CANCELLED,
        }

