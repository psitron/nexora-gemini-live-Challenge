from __future__ import annotations

"""
Hybrid AI Agent – BrowserAdapter.

Thin wrapper around Level 1 DOM executor for browser automation.
"""

from dataclasses import dataclass
from typing import Optional

from execution.level1_dom import Level1DomExecutor
from execution.level0_programmatic import ActionResult


@dataclass
class BrowserAdapter:
    """
    Adapter that exposes a small, clear interface for browser actions.
    """

    _executor: Optional[Level1DomExecutor] = None

    @property
    def executor(self) -> Level1DomExecutor:
        if self._executor is None:
            self._executor = Level1DomExecutor()
        return self._executor

    def open_url(self, url: str) -> ActionResult:
        return self.executor.navigate(url)

    def click(self, selector: str) -> ActionResult:
        return self.executor.click(selector)

    def type_text(self, selector: str, text: str) -> ActionResult:
        return self.executor.type_text(selector, text)

"""Stub module generated from Hybrid AI Agent PRD v5.0.

Fill this file using the corresponding Cursor prompt from the PRD.
"""
