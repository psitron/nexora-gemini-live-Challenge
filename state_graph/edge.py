from __future__ import annotations

"""
Hybrid AI Agent – ActionEdge.

Connects two StateNodes with the action taken and its diff/outcome.
"""

from dataclasses import dataclass
from typing import Optional

from verifier.diff_engine import DiffResult
from verifier.outcome_classifier import Outcome


@dataclass
class ActionEdge:
    id: int
    parent_node_id: int
    child_node_id: int
    action_description: str
    diff: DiffResult
    outcome: Outcome

