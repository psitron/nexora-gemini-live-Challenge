from __future__ import annotations

"""
Hybrid AI Agent – tool contracts and affinity map.

Defines:
- ToolContract dataclass with risk classes and max_auto_retries
- TOOL_CONTRACTS registry
- TOOL_AFFINITY_MAP for routing by LatencyPolicy
- Small helpers: get_risk, get_affinity_levels, get_max_retries
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


RiskClass = str  # 'SAFE'|'IDEMPOTENT'|'REVERSIBLE'|'DESTRUCTIVE'|'UNKNOWN'


@dataclass
class ToolContract:
    name: str
    risk: RiskClass
    max_auto_retries: int


def _risk_to_retries(risk: RiskClass) -> int:
    if risk == "SAFE":
        return 10
    if risk == "IDEMPOTENT":
        return 5
    if risk == "REVERSIBLE":
        return 2
    if risk in {"DESTRUCTIVE", "UNKNOWN"}:
        return 0
    return 0


# Minimal registry with a few example tools. This should be extended as
# you add more concrete actions to the execution hierarchy.
TOOL_CONTRACTS: Dict[str, ToolContract] = {}


def _add_tool(name: str, risk: RiskClass) -> None:
    TOOL_CONTRACTS[name] = ToolContract(
        name=name,
        risk=risk,
        max_auto_retries=_risk_to_retries(risk),
    )


# IDEMPOTENT examples from the PRD
_add_tool("open_application", "IDEMPOTENT")
_add_tool("navigate_to_url", "IDEMPOTENT")
_add_tool("open_folder", "IDEMPOTENT")
_add_tool("set_checkbox_checked", "IDEMPOTENT")
_add_tool("close_dialog", "IDEMPOTENT")
_add_tool("mkdir", "IDEMPOTENT")
_add_tool("focus_window", "IDEMPOTENT")

# Keyboard operations - always programmatic
_add_tool("keyboard_shortcut", "SAFE")
_add_tool("keyboard_press", "SAFE")
_add_tool("keyboard_type", "SAFE")

# File operations – reversible/destructive examples
_add_tool("file_read", "SAFE")
_add_tool("file_write", "REVERSIBLE")
_add_tool("file_delete", "DESTRUCTIVE")
_add_tool("file_copy", "REVERSIBLE")
_add_tool("list_directory", "SAFE")


# Tool Affinity Map as specified in PRD 2.6.1
TOOL_AFFINITY_MAP: Dict[str, List[str]] = {
    # Browser actions --- DOM first, visual fallback
    "browser_click": ["L1_DOM", "L4_LOCAL_VLM", "L5_CLOUD", "L6_HUMAN"],
    "browser_type": ["L1_DOM", "L4_LOCAL_VLM", "L5_CLOUD", "L6_HUMAN"],
    "browser_navigate": ["L1_DOM", "L6_HUMAN"],
    "browser_scroll": ["L1_DOM", "L4_LOCAL_VLM", "L6_HUMAN"],

    # Desktop app actions --- UI tree first
    "desktop_click": ["L2_UI_TREE", "L3_PATTERN", "L4_LOCAL_VLM", "L5_CLOUD", "L6_HUMAN"],
    "desktop_type": ["L2_UI_TREE", "L4_LOCAL_VLM", "L6_HUMAN"],
    "menu_select": ["L2_UI_TREE", "L4_LOCAL_VLM", "L6_HUMAN"],
    "dialog_respond": ["L2_UI_TREE", "L4_LOCAL_VLM", "L6_HUMAN"],
    "pattern_click": ["L3_PATTERN", "L4_LOCAL_VLM", "L5_CLOUD", "L6_HUMAN"],

    # File operations --- always programmatic
    "file_read": ["L0_PROGRAMMATIC"],
    "file_write": ["L0_PROGRAMMATIC"],
    "file_delete": ["L0_PROGRAMMATIC"],
    "file_copy": ["L0_PROGRAMMATIC"],
    "list_directory": ["L0_PROGRAMMATIC"],
    
    # Keyboard operations --- always programmatic
    "keyboard_shortcut": ["L0_PROGRAMMATIC"],
    "keyboard_press": ["L0_PROGRAMMATIC"],
    "keyboard_type": ["L0_PROGRAMMATIC"],
    "mkdir": ["L0_PROGRAMMATIC"],

    # System operations --- programmatic, UI tree fallback
    "app_launch": ["L0_PROGRAMMATIC", "L2_UI_TREE", "L4_LOCAL_VLM"],
    "app_close": ["L0_PROGRAMMATIC", "L2_UI_TREE"],
    "registry_read": ["L0_PROGRAMMATIC"],
    "registry_write": ["L0_PROGRAMMATIC"],
    "system_info": ["L0_PROGRAMMATIC"],

    # Search / data extraction --- programmatic first
    "web_search": ["L0_PROGRAMMATIC"],
    "api_call": ["L0_PROGRAMMATIC"],
    "extract_text": ["L1_DOM", "L0_PROGRAMMATIC", "L4_LOCAL_VLM"],
}


def get_risk(tool_name: str) -> RiskClass:
    contract = TOOL_CONTRACTS.get(tool_name)
    if contract is None:
        return "UNKNOWN"
    return contract.risk


def get_affinity_levels(tool_name: str) -> Optional[List[str]]:
    """
    Returns list of level strings from TOOL_AFFINITY_MAP, or None if not found.
    """
    return TOOL_AFFINITY_MAP.get(tool_name)


def get_max_retries(tool_name: str) -> int:
    """
    Returns max_auto_retries from contract, or 0 if unknown.
    """
    contract = TOOL_CONTRACTS.get(tool_name)
    if contract is None:
        return 0
    return contract.max_auto_retries

