from __future__ import annotations

"""
Hybrid AI Agent – MouseController.

Utility for moving the mouse and clicking based on a bbox string
("x,y,w,h"). This is an optional helper that higher-level executors
can use after pattern or vision matching.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class MouseActionResult:
    success: bool
    message: str


def _parse_bbox(bbox: str) -> Tuple[int, int, int, int]:
    x, y, w, h = [int(v) for v in bbox.split(",")]
    return x, y, w, h


def click_center_of_bbox(bbox: str, move_duration: float = 0.0) -> MouseActionResult:
    """
    Move the mouse to the centre of the given bbox and click.

    move_duration: seconds over which to animate the move (0 = instant).
                   Use > 0 to see the cursor move smoothly (e.g. 1.5).
    Requires the optional 'pyautogui' dependency to be installed.
    """
    try:
        import pyautogui  # type: ignore
    except Exception:
        return MouseActionResult(
            success=False,
            message="pyautogui is not installed; cannot perform mouse click.",
        )

    try:
        x, y, w, h = _parse_bbox(bbox)
        cx = x + w // 2
        cy = y + h // 2
        
        # Get current position
        try:
            curr_x, curr_y = pyautogui.position()
            print(f"    Current cursor: ({curr_x}, {curr_y})")
            print(f"    Target: ({cx}, {cy})")
            print(f"    Duration: {move_duration:.2f}s")
        except Exception:
            pass
        
        if move_duration > 0:
            print(f"    Moving cursor now (watch your screen)...")
            pyautogui.moveTo(cx, cy, duration=move_duration)
        else:
            pyautogui.moveTo(cx, cy)
        
        print(f"    Clicking...")
        pyautogui.click()
        return MouseActionResult(True, f"Clicked at centre of bbox ({cx},{cy}).")
    except Exception as exc:
        return MouseActionResult(False, f"Failed to click bbox {bbox}: {exc}")

