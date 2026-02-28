r"""
Demo: AI Teacher with Visual Annotations

Shows the hybrid teaching approach:
- Visual annotations (red boxes, text labels)
- Keyboard shortcut indicators
- Step-by-step explanations
- Typing demonstration

Perfect for training/teaching demonstrations!

Run from project root (with venv active):
  python scripts/demo_ai_teacher.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.level2_ui_tree import Level2UiTreeExecutor


def main() -> None:
    print("=" * 70)
    print("AI TEACHER DEMO - Visual Annotations for Training")
    print("=" * 70)
    print()
    print("This demonstrates the HYBRID teaching approach:")
    print()
    print("- Visual annotations (red boxes highlighting elements)")
    print("- Text labels explaining each step")
    print("- Keyboard shortcut indicators (Win+S, Enter)")
    print("- Human-like timing")
    print()
    print("Perfect for:")
    print("  - Teaching computer skills to students")
    print("  - Training demonstrations")
    print("  - Recording tutorials")
    print("  - Screen sharing lessons")
    print()
    print("=" * 70)
    print()
    print("Task: Open Control Panel")
    print()
    print("Watch for:")
    print("  1. Action label: 'Opening Start Menu Search'")
    print("  2. Keyboard indicator: 'Win+S'")
    print("  3. Red box highlight around search box")
    print("  4. Each letter typed slowly")
    print("  5. Action label: 'Pressing Enter'")
    print("  6. Keyboard indicator: 'Enter'")
    print("  7. Success message!")
    print()
    input("Press Enter to start the AI teacher demonstration...")
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
        print("- AI Teacher demonstration complete!")
        print()
        print("What you should have seen:")
        print("  - Visual annotations explaining each action")
        print("  - Red box highlighting the search box")
        print("  - Keyboard shortcuts visualized")
        print("  - Control Panel opened")
    else:
        print("x Demo had issues. Check the console output above.")
    
    print()
    print("Try teaching other tasks:")
    print("  python scripts/demo_ai_teacher.py")
    print()
    print("Customize annotations in: core/visual_annotator.py")


if __name__ == "__main__":
    main()
