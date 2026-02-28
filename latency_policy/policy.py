from __future__ import annotations

"""
Hybrid AI Agent – LatencyPolicy.

Uses TOOL_AFFINITY_MAP plus simple per-tool/level stats to choose
which execution levels to try first for a given action.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from config.tool_contracts import TOOL_AFFINITY_MAP


@dataclass
class LevelStats:
    calls: int = 0
    total_ms: int = 0
    successes: int = 0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.calls if self.calls else 0.0


@dataclass
class LatencyPolicy:
    """
    Minimal policy:
    - Start with TOOL_AFFINITY_MAP ordering
    - Within that order, prefer levels with lower observed latency
    """

    stats: Dict[str, LevelStats] = field(default_factory=dict)

    def record(self, level: str, elapsed_ms: int, success: bool) -> None:
        s = self.stats.setdefault(level, LevelStats())
        s.calls += 1
        s.total_ms += max(0, elapsed_ms)
        if success:
            s.successes += 1

    def choose_levels(self, tool_name: str) -> List[str]:
        base = TOOL_AFFINITY_MAP.get(tool_name)
        if not base:
            # Fallback order if no affinity entry
            base = ["L0_PROGRAMMATIC", "L1_DOM", "L2_UI_TREE", "L3_PATTERN", "L4_LOCAL_VLM", "L5_CLOUD", "L6_HUMAN"]

        # For now, return base order directly; stats could be used later to tweak.
        return list(base)

