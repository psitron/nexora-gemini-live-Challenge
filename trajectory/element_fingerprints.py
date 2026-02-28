from __future__ import annotations

"""
Hybrid AI Agent – element_fingerprints.

Stores simple fingerprints of successful actions to re-use them later.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json

from trajectory.db import get_connection


@dataclass
class ElementFingerprint:
    tool_name: str
    fingerprint: str  # JSON blob representing ElementID + context
    success: bool


def save_fingerprint(fp: ElementFingerprint) -> None:
    conn = get_connection()
    ts = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        "INSERT INTO action_fingerprints (tool_name, fingerprint, success, last_used_ts) VALUES (?, ?, ?, ?)",
        (fp.tool_name, fp.fingerprint, int(fp.success), ts),
    )
    conn.commit()


def find_fingerprints(tool_name: str) -> list[ElementFingerprint]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT tool_name, fingerprint, success FROM action_fingerprints WHERE tool_name = ?",
        (tool_name,),
    )
    rows = cur.fetchall()
    return [
        ElementFingerprint(tool_name=row[0], fingerprint=row[1], success=bool(row[2]))
        for row in rows
    ]

