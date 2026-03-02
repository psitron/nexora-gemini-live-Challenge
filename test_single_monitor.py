"""
Test Single Monitor Mode

Simple test to verify the agent works correctly on a single monitor (monitor 2).
"""

import os
from dotenv import load_dotenv
load_dotenv()

from core.vision_agent_logged import VisionAgentLogged

def main():
    print("="*70)
    print("SINGLE MONITOR TEST (Monitor 2 - Middle)")
    print("="*70)
    print()
    print(f"PRIMARY_MONITOR: {os.getenv('PRIMARY_MONITOR', '?')}")
    print()
    print("This test will perform ONE simple action to verify:")
    print("  1. Screenshot is captured from correct monitor")
    print("  2. Coordinates are scaled correctly (no offset needed)")
    print("  3. Annotation appears in correct position")
    print("  4. Click happens at correct position")
    print()
    print("="*70)
    print()

    # Very simple task - just open search
    task = """
    Click the Windows search icon in the taskbar (bottom-left corner).

    After clicking it once, say "done".
    """

    print("Task: Click Windows search icon")
    print()
    input("Press ENTER to start (make sure you're looking at Monitor 2 - middle monitor)...")
    print()

    # Create agent with logging
    agent = VisionAgentLogged()

    # Run task
    result = agent.run(task)

    print()
    print("="*70)
    print("RESULT:")
    print(f"  Success: {result.success}")
    print(f"  Steps: {result.steps_executed}")
    print(f"  Message: {result.message}")
    print("="*70)
    print()

    # Check the logs
    import glob
    log_dirs = sorted(glob.glob("logs/*/execution_log.json"), reverse=True)
    if log_dirs:
        latest_log = log_dirs[0]
        print(f"Latest log: {latest_log}")
        print()
        print("Check the log file to see if coordinates are in the correct range:")
        print("  Expected hint_x: 0 to 1920")
        print("  Expected hint_y: 0 to 1080")
        print()

if __name__ == "__main__":
    main()
