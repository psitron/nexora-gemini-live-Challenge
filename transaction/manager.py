from __future__ import annotations

"""
Hybrid AI Agent – TransactionManager.

Provides a thin abstraction for wrapping potentially risky actions
in a filesystem/registry transaction. For now this focuses on
file operations and creates trash/backup copies as required by
the .cursorrules safety rules.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import shutil
import uuid

from config.settings import get_settings


@dataclass
class TransactionContext:
    """
    Minimal context for a single action transaction.

    For now we only track file paths; registry and app-level
    transactions can be added later.
    """

    action_name: str
    source_path: Optional[Path] = None
    backup_path: Optional[Path] = None
    trash_path: Optional[Path] = None


class TransactionManager:
    """
    File-focused transaction manager.

    Responsibilities now:
    - For file deletes: move file into agent_trash_dir before delete
    - For file writes: copy original file into agent_backup_dir first

    Higher-level logic (when to call begin/commit/rollback) will
    live in agent_loop and execution hierarchy.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._trash_dir = Path(settings.paths.agent_trash_dir)
        self._backup_dir = Path(settings.paths.agent_backup_dir)

        self._trash_dir.mkdir(parents=True, exist_ok=True)
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def begin_file_delete(self, path: Path) -> TransactionContext:
        """
        Prepare a file delete by moving the file to the trash directory.
        Returns a context that can be used to restore if needed.
        """
        ctx = TransactionContext(action_name="file_delete", source_path=path)
        if path.exists():
            trash_name = f"{uuid.uuid4()}_{path.name}"
            trash_path = self._trash_dir / trash_name
            shutil.move(str(path), str(trash_path))
            ctx.trash_path = trash_path
        return ctx

    def begin_file_write(self, path: Path) -> TransactionContext:
        """
        Prepare a file write by copying the current file into backups.
        """
        ctx = TransactionContext(action_name="file_write", source_path=path)
        if path.exists():
            backup_name = f"{uuid.uuid4()}_{path.name}"
            backup_path = self._backup_dir / backup_name
            shutil.copy2(str(path), str(backup_path))
            ctx.backup_path = backup_path
        return ctx

    def rollback(self, ctx: TransactionContext) -> None:
        """
        Best-effort rollback:
        - For deletes: move from trash back to original path
        - For writes: restore from backup to original path
        """
        if ctx.action_name == "file_delete" and ctx.trash_path and not ctx.source_path.exists():
            shutil.move(str(ctx.trash_path), str(ctx.source_path))
        elif ctx.action_name == "file_write" and ctx.backup_path and ctx.source_path:
            shutil.copy2(str(ctx.backup_path), str(ctx.source_path))

    def commit(self, ctx: TransactionContext) -> None:
        """
        On successful completion:
        - For deletes: leave file in trash (for manual restore if needed)
        - For writes: keep backup as historical copy
        """
        # No-op for now; files remain in trash/backup locations.
        _ = ctx

