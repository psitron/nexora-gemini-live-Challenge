from __future__ import annotations

"""
Hybrid AI Agent – GovernanceBudget.

Manages step, time, cost, and retry budgets for a single run.
This is a minimal implementation matching the PRD concepts.
"""

from dataclasses import dataclass
from time import monotonic


@dataclass
class BudgetConfig:
    max_steps: int
    max_seconds: int
    max_llm_tokens: int


@dataclass
class GovernanceBudget:
    config: BudgetConfig
    start_ts: float = None
    steps_used: int = 0
    llm_tokens_used: int = 0

    def start(self) -> None:
        if self.start_ts is None:
            self.start_ts = monotonic()

    def record_step(self) -> None:
        self.steps_used += 1

    def record_llm_tokens(self, tokens: int) -> None:
        self.llm_tokens_used += max(0, tokens)

    @property
    def elapsed_seconds(self) -> int:
        if self.start_ts is None:
            return 0
        return int(monotonic() - self.start_ts)

    @property
    def steps_exhausted(self) -> bool:
        return self.steps_used >= self.config.max_steps

    @property
    def time_exhausted(self) -> bool:
        return self.elapsed_seconds >= self.config.max_seconds

    @property
    def tokens_exhausted(self) -> bool:
        return self.llm_tokens_used >= self.config.max_llm_tokens

    @property
    def exhausted(self) -> bool:
        return self.steps_exhausted or self.time_exhausted or self.tokens_exhausted

