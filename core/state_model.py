from __future__ import annotations

"""
Hybrid AI Agent – StateModel with dirty_flag and NormalisedEnvironment.

This is a minimal implementation focused on:
- Tracking whether the environment needs to be re-queried (dirty_flag)
- Storing the last NormalisedEnvironment snapshot
"""

from dataclasses import dataclass, field
from typing import Optional

from perception.schemas import NormalisedEnvironment


@dataclass
class StateModel:
    """
    Central state object for the agent loop.

    For now we track only:
    - environment: last NormalisedEnvironment snapshot
    - _dirty: whether structured perception must run again
    - _last_screen_hash: last perceptual hash (string) used for caching
    """

    environment: Optional[NormalisedEnvironment] = None
    _dirty: bool = True
    _last_screen_hash: str = ""

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

