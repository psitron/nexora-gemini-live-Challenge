from __future__ import annotations

"""
Hybrid AI Agent – LatencyProfiler.

Collects simple per-tool, per-level latency statistics and forwards
them to LatencyPolicy. This v1 implementation keeps data in memory
only; persistent storage can be added later.
"""

from dataclasses import dataclass, field
from time import perf_counter
from typing import Dict

from latency_policy.policy import LatencyPolicy


@dataclass
class CallSample:
    tool_name: str
    level: str
    elapsed_ms: int
    success: bool


@dataclass
class LatencyProfiler:
    """
    Small helper that times tool executions and updates LatencyPolicy.
    """

    policy: LatencyPolicy = field(default_factory=LatencyPolicy)
    recent_samples: Dict[str, CallSample] = field(default_factory=dict)

    def time_call(self, level: str, tool_name: str, func, *args, **kwargs):
        """
        Time a synchronous call to an executor method.

        `level` should be one of: L0_PROGRAMMATIC, L1_DOM, L2_UI_TREE, ...
        """
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = int((perf_counter() - start) * 1000)

        success = getattr(result, "success", False)
        self.policy.record(level, elapsed_ms, success)

        key = f"{level}:{tool_name}"
        self.recent_samples[key] = CallSample(
            tool_name=tool_name,
            level=level,
            elapsed_ms=elapsed_ms,
            success=success,
        )

        return result
