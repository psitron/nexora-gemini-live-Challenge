from __future__ import annotations

"""
Hybrid AI Agent – verifier.post_state

Captures StateModel after an action.
"""

from dataclasses import dataclass
from typing import Optional

from core.state_model import StateModel
from perception.schemas import NormalisedEnvironment


@dataclass
class PostStateSnapshot:
    environment: Optional[NormalisedEnvironment]
    dirty: bool


def capture_post_state(state: StateModel) -> PostStateSnapshot:
    return PostStateSnapshot(
        environment=state.environment,
        dirty=state._dirty,
    )

