from __future__ import annotations

"""
Hybrid AI Agent – Start Menu Search Helper.

Opens Windows Start menu search, types query, opens first result (Enter).
"""

import time

try:
    import pyautogui
except ImportError:
    pyautogui = None

from core.human_timing import HumanTiming
from execution.level0_programmatic import ActionResult


class StartMenuSearchHelper:
    """
    Opens Start menu, searches for an app, opens first result.
    """

    def __init__(self) -> None:
        self._timing = HumanTiming()

    def search_and_click(self, app_name: str) -> ActionResult:
        """
        Open Start menu search (Win+S), type app_name, press Enter.
        Returns ActionResult with success=True if app opened.
        """
        if pyautogui is None:
            return ActionResult(False, "pyautogui not installed")

        # Open Start menu search
        print(f"  Opening Start menu search...")
        try:
            pyautogui.hotkey("win", "s")
            self._timing.wait_for_search_results()
        except Exception as e:
            return ActionResult(False, f"Failed to open Start menu: {e}")

        # Draw one red box around the search area on the PRIMARY_MONITOR
        try:
            from core.visual_annotator import highlight_bbox
            from core.monitor_utils import search_box_bbox_on_selected_monitor
            bbox = search_box_bbox_on_selected_monitor()
            if bbox:
                highlight_bbox(bbox, duration=1.5)
            else:
                # Fallback: primary monitor center-top
                screen_w, screen_h = pyautogui.size()
                x, y = screen_w // 2 - 320, int(screen_h * 0.12)
                highlight_bbox(f"{x},{y},640,56", duration=1.5)
        except Exception as e:
            print(f"  [Could not draw search box highlight: {e}]")

        # Type query
        print(f"  Typing '{app_name}'...")
        try:
            for i, char in enumerate(app_name, 1):
                pyautogui.write(char, interval=0)
                time.sleep(self._timing.typing_interval())
                if i % 3 == 0:
                    print(f"    Typed: {app_name[:i]}")
            print(f"    Typed: {app_name}")
            self._timing.wait_for_search_results()
        except Exception as e:
            return ActionResult(False, f"Failed to type: {e}")

        # Find the search result with OCR and annotate it before clicking
        print(f"  Finding '{app_name}' in search results with OCR...")
        try:
            from core.ocr_finder import find_text_on_screen
            from core.visual_annotator import highlight_bbox
            from core.monitor_utils import get_selected_monitor
            
            # Search in the selected monitor area (Start menu results are typically center-left)
            monitor_rect = get_selected_monitor()
            if monitor_rect:
                left, top, right, bottom = monitor_rect
                # Search region: left half of screen, center vertical area
                search_x = left
                search_y = top + int((bottom - top) * 0.2)
                search_w = int((right - left) * 0.5)
                search_h = int((bottom - top) * 0.6)
                search_region = (search_x, search_y, search_w, search_h)
                
                result_bbox = find_text_on_screen(app_name, region=search_region, timeout=2.0)
                if result_bbox:
                    x, y, w, h = result_bbox
                    print(f"  Found '{app_name}' at ({x},{y}) size {w}x{h}")
                    # Draw red box around the result
                    highlight_bbox(f"{x},{y},{w},{h}", duration=1.5, fade_out_seconds=2.0)
                    # Move cursor to result and click
                    cx, cy = x + w // 2, y + h // 2
                    from core.human_timing import HumanTiming
                    timing = HumanTiming()
                    timing.before_click()
                    # Calculate distance for smooth movement
                    try:
                        curr_x, curr_y = pyautogui.position()
                        distance = ((cx - curr_x) ** 2 + (cy - curr_y) ** 2) ** 0.5
                        move_duration = timing.cursor_move_duration(int(distance))
                        pyautogui.moveTo(cx, cy, duration=move_duration)
                    except Exception:
                        pyautogui.moveTo(cx, cy, duration=1.0)
                    pyautogui.click()
                    timing.after_click()
                    self._timing.wait_for_window()
                    return ActionResult(True, f"Opened '{app_name}' by clicking OCR result")
        except Exception as e:
            print(f"  [OCR search failed: {e}]")

        # Fallback: Open first result with Enter
        print(f"  Pressing Enter to open first result (OCR fallback)...")
        try:
            self._timing.short_pause()
            pyautogui.press("enter")
            self._timing.wait_for_window()
            return ActionResult(True, f"Opened '{app_name}' via Start menu search")
        except Exception as e:
            return ActionResult(False, f"Failed to press Enter: {e}")
