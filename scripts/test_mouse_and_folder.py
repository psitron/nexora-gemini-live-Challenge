r"""
Create a folder using the mouse cursor (and keyboard) in File Explorer.

1. Opens File Explorer at the given directory.
2. Moves the cursor smoothly into the Explorer window and clicks (so you see it).
3. Uses Ctrl+Shift+N to create a new folder, types the name, Enter.

Run from project root (with venv active):
  python scripts/test_mouse_and_folder.py
  python scripts/test_mouse_and_folder.py "E:/ui-agent/sessions"

Requires: pip install pyautogui pywinauto
"""

from __future__ import annotations

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def open_explorer_at(path: Path) -> None:
    """Start File Explorer with the given folder open."""
    subprocess.Popen(["explorer", str(path.resolve())], shell=False)


def bring_explorer_to_front_and_get_rect(path: Path) -> tuple[int, int, int, int] | None:
    """Find an Explorer window showing this path; bring to front; return (left, top, right, bottom)."""
    try:
        from pywinauto import Desktop
        from pywinauto.findwindows import find_elements

        time.sleep(1.2)
        desktop = Desktop(backend="uia")
        # Find windows with "File Explorer" or path in title
        path_str = str(path).replace("/", "\\")
        for win in desktop.windows():
            try:
                title = win.window_text()
                if "File Explorer" in title or path_str in title or path.name in title:
                    win.set_focus()
                    time.sleep(0.3)
                    r = win.rectangle()
                    return (r.left, r.top, r.right, r.bottom)
            except Exception:
                continue
        # Fallback: any Explorer window
        for win in desktop.windows():
            try:
                if "explorer" in win.window_text().lower() or win.class_name() == "CabinetWClass":
                    win.set_focus()
                    time.sleep(0.3)
                    r = win.rectangle()
                    return (r.left, r.top, r.right, r.bottom)
            except Exception:
                continue
    except Exception:
        pass
    return None


def main() -> None:
    base_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "sessions"
    base_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"mouse_test_{stamp}"

    print("Step 1: Open File Explorer at directory")
    print(f"  {base_dir}")
    open_explorer_at(base_dir)

    print("\nStep 2: Bring Explorer to front and find window...")
    rect = bring_explorer_to_front_and_get_rect(base_dir)
    if not rect:
        print("  Could not find Explorer window. Moving to screen center instead.")
        try:
            import pyautogui
            w, h = pyautogui.size()
            cx, cy = w // 2, h // 2
        except Exception:
            cx, cy = 960, 540
    else:
        left, top, right, bottom = rect
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        print(f"  Window center: ({cx}, {cy})")

    print("\nStep 3: Move cursor into Explorer and click (watch the cursor)...")
    try:
        import pyautogui
        duration = 1.8
        pyautogui.moveTo(cx, cy, duration=duration)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.4)
    except ImportError:
        print("  pyautogui not installed. Run: pip install pyautogui")
        sys.exit(1)

    print("Step 4: Create new folder (Ctrl+Shift+N), type name, Enter...")
    try:
        import pyautogui
        pyautogui.hotkey("ctrl", "shift", "n")
        time.sleep(0.6)
        pyautogui.write(folder_name, interval=0.05)
        time.sleep(0.2)
        pyautogui.press("enter")
    except Exception as e:
        print(f"  Failed: {e}")
        sys.exit(1)

    print(f"\nDone. Folder '{folder_name}' should appear in Explorer.")
    expected_path = base_dir / folder_name
    if expected_path.exists():
        print(f"  Confirmed: {expected_path}")
    else:
        print("  (Folder may take a moment to appear; check Explorer.)")


if __name__ == "__main__":
    main()
