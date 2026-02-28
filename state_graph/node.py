from __future__ import annotations

"""
Hybrid AI Agent – StateNode.

Represents a single point in the agent's execution tree.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from core.state_model import StateModel
from verifier.diff_engine import DiffResult


@dataclass
class StateNode:
    id: int
    parent_id: Optional[int]
    depth: int
    state_snapshot: StateModel
    incoming_edge_id: Optional[int] = None
    children_ids: List[int] = field(default_factory=list)

