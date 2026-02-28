from __future__ import annotations

"""
Hybrid AI Agent – failure_patterns.

Tracks recurring failure signatures for tools, to avoid repeating
known-bad actions.
"""

from dataclasses import dataclass
from typing import List

from trajectory.db import get_connection


@dataclass
class FailurePattern:
    tool_name: str
    pattern: str  # textual/JSON description of the failure


def record_failure(pattern: FailurePattern) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO failure_patterns (tool_name, pattern, occurrence_count)
        VALUES (?, ?, 1)
        ON CONFLICT(tool_name, pattern) DO UPDATE SET occurrence_count = occurrence_count + 1
        """,
        (pattern.tool_name, pattern.pattern),
    )
    conn.commit()


def list_failures(tool_name: str) -> List[FailurePattern]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT tool_name, pattern FROM failure_patterns WHERE tool_name = ?",
        (tool_name,),
    )
    rows = cur.fetchall()
    return [FailurePattern(tool_name=row[0], pattern=row[1]) for row in rows]

