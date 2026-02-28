from __future__ import annotations

"""
Hybrid AI Agent – ElementID resolver.

Builds ElementID instances from NormalisedElement records and provides
simple lookup helpers.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from element_id.element_id import ElementID
from perception.schemas import NormalisedElement


@dataclass
class ElementResolutionResult:
    element_id: ElementID
    element: NormalisedElement


def from_normalised(element: NormalisedElement) -> ElementID:
    """
    Construct an ElementID from a NormalisedElement, filling the
    fallback chain from all available sources.
    """
    return ElementID(
        label=element.label,
        dom_locator=element.dom_locator,
        ui_tree_id=element.ui_tree_id,
        bbox=element.bbox,
        source=(element.sources[0] if element.sources else None),
    )


def index_by_label(elements: List[NormalisedElement]) -> Dict[str, ElementResolutionResult]:
    """
    Build a simple index of label -> ElementResolutionResult.
    Later this can be extended to more advanced matching, but for
    v1 it is sufficient for many tasks.
    """
    index: Dict[str, ElementResolutionResult] = {}
    for el in elements:
        if not el.label:
            continue
        if el.label in index:
            # Keep the first occurrence for now; more complex
            # disambiguation can be added later.
            continue
        eid = from_normalised(el)
        index[el.label] = ElementResolutionResult(element_id=eid, element=el)
    return index


def resolve_by_label(
    label: str,
    elements: List[NormalisedElement],
) -> Optional[ElementResolutionResult]:
    """
    Convenience helper to resolve a single label from a list of
    NormalisedElement objects.
    """
    index = index_by_label(elements)
    return index.get(label)
