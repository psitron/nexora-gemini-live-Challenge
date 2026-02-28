from __future__ import annotations

"""
Hybrid AI Agent – trajectory DB.

Provides a SQLite-backed store for trajectories, fingerprints, templates,
and failure patterns. For now we expose only the core connection and
basic table creation so other trajectory modules can share it.
"""

from pathlib import Path
import sqlite3

from config.settings import get_settings


DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS action_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    success INTEGER NOT NULL,
    last_used_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    template TEXT NOT NULL,
    success_rate REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS failure_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    pattern TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS navigation_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_label TEXT NOT NULL,
    end_label TEXT NOT NULL,
    path TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    settings = get_settings()
    db_path = Path(settings.paths.trajectory_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    conn.commit()
    return conn

