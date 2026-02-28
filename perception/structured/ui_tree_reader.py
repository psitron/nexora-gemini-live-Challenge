from __future__ import annotations

"""
Hybrid AI Agent – UI tree reader.

pywinauto-based Windows UI Automation (UIA) tree extraction.

Responsibilities:
- Attach to the active (foreground) window
- Walk its control tree using UIA backend
- Return a list of elements with name, control_type, automation_id
  that EnvironmentNormaliser can consume.
"""

from typing import Any, Dict, List, Optional

from pywinauto import Desktop
from pywinauto.base_wrapper import BaseWrapper


class UiTreeReader:
    """
    Asynchronous-friendly wrapper around pywinauto Desktop UI tree.

    Returns a flat list of controls from the active window in the form:
    [
        {
            "name": "OK",
            "control_type": "Button",
            "automation_id": "1",
        },
        ...
    ]
    """

    def __init__(self, backend: str = "uia") -> None:
        self._backend = backend

    async def read(self) -> List[Dict[str, Any]]:
        """
        Inspect the foreground window and return a list of UI elements.

        This method is defined as async for compatibility with the rest
        of the perception pipeline but internally uses synchronous
        pywinauto calls.
        """
        try:
            desktop = Desktop(backend=self._backend)
            active: Optional[BaseWrapper] = desktop.active()
        except Exception:
            return []

        if active is None:
            return []

        elements: List[Dict[str, Any]] = []

        try:
            # depth=2/3 keeps traversal cheap but useful; can be tuned later.
            for ctrl in active.descendants(depth=3):
                try:
                    info = ctrl.element_info
                    name = info.name or ""
                    control_type = info.control_type or ""
                    automation_id = info.automation_id or ""

                    if not (name or control_type or automation_id):
                        continue

                    elements.append(
                        {
                            "name": name,
                            "control_type": control_type,
                            "automation_id": automation_id,
                        }
                    )
                except Exception:
                    # Skip any problematic control; best-effort enumeration.
                    continue
        except Exception:
            # If traversal fails entirely, return what we have (likely empty).
            return elements

        return elements

