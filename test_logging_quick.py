"""
Quick test to verify detailed logging is working

This creates a simple task and verifies that:
1. Logs directory is created
2. HTML report is generated
3. Screenshots are captured
4. JSON and text logs are created
"""

import os
import sys
from pathlib import Path

# Enable educational mode for visible movements
os.environ["EDUCATIONAL_MODE"] = "true"
os.environ["DEBUG_MODE"] = "false"

from core.vision_agent_logged import VisionAgentLogged

print("\n" + "="*70)
print("DETAILED LOGGING VERIFICATION TEST")
print("="*70)
print()
print("This test will:")
print("1. Run a simple task with VisionAgentLogged")
print("2. Verify logs are created")
print("3. Show you where to find the HTML report")
print()
print("="*70)
print()

# Create agent with logging
agent = VisionAgentLogged()

# Simple task that should complete quickly
task = """
Look at the screen and tell me what you see.
Just observe for 1 step, then mark as done.
"""

print("Running simple observation task...")
print("(This will take just a few seconds)")
print()

try:
    result = agent.run(task)

    print()
    print("="*70)
    print("TASK COMPLETE")
    print("="*70)
    print(f"Success: {result.success}")
    print(f"Steps: {result.steps_executed}")
    print(f"Message: {result.message}")
    print()

except KeyboardInterrupt:
    print("\n\n[Test cancelled by user]")
    sys.exit(0)

except Exception as e:
    print(f"\n[Error: {e}]")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify logs were created
print()
print("="*70)
print("VERIFYING LOGS")
print("="*70)
print()

logs_dir = Path("E:/ui-agent/logs")
if not logs_dir.exists():
    print("[FAIL] Logs directory does not exist!")
    sys.exit(1)

# Find most recent log directory
log_dirs = sorted(logs_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
if not log_dirs:
    print("[FAIL] No log directories found!")
    sys.exit(1)

recent_log = log_dirs[0]
print(f"[PASS] Logs directory exists: {recent_log}")
print()

# Check for required files
required_files = [
    "execution_report.html",
    "execution_log.txt",
    "execution_log.json"
]

all_exist = True
for filename in required_files:
    filepath = recent_log / filename
    if filepath.exists():
        size = filepath.stat().st_size
        print(f"[PASS] {filename:<30} ({size:,} bytes)")
    else:
        print(f"[FAIL] {filename:<30} MISSING!")
        all_exist = False

print()

# Check screenshots directory
screenshots_dir = recent_log / "screenshots"
if screenshots_dir.exists():
    screenshot_count = len(list(screenshots_dir.glob("*.png")))
    print(f"[PASS] Screenshots directory exists ({screenshot_count} images)")
else:
    print(f"[WARN] Screenshots directory missing")

print()

if all_exist:
    print("="*70)
    print("SUCCESS - ALL LOGS CREATED!")
    print("="*70)
    print()
    print("Open this file in your browser:")
    print(f"  {recent_log / 'execution_report.html'}")
    print()
    print("You'll see:")
    print("  - Dashboard with summary")
    print("  - Every step with details")
    print("  - Screenshots before/after each action")
    print("  - LLM interactions")
    print("  - Timing information")
    print()
else:
    print("="*70)
    print("INCOMPLETE - Some logs missing")
    print("="*70)
    sys.exit(1)
