from __future__ import annotations

"""
Hybrid AI Agent – StateGraph.

Maintains a tree of StateNodes linked by ActionEdges, enabling
backtracking and trajectory analysis.
"""

from dataclasses import dataclass
from typing import Dict

from core.state_model import StateModel
from verifier.diff_engine import DiffResult
from verifier.outcome_classifier import Outcome
from state_graph.node import StateNode
from state_graph.edge import ActionEdge


@dataclass
class StateGraph:
    nodes: Dict[int, StateNode]
    edges: Dict[int, ActionEdge]
    current_node_id: int
    _next_node_id: int
    _next_edge_id: int

    @classmethod
    def from_initial_state(cls, state: StateModel) -> "StateGraph":
        root = StateNode(
            id=0,
            parent_id=None,
            depth=0,
            state_snapshot=state,
        )
        return cls(
            nodes={0: root},
            edges={},
            current_node_id=0,
            _next_node_id=1,
            _next_edge_id=1,
        )

    def add_transition(
        self,
        action_description: str,
        new_state: StateModel,
        diff: DiffResult,
        outcome: Outcome,
    ) -> int:
        parent_id = self.current_node_id
        node_id = self._next_node_id
        edge_id = self._next_edge_id

        new_node = StateNode(
            id=node_id,
            parent_id=parent_id,
            depth=self.nodes[parent_id].depth + 1,
            state_snapshot=new_state,
            incoming_edge_id=edge_id,
        )
        self.nodes[node_id] = new_node

        edge = ActionEdge(
            id=edge_id,
            parent_node_id=parent_id,
            child_node_id=node_id,
            action_description=action_description,
            diff=diff,
            outcome=outcome,
        )
        self.edges[edge_id] = edge

        self.nodes[parent_id].children_ids.append(node_id)

        self.current_node_id = node_id
        self._next_node_id += 1
        self._next_edge_id += 1

        return node_id

    def backtrack_to_parent(self) -> int:
        node = self.nodes[self.current_node_id]
        if node.parent_id is not None:
            self.current_node_id = node.parent_id
        return self.current_node_id

