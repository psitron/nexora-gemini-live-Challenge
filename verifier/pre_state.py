from __future__ import annotations

"""
Hybrid AI Agent – verifier.pre_state

Captures a lightweight snapshot of StateModel before an action.
"""

from dataclasses import dataclass
from typing import Optional

from core.state_model import StateModel
from perception.schemas import NormalisedEnvironment


@dataclass
class PreStateSnapshot:
    environment: Optional[NormalisedEnvironment]
    dirty: bool


def capture_pre_state(state: StateModel) -> PreStateSnapshot:
    return PreStateSnapshot(
        environment=state.environment,
        dirty=state._dirty,
    )

