from __future__ import annotations

"""
Hybrid AI Agent – FilesystemAdapter.

Adapter over Level 0 programmatic executor for file/directory actions.
"""

from dataclasses import dataclass
from pathlib import Path

from execution.level0_programmatic import Level0ProgrammaticExecutor, ActionResult


@dataclass
class FilesystemAdapter:
    """
    Adapter that exposes a simple filesystem API to higher-level code.
    """

    _executor: Level0ProgrammaticExecutor

    def __init__(self) -> None:
        self._executor = Level0ProgrammaticExecutor()

    def read_text(self, path: Path) -> ActionResult:
        return self._executor.file_read(path)

    def write_text(self, path: Path, content: str) -> ActionResult:
        return self._executor.file_write(path, content)

    def delete(self, path: Path) -> ActionResult:
        return self._executor.file_delete(path)

    def copy(self, src: Path, dst: Path) -> ActionResult:
        return self._executor.file_copy(src, dst)

    def list_dir(self, path: Path) -> ActionResult:
        return self._executor.list_directory(path)

    def ensure_dir(self, path: Path) -> ActionResult:
        return self._executor.mkdir(path)

"""Stub module generated from Hybrid AI Agent PRD v5.0.

Fill this file using the corresponding Cursor prompt from the PRD.
"""
