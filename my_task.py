"""
Simple script to run any task with the vision agent.

Usage:
    python my_task.py "open notepad and type hello"
    python my_task.py "search for cat pictures online"
    python my_task.py "open calculator and calculate 25 * 37"
"""

import sys
from core.vision_agent_logged import VisionAgentLogged

def main():
    if len(sys.argv) < 2:
        print("Usage: python my_task.py \"your task here\"")
        print()
        print("Examples:")
        print("  python my_task.py \"open notepad and write a poem\"")
        print("  python my_task.py \"open calculator and calculate 123 + 456\"")
        print("  python my_task.py \"search google for python tutorials\"")
        print("  python my_task.py \"open paint and draw a circle\"")
        sys.exit(1)

    # Get task from command line
    task = " ".join(sys.argv[1:])

    print("="*70)
    print("VISION AGENT - FREE TASK MODE")
    print("="*70)
    print()
    print(f"Task: {task}")
    print()
    print("Starting agent...")
    print("="*70)
    print()

    # Run agent
    agent = VisionAgentLogged()
    result = agent.run(task)

    print()
    print("="*70)
    print("RESULT")
    print("="*70)
    print(f"Success: {result.success}")
    print(f"Steps executed: {result.steps_executed}")
    print(f"Message: {result.message}")
    print()

    if result.success:
        print("[SUCCESS] Agent completed the task!")
    else:
        print(f"[INCOMPLETE] Agent stopped: {result.message}")

    print()
    print("Check logs/ directory for detailed execution logs and screenshots")
    print("="*70)

if __name__ == "__main__":
    main()
