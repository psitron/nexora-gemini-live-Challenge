"""
Validate that the red annotation box is visible on your screen.

The red box is drawn on the monitor WHERE YOUR MOUSE CURSOR IS.
So: move your mouse to the screen you want to check, then run this script.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pyautogui
except ImportError:
    pyautogui = None

from core.monitor_utils import get_monitor_rect_containing_cursor


def draw_red_box_win32(x: int, y: int, w: int, h: int) -> bool:
    """Draw red rectangle using Win32 GDI. Returns True if drawn."""
    try:
        import win32gui
        import win32con
        import win32api
    except ImportError as e:
        print(f"ERROR: Win32 not available: {e}")
        print("  Install: pip install pywin32")
        return False

    try:
        hdc = win32gui.GetDC(0)
        pen = win32gui.CreatePen(win32con.PS_SOLID, 8, win32api.RGB(255, 0, 0))
        old_pen = win32gui.SelectObject(hdc, pen)
        win32gui.Rectangle(hdc, x, y, x + w, y + h)
        win32gui.SelectObject(hdc, old_pen)
        win32gui.DeleteObject(pen)
        win32gui.ReleaseDC(0, hdc)
        return True
    except Exception as e:
        print(f"ERROR: Win32 draw failed: {e}")
        return False


def main() -> None:
    print("=" * 60)
    print("ANNOTATION VISIBILITY CHECK (multi-monitor)")
    print("=" * 60)
    print()
    print("The red box is drawn on the monitor WHERE YOUR CURSOR IS.")
    print()
    print("  1. Move your mouse to the screen you want to test.")
    print("  2. In 2 seconds a LARGE RED BOX will appear in the center")
    print("     of THAT screen for 5 seconds.")
    print()
    print("  -> If you SEE it: annotation works on that screen.")
    print("  -> If you do NOT: we debug (wrong monitor, etc.).")
    print()
    time.sleep(2)

    if not pyautogui:
        print("ERROR: pyautogui not installed.")
        sys.exit(1)

    rect = get_monitor_rect_containing_cursor()
    if not rect:
        # Fallback: primary monitor (pyautogui.size())
        screen_w, screen_h = pyautogui.size()
        x, y = (screen_w - 400) // 2, (screen_h - 200) // 2
        w, h = 400, 200
        print(f"Using primary monitor. Drawing at ({x},{y}) size {w}x{h}")
    else:
        left, top, right, bottom = rect
        w, h = 400, 200
        x = left + (right - left - w) // 2
        y = top + (bottom - top - h) // 2
        print(f"Monitor under cursor: rect ({left},{top}) to ({right},{bottom})")
        print(f"Drawing red box at center of that monitor: ({x},{y}) size {w}x{h}")

    print()
    print(">>> LOOK AT THE SCREEN WHERE YOUR CURSOR IS <<<")
    print()

    ok = draw_red_box_win32(x, y, w, h)
    if not ok:
        sys.exit(1)

    time.sleep(5)

    try:
        cx, cy = pyautogui.position()
        pyautogui.moveTo(cx + 2, cy)
        pyautogui.moveTo(cx, cy)
    except Exception:
        pass

    print()
    print("Did you see the red box on that screen? (y/n)")
    print()


if __name__ == "__main__":
    main()
