"""
Test Coordinate Logging

This test will show detailed coordinate transformation logging
to diagnose the multi-monitor coordinate scaling issue.

Usage:
    python test_coordinate_logging.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import agent
from core.vision_agent_logged import VisionAgentLogged

def main():
    print("="*70)
    print("COORDINATE LOGGING TEST")
    print("="*70)
    print()
    print("This test will run a simple task and show detailed coordinate logging.")
    print("Watch for the COORDINATE TRANSFORMATION sections in the output.")
    print()
    print("Environment settings:")
    print(f"  PRIMARY_MONITOR: {os.getenv('PRIMARY_MONITOR', '1')}")
    print(f"  EDUCATIONAL_MODE: {os.getenv('EDUCATIONAL_MODE', 'true')}")
    print(f"  VISION_PROVIDER: {os.getenv('VISION_PROVIDER', 'gemini')}")
    print()

    # Simple task
    task = """
    Open Windows search (click the search icon in taskbar).

    Just do this ONE action, then say done.
    """

    print("Task: Open Windows search")
    print()
    print("="*70)
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

if __name__ == "__main__":
    main()
