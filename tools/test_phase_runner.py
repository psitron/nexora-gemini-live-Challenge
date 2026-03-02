"""
Phased Test Runner - Guides through step-by-step testing

Usage:
    python tools/test_phase_runner.py
"""

import sys
from pathlib import Path

print("=" * 70)
print("PHASED TEST RUNNER")
print("=" * 70)
print()
print("This will guide you through testing each component individually.")
print("We fix ONE thing at a time, test it, verify it works, then move on.")
print()
print("=" * 70)
print()

# ============================================================================
# PHASE 1: Run Diagnostics
# ============================================================================
print("PHASE 1: DIAGNOSTICS")
print("-" * 70)
print()
print("First, let's see what's currently broken.")
print()
print("Run this command:")
print("  python tools/diagnostic_full.py")
print()
print("This will check:")
print("  - Is Tesseract OCR installed?")
print("  - Can Python use OCR?")
print("  - Does loop detection code exist?")
print("  - Did loop detection trigger in last run?")
print("  - Is reflection agent integrated?")
print()

response = input("Have you run the diagnostic? (yes/no): ").strip().lower()

if response != 'yes':
    print()
    print("Please run the diagnostic first:")
    print("  python tools/diagnostic_full.py")
    print()
    print("Share the output, then we'll decide what to fix.")
    sys.exit(0)

print()

# ============================================================================
# PHASE 2: OCR Check
# ============================================================================
print("PHASE 2: OCR VERIFICATION")
print("-" * 70)
print()
print("Based on diagnostic results, is OCR working?")
print()

ocr_status = input("Did diagnostic say 'OCR works'? (yes/no): ").strip().lower()

if ocr_status != 'yes':
    print()
    print("❌ OCR is broken. This is the #1 priority to fix.")
    print()
    print("STOP HERE.")
    print()
    print("Action items:")
    print("1. If Tesseract not installed:")
    print("   - Download: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   - Install: tesseract-ocr-w64-setup-5.3.3.20231005.exe")
    print("   - Verify: tesseract --version")
    print()
    print("2. If Tesseract installed but Python can't find it:")
    print("   - Check PATH includes: C:\\Program Files\\Tesseract-OCR")
    print("   - Or configure path in core/ocr_finder.py")
    print()
    print("3. Test OCR manually:")
    print("   python tools/test_ocr_on_screenshot.py logs/<latest>/screenshots/step_8_before.png \"Blank workbook\"")
    print()
    print("4. Re-run this test runner after OCR is fixed")
    print()
    sys.exit(1)

print("✅ OCR is working")
print()

# Check accuracy
ocr_accurate = input("Did diagnostic say OCR position is correct? (yes/no): ").strip().lower()

if ocr_accurate != 'yes':
    print()
    print("⚠️  OCR works but position may be inaccurate")
    print()
    print("Test this manually:")
    print("1. Open coordinate validator tool:")
    print("   start tools/coordinate_validator.html")
    print()
    print("2. Upload: logs/<latest>/screenshots/step_8_before.png")
    print()
    print("3. Click where 'Blank workbook' actually is")
    print()
    print("4. Compare with OCR coordinates from diagnostic")
    print()
    print("If they match (within 20 pixels): Continue")
    print("If they don't match: OCR needs debugging")
    print()

    continue_test = input("Continue to next phase? (yes/no): ").strip().lower()
    if continue_test != 'yes':
        sys.exit(0)

print()

# ============================================================================
# PHASE 3: Loop Detection
# ============================================================================
print("PHASE 3: LOOP DETECTION")
print("-" * 70)
print()

loop_exists = input("Did diagnostic say 'Loop detection function exists'? (yes/no): ").strip().lower()
loop_triggered = input("Did diagnostic say 'Loop detection triggered'? (yes/no): ").strip().lower()

if loop_exists == 'yes' and loop_triggered != 'yes':
    print()
    print("❌ Loop detection exists but didn't trigger when it should have")
    print()
    print("This is a BUG in the loop detection logic.")
    print()
    print("Investigation needed:")
    print("1. Check what's being tracked in _action_history")
    print("2. Check what action_key format is used")
    print("3. Check if threshold (3 repeats) is correct")
    print()
    print("Add debug logging to see why detection failed:")
    print("  - Print _action_history before checking")
    print("  - Print action_key being checked")
    print("  - Print repeat_count")
    print()
    print("STOP HERE until loop detection is fixed.")
    sys.exit(1)
elif loop_exists != 'yes':
    print()
    print("❌ Loop detection code is missing")
    print()
    print("Need to implement loop detection in vision_agent_logged.py")
    print("STOP HERE.")
    sys.exit(1)

print("✅ Loop detection working")
print()

# ============================================================================
# PHASE 4: Reflection Accuracy
# ============================================================================
print("PHASE 4: REFLECTION ACCURACY")
print("-" * 70)
print()

reflection_exists = input("Did diagnostic say 'Reflection agent is integrated'? (yes/no): ").strip().lower()

if reflection_exists != 'yes':
    print()
    print("⚠️  Reflection agent not integrated or not running")
    print()
    print("This is lower priority - OCR + loop detection more important")
    print()
    print("Can continue without this, but accuracy will be reduced")
    print()

print()
print("Check reflection accuracy manually:")
print()
print("1. Look at latest log: logs/<latest>/execution_log.txt")
print()
print("2. Find a step where reflection said 'action_succeeded: True'")
print()
print("3. Open before/after screenshots for that step")
print()
print("4. Did anything actually change? Was the action successful?")
print()

reflection_accurate = input("Is reflection giving accurate results? (yes/no/unknown): ").strip().lower()

if reflection_accurate == 'no':
    print()
    print("❌ Reflection is reporting false positives")
    print()
    print("This needs investigation:")
    print("  - How does reflection determine success?")
    print("  - What LLM prompt does it use?")
    print("  - Does it actually compare screenshots properly?")
    print()
    print("This is MEDIUM priority (after OCR + loop detection)")
    print()

print()

# ============================================================================
# PHASE 5: Integration Test
# ============================================================================
print("PHASE 5: INTEGRATION TEST")
print("-" * 70)
print()
print("If you've reached this phase:")
print("  ✅ OCR is working")
print("  ✅ Loop detection is working")
print("  (Reflection may or may not be accurate)")
print()
print("Now test the full agent:")
print()
print("Run this command:")
print("  python test_educational_excel.py")
print()
print("Watch for:")
print("  1. Does OCR find 'Blank workbook' at correct position?")
print("  2. Does agent click at correct position?")
print("  3. Does 'Blank workbook' open on first try?")
print("  4. Does task complete without loops?")
print()
print("After test completes, check:")
print("  - logs/<latest>/execution_log.txt")
print("  - logs/<latest>/screenshots/")
print()

print("=" * 70)
print("END OF PHASED TESTING")
print("=" * 70)
print()
print("Share results at each phase before proceeding.")
print("Do NOT skip phases or claim things are fixed without verification.")
print()
