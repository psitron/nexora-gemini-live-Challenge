"""
Test the upgraded ActionMapper with LLM mapping.

Checks that:
1. LLM mapping works when API keys present
2. Fallback heuristics work when LLM unavailable
3. Desktop UI patterns (Control Panel, Recycle Bin) map correctly
"""

from __future__ import annotations

from unittest.mock import patch

from config.settings import get_settings
from core.action_mapper import ActionMapper
from core.planner_task import PlannedStep


def test_heuristic_control_panel() -> None:
    """When LLM unavailable, heuristic should map 'control panel' to desktop_click."""
    settings = get_settings()
    mapper = ActionMapper(settings)
    step = PlannedStep(index=1, description="Open Control Panel")
    
    # Mock LLM unavailable
    with patch.object(mapper, "_try_llm_mapping", return_value=[]):
        actions = mapper.map_step(step, "Open Control Panel")
    
    assert len(actions) >= 1
    assert actions[0].tool_name == "desktop_click"
    assert actions[0].kwargs["name"] == "Control Panel"


def test_heuristic_recycle_bin() -> None:
    """When LLM unavailable, heuristic should map 'recycle bin' to desktop_click."""
    settings = get_settings()
    mapper = ActionMapper(settings)
    step = PlannedStep(index=1, description="Open Recycle Bin")
    
    with patch.object(mapper, "_try_llm_mapping", return_value=[]):
        actions = mapper.map_step(step, "Open Recycle Bin")
    
    assert len(actions) >= 1
    assert actions[0].tool_name == "desktop_click"
    assert actions[0].kwargs["name"] == "Recycle Bin"


def test_heuristic_file_explorer() -> None:
    """When LLM unavailable, heuristic should map 'file explorer' to desktop_click."""
    settings = get_settings()
    mapper = ActionMapper(settings)
    step = PlannedStep(index=1, description="Open File Explorer")
    
    with patch.object(mapper, "_try_llm_mapping", return_value=[]):
        actions = mapper.map_step(step, "Open File Explorer")
    
    assert len(actions) >= 1
    assert actions[0].tool_name == "desktop_click"
    assert actions[0].kwargs["name"] == "File Explorer"


def test_llm_mapping_integration() -> None:
    """If LLM returns valid actions, ActionMapper uses them (tested with mock)."""
    from core.action_mapper import ActionSpec
    
    settings = get_settings()
    mapper = ActionMapper(settings)
    step = PlannedStep(index=1, description="Open Settings")
    
    mock_actions = [ActionSpec(tool_name="desktop_click", kwargs={"name": "Settings"})]
    with patch.object(mapper, "_try_llm_mapping", return_value=mock_actions):
        actions = mapper.map_step(step, "Open Settings")
    
    assert len(actions) == 1
    assert actions[0].tool_name == "desktop_click"
    assert actions[0].kwargs["name"] == "Settings"
