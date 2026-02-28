from __future__ import annotations

"""
Hybrid AI Agent – DeadlockDetector.

Minimal implementation based on PRD ideas:
- No interactive elements
- Repeated states
"""

from dataclasses import dataclass, field
from typing import Set

from core.state_model import StateModel


@dataclass
class DeadlockDetector:
    seen_hashes: Set[str] = field(default_factory=set)

    def is_deadlocked(self, state: StateModel) -> bool:
        # Condition 1: no interactive elements
        env = state.environment
        if env is None or not env.interactive:
            return True

        # Condition 2: repeated environment hash (simple loop detection)
        h = env.source_hash
        if h in self.seen_hashes:
            return True
        self.seen_hashes.add(h)

        return False

