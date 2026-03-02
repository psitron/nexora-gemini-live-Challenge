"""
Educational Excel Demonstration

This script demonstrates the educational mouse controller with a real Excel task.
Students will SEE:
- Visible mouse movements (slow, smooth)
- Where to click (with red box annotations)
- When to use shortcuts vs mouse
- Complete workflow from start to finish

Task: Create a simple budget spreadsheet with SUM formula
"""

import os
import sys

# Set educational mode BEFORE importing agent
os.environ["EDUCATIONAL_MODE"] = "true"  # Enable visible movements
os.environ["DEBUG_MODE"] = "false"

# Use VisionAgentLogged for detailed logging
from core.vision_agent_logged import VisionAgentLogged


def demonstrate_excel_basics():
    """
    Demonstrate Excel basics with visible mouse movements.

    Task: Create a budget spreadsheet
    1. Open Excel
    2. Enter "Income" label
    3. Enter some numbers
    4. Create SUM formula
    5. Format as currency

    Students learn:
    - Where to click
    - What to type
    - When to use shortcuts
    - How formulas work
    """

    print("\n" + "=" * 70)
    print("EDUCATIONAL DEMONSTRATION: Excel Budget Creation")
    print("=" * 70)
    print()
    print("NOTICE: Educational mode is ENABLED")
    print("  - Mouse movements will be VISIBLE and SLOW")
    print("  - Students can follow along")
    print("  - Red boxes show targets")
    print("  - Pauses between actions")
    print()
    print("Task: Create a simple budget with SUM formula")
    print()
    print("=" * 70)
    print()

    agent = VisionAgentLogged()

    # Detailed task with teaching context
    task = """
Open Excel and create a simple budget spreadsheet:

STEP 1: Open Excel
- Click the Start menu or search for Excel
- Wait for Excel to open

STEP 2: Create labels and data
- Click cell A1, type "Income"
- Press Enter to move to A2
- Type "Salary: 5000"
- Press Enter to A3
- Type "Freelance: 2000"
- Press Enter to A4
- Type "Total:"

STEP 3: Create SUM formula
- Click cell B4
- Type the formula: =B1+B2+B3
- Press Enter to calculate

STEP 4 (OPTIONAL): Format as currency
- Select cells B1:B4
- Click the Currency button in the ribbon (or press Ctrl+Shift+$)

Remember: We use BOTH mouse clicks (to show where things are) AND keyboard shortcuts (to be efficient).
Students need to SEE where to click, then learn the fast way!

Complete the task step by step.
"""

    print("Starting educational demonstration...")
    print()
    print("TIP: Watch the mouse cursor move smoothly between actions")
    print("TIP: Notice the red boxes showing EXACTLY what to click")
    print("TIP: See the pauses before and after each action")
    print()
    print("LOGGING: Every step will be logged with screenshots!")
    print("         You'll get an HTML report at the end")
    print()
    input("Press Enter when Excel is visible on your screen...")

    # Run the task with detailed logging
    result = agent.run(task)

    print()
    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    print(f"Success: {result.success}")
    print(f"Steps executed: {result.steps_executed}")
    print(f"Message: {result.message}")
    print()

    if result.success:
        print("✅ GREAT! Students saw:")
        print("  - Visible mouse movements to each cell")
        print("  - Red boxes highlighting targets")
        print("  - Natural pauses to observe")
        print("  - Combination of mouse + keyboard")
    else:
        print("⚠️  Task incomplete, but students still learned from watching:")
        print("  - Mouse movement techniques")
        print("  - Where UI elements are located")
        print("  - How to interact step-by-step")

    print()
    print("=" * 70)
    print()


def show_educational_settings():
    """Show current educational mode configuration"""
    print("\n" + "=" * 70)
    print("EDUCATIONAL MODE CONFIGURATION")
    print("=" * 70)
    print()

    from execution.educational_mouse_controller import EducationalMouseController

    controller = EducationalMouseController(educational_mode=True)

    print("Current settings for student learning:")
    print()
    print(f"  Movement Duration: {controller.MOVEMENT_DURATION}s")
    print(f"    - Mouse takes {controller.MOVEMENT_DURATION}s to move to target")
    print(f"    - Students can follow with their eyes")
    print(f"    - Not too fast, not too slow")
    print()
    print(f"  Pause Before Click: {controller.PAUSE_BEFORE_CLICK}s")
    print(f"    - Let students see what we're about to click")
    print(f"    - Brain processes the target")
    print()
    print(f"  Pause After Click: {controller.PAUSE_AFTER_CLICK}s")
    print(f"    - Let students see the result")
    print(f"    - Understand what happened")
    print()
    print("For different skill levels, you can adjust:")
    print()
    print("  Beginners (slower):")
    print("    MOVEMENT_DURATION = 1.2")
    print("    PAUSE_BEFORE_CLICK = 0.5")
    print("    PAUSE_AFTER_CLICK = 0.7")
    print()
    print("  Advanced (faster):")
    print("    MOVEMENT_DURATION = 0.5")
    print("    PAUSE_BEFORE_CLICK = 0.2")
    print("    PAUSE_AFTER_CLICK = 0.3")
    print()
    print("To disable educational mode (for production speed):")
    print("    Set EDUCATIONAL_MODE=false in .env")
    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("EDUCATIONAL EXCEL DEMONSTRATION")
    print("=" * 70)
    print()
    print("This demonstration shows how the AI agent teaches students")
    print("by using VISIBLE mouse movements instead of instant clicks.")
    print()
    print("Perfect for teaching Excel, Word, or any software!")
    print()
    print("=" * 70)
    print()

    # Show menu
    print("Options:")
    print()
    print("1. Show educational mode settings")
    print("2. Run Excel demonstration (RECOMMENDED)")
    print("3. Exit")
    print()

    choice = input("Enter choice (1-3): ").strip()

    if choice == "1":
        show_educational_settings()
        print()
        input("Press Enter to continue...")
        sys.exit(0)
    elif choice == "2":
        demonstrate_excel_basics()
    else:
        print("\nExiting...")
        sys.exit(0)
