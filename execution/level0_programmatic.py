from __future__ import annotations

"""
Hybrid AI Agent – Level 0 Programmatic Execution.

Implements safe file and system actions using Python, TransactionManager,
and SafetyClassifier. This is the lowest-latency, highest-confidence
execution level and should be preferred whenever possible.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import shutil

from config.tool_contracts import get_risk
from safety.classifier import SafetyClassifier
from safety.action_logger import ActionLogger, ActionRecord
from transaction.manager import TransactionManager


@dataclass
class ActionResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class Level0ProgrammaticExecutor:
    def __init__(self) -> None:
        self._tx = TransactionManager()
        self._safety = SafetyClassifier()
        self._logger = ActionLogger()

    def _log(self, tool_name: str, success: bool, details: Optional[Dict[str, Any]] = None) -> None:
        risk = get_risk(tool_name)
        rec = ActionRecord(
            tool_name=tool_name,
            risk=risk,
            status="SUCCESS" if success else "FAILURE",
            details=details or {},
        )
        self._logger.log(rec)

    # --- File operations -------------------------------------------------

    def file_read(self, path: Path) -> ActionResult:
        tool_name = "file_read"
        try:
            text = path.read_text(encoding="utf-8")
            self._log(tool_name, True, {"path": str(path)})
            return ActionResult(True, f"Read file {path}", {"content": text})
        except Exception as exc:
            self._log(tool_name, False, {"path": str(path), "error": str(exc)})
            return ActionResult(False, f"Failed to read file {path}: {exc}")

    def file_write(self, path: Path, content: str) -> ActionResult:
        tool_name = "file_write"
        ctx = self._tx.begin_file_write(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self._tx.commit(ctx)
            self._log(tool_name, True, {"path": str(path)})
            return ActionResult(True, f"Wrote file {path}")
        except Exception as exc:
            self._tx.rollback(ctx)
            self._log(tool_name, False, {"path": str(path), "error": str(exc)})
            return ActionResult(False, f"Failed to write file {path}: {exc}")

    def file_delete(self, path: Path) -> ActionResult:
        tool_name = "file_delete"
        ctx = self._tx.begin_file_delete(path)
        try:
            # File already moved to trash in begin_file_delete
            self._tx.commit(ctx)
            self._log(tool_name, True, {"path": str(path)})
            return ActionResult(True, f"Deleted file {path} (moved to trash).")
        except Exception as exc:
            self._tx.rollback(ctx)
            self._log(tool_name, False, {"path": str(path), "error": str(exc)})
            return ActionResult(False, f"Failed to delete file {path}: {exc}")

    def file_copy(self, src: Path, dst: Path) -> ActionResult:
        tool_name = "file_copy"
        ctx = self._tx.begin_file_write(dst)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            self._tx.commit(ctx)
            self._log(tool_name, True, {"src": str(src), "dst": str(dst)})
            return ActionResult(True, f"Copied {src} to {dst}")
        except Exception as exc:
            self._tx.rollback(ctx)
            self._log(tool_name, False, {"src": str(src), "dst": str(dst), "error": str(exc)})
            return ActionResult(False, f"Failed to copy {src} to {dst}: {exc}")

    def list_directory(self, path: Path) -> ActionResult:
        tool_name = "list_directory"
        try:
            items = [p.name for p in path.iterdir()]
            self._log(tool_name, True, {"path": str(path), "count": len(items)})
            return ActionResult(True, f"Listed directory {path}", {"items": items})
        except Exception as exc:
            self._log(tool_name, False, {"path": str(path), "error": str(exc)})
            return ActionResult(False, f"Failed to list directory {path}: {exc}")

    def mkdir(self, path: Path) -> ActionResult:
        tool_name = "mkdir"
        try:
            path.mkdir(parents=True, exist_ok=True)
            self._log(tool_name, True, {"path": str(path)})
            return ActionResult(True, f"Ensured directory {path} exists")
        except Exception as exc:
            self._log(tool_name, False, {"path": str(path), "error": str(exc)})
            return ActionResult(False, f"Failed to create directory {path}: {exc}")

