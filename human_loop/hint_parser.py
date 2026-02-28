from __future__ import annotations

"""
Hybrid AI Agent – human_loop.hint_parser

Parses a simple natural language hint from a human into a structured
hint dict that the planner/executor can interpret.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import re


@dataclass
class ParsedHint:
    """
    Very small structured representation of a human hint.
    """

    action: str
    target: Optional[str] = None
    extra: Optional[str] = None


def parse_hint(text: str) -> ParsedHint:
    """
    Parse a human hint. This v1 implementation supports only a few
    simple patterns and otherwise returns a generic "comment" action.
    """
    t = text.strip()
    lower = t.lower()

    # Click patterns: "click the 'Submit' button", "click Submit"
    m = re.search(r"click(?: the)? ['\"]?(.+?)['\"]?(?: button)?$", t, re.IGNORECASE)
    if m:
        return ParsedHint(action="click", target=m.group(1))

    # Open URL: "open https://example.com"
    m = re.search(r"open\s+(https?://\S+)", t, re.IGNORECASE)
    if m:
        return ParsedHint(action="open_url", target=m.group(1))

    # Type text: "type 'hello' into 'Search'"
    m = re.search(
        r"type ['\"](.+?)['\"] into ['\"](.+?)['\"]",
        t,
        re.IGNORECASE,
    )
    if m:
        return ParsedHint(action="type_text", target=m.group(2), extra=m.group(1))

    # Fallback: treat as freeform comment
    return ParsedHint(action="comment", target=None, extra=t)

