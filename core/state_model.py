from __future__ import annotations

"""
Hybrid AI Agent - StateModel with dirty_flag and NormalisedEnvironment.

This is a minimal implementation focused on:
- Tracking whether the environment needs to be re-queried (dirty_flag)
- Storing the last NormalisedEnvironment snapshot
"""

from dataclasses import dataclass, field
from typing import Optional, List

from perception.schemas import NormalisedEnvironment


@dataclass
class StateModel:
    """
    Central state object for the agent loop.

    For now we track only:
    - environment: last NormalisedEnvironment snapshot
    - _dirty: whether structured perception must run again
    - _last_screen_hash: last perceptual hash (string) used for caching
    - knowledge_buffer: accumulated facts discovered during execution
    """

    environment: Optional[NormalisedEnvironment] = None
    _dirty: bool = True
    _last_screen_hash: str = ""
    knowledge_buffer: List[str] = field(default_factory=list)

    def check_and_update_dirty(self, new_screen_hash: str) -> bool:
        """
        Call with current screen hash before perception step.

        Returns True if re-query needed (hash changed or first run).
        Returns False if screen unchanged and cache is clean.
        """
        if new_screen_hash == self._last_screen_hash and not self._dirty:
            return False

        self._dirty = True
        self._last_screen_hash = new_screen_hash
        return True

    def update_from_normalised(self, env: NormalisedEnvironment) -> None:
        """Store normalised environment and mark clean."""
        self.environment = env
        self._dirty = False

    def invalidate(self) -> None:
        """Force re-query on next iteration. Call after every action."""
        self._dirty = True
        self._last_screen_hash = ""

    def add_knowledge(self, fact: str) -> None:
        """
        Add a fact to the knowledge buffer.

        Facts are accumulated during execution and can be used to inform
        future decisions. Duplicates are automatically filtered out.

        Args:
            fact: A discovered fact (e.g., "Chrome is open", "User is logged in")
        """
        if fact and fact not in self.knowledge_buffer:
            self.knowledge_buffer.append(fact)

    def get_knowledge_summary(self) -> str:
        """
        Get formatted knowledge buffer for LLM prompts.

        Returns:
            Formatted string of all accumulated knowledge, or empty string if none.
        """
        if not self.knowledge_buffer:
            return ""
        return "Known facts:\n- " + "\n- ".join(self.knowledge_buffer)

    def clear_knowledge(self) -> None:
        """Clear the knowledge buffer. Call when starting a new task."""
        self.knowledge_buffer.clear()

