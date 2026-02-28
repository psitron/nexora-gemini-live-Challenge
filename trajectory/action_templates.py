from __future__ import annotations

"""
Hybrid AI Agent – action_templates.

Stores reusable action templates for common tasks.
"""

from dataclasses import dataclass
from typing import List

from trajectory.db import get_connection


@dataclass
class ActionTemplate:
    tool_name: str
    template: str  # textual description or serialized structure


def save_template(tmpl: ActionTemplate) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO action_templates (tool_name, template, success_rate) VALUES (?, ?, ?)",
        (tmpl.tool_name, tmpl.template, 0.0),
    )
    conn.commit()


def list_templates(tool_name: str) -> List[ActionTemplate]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT tool_name, template FROM action_templates WHERE tool_name = ?",
        (tool_name,),
    )
    rows = cur.fetchall()
    return [ActionTemplate(tool_name=row[0], template=row[1]) for row in rows]

