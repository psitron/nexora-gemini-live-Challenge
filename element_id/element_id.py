from __future__ import annotations

"""
Hybrid AI Agent – ElementID dataclass.

ElementID is the stable handle the agent uses to refer to a UI element
across perception sources (DOM, UI tree, visual).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ElementID:
    """
    Fallback chain for locating a UI element.

    Fields:
    - label: human-readable label, e.g. "Submit Button"
    - dom_locator: CSS/XPath selector for DOM-based lookup
    - ui_tree_id: automation_id for Windows UIA lookup
    - bbox: "x,y,w,h" absolute screen coordinates for visual lookup
    - source: which source last successfully resolved this id
    """

    label: str
    dom_locator: Optional[str] = None
    ui_tree_id: Optional[str] = None
    bbox: Optional[str] = None
    source: Optional[str] = None  # "dom" | "ui_tree" | "visual"

"""Stub module generated from Hybrid AI Agent PRD v5.0.

Fill this file using the corresponding Cursor prompt from the PRD.
"""
