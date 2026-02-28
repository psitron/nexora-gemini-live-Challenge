r"""
Direct test: Open Start menu, type, and move cursor to a fixed position.

This bypasses vision to test just the typing + cursor movement parts.
Run from project root (with venv active):
  python scripts/test_start_menu_typing.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pyautogui
except ImportError:
    print("ERROR: pyautogui not installed")
    sys.exit(1)

from core.human_timing import HumanTiming


def main() -> None:
    timing = HumanTiming()
    
    print("=" * 70)
    print("START MENU TYPING + CURSOR MOVEMENT TEST")
    print("=" * 70)
    print()
    print("This will:")
    print("  1. Open Start menu (Win+S)")
    print("  2. Type 'Calculator' slowly (you'll see each letter)")
    print("  3. Wait for results")
    print("  4. Move cursor to center of screen (simulating clicking result)")
    print("  5. Click")
    print()
    input("Press Enter to start (watch your screen)...")
    print()
    
    # Step 1: Open Start menu
    print("1. Opening Start menu (Win+S)...")
    pyautogui.hotkey("win", "s")
    timing.wait_for_search_results()
    
    # Step 2: Type slowly
    print("2. Typing 'Calculator' slowly (watch each letter)...")
    text = "Calculator"
    for i, char in enumerate(text, 1):
        print(f"   Typing: {char}")
        pyautogui.write(char, interval=0)
        time.sleep(timing.typing_interval())
    
    print("3. Waiting for search results...")
    timing.wait_for_search_results()
    
    # Step 4: Get current cursor position
    curr_x, curr_y = pyautogui.position()
    print(f"4. Current cursor: ({curr_x}, {curr_y})")
    
    # Calculate center (simulating where result would be)
    screen_w, screen_h = pyautogui.size()
    center_x = screen_w // 2
    center_y = screen_h // 2
    print(f"   Target: ({center_x}, {center_y})")
    
    # Calculate distance
    distance = ((center_x - curr_x) ** 2 + (center_y - curr_y) ** 2) ** 0.5
    move_duration = timing.cursor_move_duration(int(distance))
    print(f"   Distance: {distance:.0f}px, Duration: {move_duration:.2f}s")
    
    # Step 5: Move cursor
    print(f"5. Moving cursor NOW (watch for {move_duration:.1f} seconds)...")
    timing.before_click()
    pyautogui.moveTo(center_x, center_y, duration=move_duration)
    
    print("6. Pausing before click...")
    timing.before_click()
    
    print("7. Clicking...")
    pyautogui.click()
    
    print("8. Pausing after click...")
    timing.after_click()
    
    print()
    print("=" * 70)
    print("✓ Test complete!")
    print()
    print("You should have seen:")
    print("  - Start menu open")
    print("  - 'Calculator' typed letter by letter")
    print("  - Cursor move smoothly to center")
    print("  - Click")


if __name__ == "__main__":
    main()
