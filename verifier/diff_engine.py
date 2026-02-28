from __future__ import annotations

"""
Hybrid AI Agent – verifier.diff_engine

Provides a simple wrapper around deepdiff to compare pre and post
state snapshots. This is a minimal text/structure diff; visual and
element-level diffs can be expanded later.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from deepdiff import DeepDiff

from verifier.pre_state import PreStateSnapshot
from verifier.post_state import PostStateSnapshot


@dataclass
class DiffResult:
    raw: Dict[str, Any]

    @property
    def has_changes(self) -> bool:
        return bool(self.raw)


def diff_states(pre: PreStateSnapshot, post: PostStateSnapshot) -> DiffResult:
    before = {
        "environment": pre.environment,
        "dirty": pre.dirty,
    }
    after = {
        "environment": post.environment,
        "dirty": post.dirty,
    }
    dd = DeepDiff(before, after, ignore_order=True).to_dict()
    return DiffResult(raw=dd)

