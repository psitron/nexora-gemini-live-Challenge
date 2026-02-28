from __future__ import annotations

"""
Hybrid AI Agent – action logger.

Logs every executed action to a SQLite database, as required by the
PRD and .cursorrules. This is a minimal implementation that other
modules can call synchronously.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import json
import sqlite3

from config.settings import get_settings


DDL = """
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    risk TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT
);
"""


@dataclass
class ActionRecord:
    tool_name: str
    risk: str
    status: str  # e.g. "SUCCESS", "FAILURE"
    details: Optional[Dict[str, Any]] = None


class ActionLogger:
    def __init__(self) -> None:
        settings = get_settings()
        db_path = Path(settings.paths.action_log_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(db_path)
        self._conn.execute(DDL)
        self._conn.commit()

    def log(self, record: ActionRecord) -> None:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        details_json = json.dumps(record.details or {})
        self._conn.execute(
            "INSERT INTO action_log (ts, tool_name, risk, status, details) VALUES (?, ?, ?, ?, ?)",
            (ts, record.tool_name, record.risk, record.status, details_json),
        )
        self._conn.commit()

