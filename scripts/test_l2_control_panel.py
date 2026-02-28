r"""
Simple direct test: L2 desktop_click for Control Panel.

Tests the enhanced L2 executor directly (no full agent loop).
Run from project root (with venv active):
  python scripts/test_l2_control_panel.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.level2_ui_tree import Level2UiTreeExecutor


def main() -> None:
    print("Testing L2 desktop_click with Control Panel...")
    print("-" * 60)
    
    executor = Level2UiTreeExecutor()
    result = executor.desktop_click("Control Panel")
    
    print(f"Result: {result.success}")
    print(f"Message: {result.message}")
    
    if result.success:
        print("\nSuccess! Check if Control Panel window opened.")
        print("(Give it 2-3 seconds to appear)")
        time.sleep(3)
    else:
        print("\nFailed. This might work better if you:")
        print("  1. Have Control Panel pinned or visible")
        print("  2. Try other items like 'File Explorer', 'Calculator'")
    
    # Try a few more common items
    print("\n" + "=" * 60)
    print("Testing other common items:")
    print("=" * 60)
    
    items_to_test = ["Calculator", "Notepad"]
    for item in items_to_test:
        print(f"\n{item}:")
        result = executor.desktop_click(item)
        print(f"  -> {result.success}: {result.message}")
        if result.success:
            time.sleep(1)


if __name__ == "__main__":
    main()
