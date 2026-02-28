r"""
Simple test: Just move cursor and click.

This tests if pyautogui cursor movement is visible on your system.
Run from project root (with venv active):
  python scripts/test_cursor_movement.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pyautogui
except ImportError:
    print("ERROR: pyautogui not installed. Run: pip install pyautogui")
    sys.exit(1)


def main() -> None:
    print("=" * 70)
    print("CURSOR MOVEMENT TEST")
    print("=" * 70)
    print()
    print("This will:")
    print("  1. Get your current cursor position")
    print("  2. Move cursor to center of screen (2 seconds - WATCH IT!)")
    print("  3. Click once")
    print()
    print("Make sure you can see your screen!")
    print()
    input("Press Enter to start...")
    print()
    
    # Get current position
    curr_x, curr_y = pyautogui.position()
    print(f"Current cursor position: ({curr_x}, {curr_y})")
    
    # Get screen size
    screen_w, screen_h = pyautogui.size()
    print(f"Screen size: {screen_w}x{screen_h}")
    
    # Calculate center
    center_x = screen_w // 2
    center_y = screen_h // 2
    print(f"Target (center): ({center_x}, {center_y})")
    print()
    
    # Move cursor slowly
    print("Moving cursor NOW (watch your screen for 2 seconds)...")
    pyautogui.moveTo(center_x, center_y, duration=2.0)
    
    print("Cursor should be at center now!")
    print()
    
    # Verify position
    new_x, new_y = pyautogui.position()
    print(f"Cursor is now at: ({new_x}, {new_y})")
    
    print()
    print("Clicking in 1 second...")
    import time
    time.sleep(1)
    pyautogui.click()
    print("Clicked!")
    
    print()
    print("=" * 70)
    print("Test complete!")
    print()
    if abs(new_x - center_x) < 10 and abs(new_y - center_y) < 10:
        print("✓ SUCCESS: Cursor moved to center")
    else:
        print(f"✗ ISSUE: Cursor didn't reach target")
        print(f"  Expected: ({center_x}, {center_y})")
        print(f"  Got: ({new_x}, {new_y})")


if __name__ == "__main__":
    main()
