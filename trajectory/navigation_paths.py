from __future__ import annotations

"""
Hybrid AI Agent – navigation_paths.

Stores known-good navigation paths between labelled UI states.
"""

from dataclasses import dataclass
from typing import List

from trajectory.db import get_connection


@dataclass
class NavigationPath:
    start_label: str
    end_label: str
    path: str  # serialized list of actions or ElementIDs


def save_navigation_path(nav: NavigationPath) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO navigation_paths (start_label, end_label, path) VALUES (?, ?, ?)",
        (nav.start_label, nav.end_label, nav.path),
    )
    conn.commit()


def list_paths(start_label: str, end_label: str) -> List[NavigationPath]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT start_label, end_label, path FROM navigation_paths WHERE start_label = ? AND end_label = ?",
        (start_label, end_label),
    )
    rows = cur.fetchall()
    return [
        NavigationPath(start_label=row[0], end_label=row[1], path=row[2])
        for row in rows
    ]

