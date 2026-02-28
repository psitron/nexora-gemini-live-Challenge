r"""
Demo: Human-Like Visual Automation

Shows the agent opening Control Panel like a human:
1. Looks at desktop for Control Panel icon (vision)
2. If not found, opens Start menu search
3. Types "Control Panel" slowly
4. Finds result in search (vision)
5. Moves cursor smoothly and clicks

Run from project root (with venv active):
  python scripts/demo_human_like_control_panel.py

Requirements:
- GEMINI_API_KEY in .env
- pyautogui installed
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.level2_ui_tree import Level2UiTreeExecutor


def main() -> None:
    print("=" * 70)
    print("HUMAN-LIKE VISUAL AUTOMATION DEMO")
    print("=" * 70)
    print()
    print("Task: Open Control Panel")
    print()
    print("Watch as the agent:")
    print("  1. Looks for Control Panel icon on desktop (Gemini vision)")
    print("  2. If not found, opens Start menu search (Win+S)")
    print("  3. Types 'Control Panel' slowly (human-like)")
    print("  4. Finds result in search (Gemini vision)")
    print("  5. Moves cursor smoothly to result (~1.2 seconds)")
    print("  6. Pauses briefly before clicking (human-like)")
    print("  7. Clicks")
    print()
    print("=" * 70)
    print()
    input("Press Enter to start (make sure you can see your screen)...")
    print()
    
    executor = Level2UiTreeExecutor()
    result = executor.desktop_click("Control Panel")
    
    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print()
    
    if result.success:
        print("✓ Control Panel opened with human-like automation!")
    else:
        print("✗ Failed. Possible reasons:")
        print("  - GEMINI_API_KEY not configured in .env")
        print("  - Gemini quota exceeded")
        print("  - Control Panel not found on desktop or in Start menu")
    
    print()
    print("Try other items:")
    print("  - Calculator: python -c \"from execution.level2_ui_tree import Level2UiTreeExecutor; Level2UiTreeExecutor().desktop_click('Calculator')\"")
    print("  - Notepad: python -c \"from execution.level2_ui_tree import Level2UiTreeExecutor; Level2UiTreeExecutor().desktop_click('Notepad')\"")


if __name__ == "__main__":
    main()
