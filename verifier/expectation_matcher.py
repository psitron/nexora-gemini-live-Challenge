from __future__ import annotations

"""
Hybrid AI Agent – verifier.expectation_matcher

Uses NormalisedEnvironment for element-level reasoning. For now this is
a very simple matcher that checks whether a labelled element exists in
the post-state interactive list.
"""

from dataclasses import dataclass
from typing import Optional

from perception.schemas import NormalisedEnvironment


@dataclass
class Expectation:
    """
    Minimal expectation type: we expect an element with a given label
    to be present in the interactive set.
    """

    element_label: str


def is_expectation_satisfied(
    expectation: Expectation,
    post_env: Optional[NormalisedEnvironment],
) -> bool:
    if post_env is None:
        return False
    for el in post_env.interactive:
        if el.label == expectation.element_label:
            return True
    return False

