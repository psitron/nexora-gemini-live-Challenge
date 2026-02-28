"""
End-to-end integration test for AgentLoop.

Runs the full loop with a filesystem-only goal (L0 actions). Asserts
the loop completes without validation failure, at least one step runs,
and the folder created by the mapper (mkdir) exists. Perception and
deadlock are mocked so the test needs no browser/UI/stdin.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from core.agent_loop import AgentLoop


def test_e2e_agent_loop_filesystem_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        e2e_dir = base / "e2e_dir"
        goal = f"Create folder {e2e_dir} and list the contents of {e2e_dir}"
        loop = AgentLoop()
        with patch.object(loop, "_update_perception_if_needed"), patch.object(
            loop.deadlock_detector, "is_deadlocked", return_value=False
        ):
            result = loop.run(goal)

        assert result.goal_status != "FAILED", result.outcomes
        assert result.steps_executed >= 1
        # Mapper produces mkdir then list_directory for this goal; folder must exist
        assert e2e_dir.is_dir(), f"Expected folder {e2e_dir}"
