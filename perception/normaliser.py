from __future__ import annotations

"""
Hybrid AI Agent – EnvironmentNormaliser.

Merges DOM, UI tree, and (optionally) visual elements into a single
NormalisedEnvironment, as per the PRD.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from perception.schemas import NormalisedElement, NormalisedEnvironment


class EnvironmentNormaliser:
    def normalise(
        self,
        dom: Optional[Dict[str, Any]],
        ui_tree: Optional[List[Dict[str, Any]]],
        visual: Optional[List[Dict[str, Any]]] = None,
        window_title: str = "",
        window_type: str = "unknown",
        current_url: Optional[str] = None,
        app_name: str = "",
    ) -> NormalisedEnvironment:
        elements = self._merge_elements(dom or {}, ui_tree or [], visual or [])
        interactive = [e for e in elements if e.state == "enabled" and e.element_type in {"button", "input", "link"}]

        source_hash = str(hash(str(dom) + str(ui_tree) + str(visual)))

        return NormalisedEnvironment(
            window_title=window_title,
            window_type=window_type,
            current_url=current_url,
            app_name=app_name,
            elements=elements,
            interactive=interactive,
            timestamp=datetime.utcnow(),
            source_hash=source_hash,
        )

    def _merge_elements(
        self,
        dom_els: Dict[str, Any],
        tree_els: List[Dict[str, Any]],
        vis_els: List[Dict[str, Any]],
    ) -> List[NormalisedElement]:
        """
        Minimal merge strategy:
        - Start with DOM elements as authoritative
        - Attach matching UI tree elements by text
        - Attach visual elements by label (if present)
        """
        normalised: List[NormalisedElement] = []

        # Expect dom_els to look like {"elements": [{...}, ...]}
        for dom_el in dom_els.get("elements", []):
            ne = NormalisedElement(
                id=str(uuid4()),
                label=dom_el.get("label") or dom_el.get("text", "") or "",
                element_type=self._map_dom_type(dom_el.get("tag", "")),
                text_content=dom_el.get("text"),
                state="enabled" if not dom_el.get("disabled") else "disabled",
                sources=["dom"],
                dom_locator=dom_el.get("selector"),
                ui_tree_id=None,
                bbox=None,
                confidence=1.0,
            )
            normalised.append(ne)

        # Simple append of UI tree elements not already present by label
        existing_labels = {e.label for e in normalised}
        for ui_el in tree_els:
            label = ui_el.get("name", "")
            if label in existing_labels:
                continue
            ne = NormalisedElement(
                id=str(uuid4()),
                label=label,
                element_type=self._map_ui_control_type(ui_el.get("control_type", "")),
                text_content=label,
                state="enabled",
                sources=["ui_tree"],
                dom_locator=None,
                ui_tree_id=ui_el.get("automation_id"),
                bbox=None,
                confidence=0.8,
            )
            normalised.append(ne)

        # Visual elements appended as separate entries (for now)
        for vis in vis_els:
            label = vis.get("label", "")
            ne = NormalisedElement(
                id=str(uuid4()),
                label=label,
                element_type="container",
                text_content=label,
                state="enabled",
                sources=["visual"],
                dom_locator=None,
                ui_tree_id=None,
                bbox=vis.get("bbox"),
                confidence=float(vis.get("confidence", 0.7)),
            )
            normalised.append(ne)

        return normalised

    @staticmethod
    def _map_dom_type(tag: str) -> str:
        tag = tag.lower()
        if tag in {"button", "input", "a"}:
            if tag == "a":
                return "link"
            if tag == "input":
                return "input"
            return "button"
        if tag in {"img", "image"}:
            return "image"
        if tag in {"div", "span", "section"}:
            return "container"
        return "text"

    @staticmethod
    def _map_ui_control_type(control_type: str) -> str:
        ct = control_type.lower()
        if "button" in ct:
            return "button"
        if "edit" in ct or "textbox" in ct:
            return "input"
        if "link" in ct:
            return "link"
        return "container"

