"""ExecutionHierarchy tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from execution.hierarchy import ExecutionHierarchy


def test_attempt_unknown_tool_fails() -> None:
    h = ExecutionHierarchy()
    result = h.attempt("unknown_tool_xyz")
    assert result.success is False
    assert "Unknown" in result.message or "unknown" in result.message.lower()


def test_attempt_list_directory_succeeds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        h = ExecutionHierarchy()
        result = h.attempt("list_directory", path=tmp)
        assert result.success is True
        assert result.data is None or "items" in (result.data or {})


def test_attempt_mkdir_succeeds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / "newdir"
        h = ExecutionHierarchy()
        result = h.attempt("mkdir", path=str(sub))
        assert result.success is True
        assert sub.exists()
