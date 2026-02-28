from __future__ import annotations

"""
Hybrid AI Agent – WindowsUIAdapter.

Thin adapter over Level 2 UI-tree executor for desktop automation.
"""

from dataclasses import dataclass

from execution.level2_ui_tree import Level2UiTreeExecutor
from execution.level0_programmatic import ActionResult


@dataclass
class WindowsUIAdapter:
    """
    Adapter exposing a small desktop UI API.
    """

    _executor: Level2UiTreeExecutor

    def __init__(self) -> None:
        self._executor = Level2UiTreeExecutor()

    def click_by_name(self, name: str) -> ActionResult:
        return self._executor.desktop_click(name)

    def type_into(self, name: str, text: str) -> ActionResult:
        return self._executor.desktop_type(name, text)

