from __future__ import annotations

"""
Hybrid AI Agent – perception schemas.

NormalisedElement and NormalisedEnvironment dataclasses, as specified
in the PRD. This is a minimal version sufficient for early wiring and
type-checking; behaviour will be expanded when building perception.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class NormalisedElement:
    id: str
    label: str
    element_type: str  # 'button'|'input'|'link'|'text'|'image'|'container'
    text_content: Optional[str]
    state: str  # 'enabled'|'disabled'|'checked'|'hidden'
    sources: List[str]  # ['dom','ui_tree','visual']
    dom_locator: Optional[str]
    ui_tree_id: Optional[str]
    bbox: Optional[str]  # 'x,y,w,h'
    confidence: float
    children: List["NormalisedElement"] = field(default_factory=list)


@dataclass
class NormalisedEnvironment:
    window_title: str
    window_type: str  # 'browser'|'desktop_app'|'dialog'|'unknown'
    current_url: Optional[str]
    app_name: str
    elements: List[NormalisedElement]
    interactive: List[NormalisedElement]
    timestamp: datetime
    source_hash: str

