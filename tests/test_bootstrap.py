from __future__ import annotations

"""
Hybrid AI Agent – smoke tests.

These are very lightweight checks intended as a starting point for a
full test suite in Phase 7.
"""

from config.settings import get_settings
from core.agent_loop import AgentLoop


def test_settings_load() -> None:
    settings = get_settings()
    assert settings.paths.root_dir is not None
    assert settings.runtime.environment in {"dev", "prod", "test"}


def test_agent_loop_instantiates() -> None:
    loop = AgentLoop()
    assert loop is not None

