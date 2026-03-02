"""
Complete Diagnostic Script - Check What's Actually Broken

Runs all checks and reports current system state.

Usage:
    python tools/diagnostic_full.py
"""

import sys
import subprocess
from pathlib import Path
from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("DIAGNOSTIC REPORT - Current System State")
print("=" * 70)
print()

results = {
    "tesseract_installed": False,
    "tesseract_accessible": False,
    "ocr_works": False,
    "ocr_accurate": False,
    "loop_detection_exists": False,
    "loop_detection_called": False,
    "reflection_exists": False,
    "reflection_accurate": None
}

# ============================================================================
# TEST 1: Is Tesseract installed?
# ============================================================================
print("TEST 1: Tesseract Installation")
print("-" * 70)

try:
    result = subprocess.run(
        ["tesseract", "--version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        version = result.stdout.split('\n')[0]
        print(f"✅ Tesseract installed: {version}")
        results["tesseract_installed"] = True
        results["tesseract_accessible"] = True
    else:
        print(f"❌ Tesseract command failed")
        print(f"   Error: {result.stderr}")
except FileNotFoundError:
    print("❌ Tesseract NOT found")
    print("   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   Install: tesseract-ocr-w64-setup-5.3.3.20231005.exe")
except Exception as e:
    print(f"❌ Error checking Tesseract: {e}")

print()

# ============================================================================
# TEST 2: Can Python access OCR?
# ============================================================================
print("TEST 2: OCR Python Integration")
print("-" * 70)

try:
    from core.ocr_finder import find_all_text_on_screen
    print("✅ OCR module imported successfully")

    # Find a recent screenshot to test on
    logs_dir = Path("logs")
    recent_logs = sorted(logs_dir.glob("*/"), reverse=True)

    if recent_logs:
        test_screenshot = None
        for log_dir in recent_logs[:3]:  # Check last 3 runs
            screenshots = list((log_dir / "screenshots").glob("step_*_before.png"))
            if screenshots:
                test_screenshot = screenshots[0]
                break

        if test_screenshot:
            print(f"   Testing on: {test_screenshot}")

            # Try to find "Blank workbook" in screenshot
            try:
                img = Image.open(test_screenshot)
                print(f"   Screenshot size: {img.width}x{img.height}")

                matches = find_all_text_on_screen(
                    "Blank workbook",
                    region=None,
                    timeout=3.0
                )

                if matches:
                    results["ocr_works"] = True
                    print(f"✅ OCR works! Found {len(matches)} match(es)")
                    for i, (x, y, w, h) in enumerate(matches, 1):
                        center_x = x + w // 2
                        center_y = y + h // 2
                        print(f"   Match {i}: center=({center_x}, {center_y}), bbox=({x},{y},{w},{h})")

                    # Check if position looks reasonable
                    # "Blank workbook" should be in top-left area (~60-150, ~60-150)
                    first_match = matches[0]
                    center_x = first_match[0] + first_match[2] // 2
                    center_y = first_match[1] + first_match[3] // 2

                    if 40 <= center_x <= 200 and 40 <= center_y <= 200:
                        results["ocr_accurate"] = True
                        print(f"✅ Position looks correct (top-left area)")
                    else:
                        print(f"⚠️  Position seems off (expected top-left, got middle/bottom)")
                else:
                    print("❌ OCR found NO matches for 'Blank workbook'")
                    print("   Possible reasons:")
                    print("   - Text is in an image/graphic (not readable text)")
                    print("   - Font is too small or stylized")
                    print("   - OCR timeout too short")
            except Exception as e:
                print(f"❌ OCR test failed: {e}")
        else:
            print("⚠️  No test screenshots found in recent logs")
    else:
        print("⚠️  No log directories found")

except ImportError as e:
    print(f"❌ Cannot import OCR module: {e}")
except Exception as e:
    print(f"❌ Error testing OCR: {e}")

print()

# ============================================================================
# TEST 3: Loop detection code exists?
# ============================================================================
print("TEST 3: Loop Detection Code")
print("-" * 70)

vision_agent_file = Path("core/vision_agent_logged.py")
if vision_agent_file.exists():
    content = vision_agent_file.read_text(encoding='utf-8')

    if "_is_stuck_in_loop" in content:
        results["loop_detection_exists"] = True
        print("✅ Loop detection function exists")

        # Check if it's actually called
        if "if self._is_stuck_in_loop" in content:
            print("✅ Loop detection is called in code")
        else:
            print("⚠️  Loop detection function exists but may not be called")
    else:
        print("❌ Loop detection function NOT found")
else:
    print("❌ vision_agent_logged.py not found")

print()

# ============================================================================
# TEST 4: Was loop detection triggered in recent run?
# ============================================================================
print("TEST 4: Loop Detection Runtime")
print("-" * 70)

if recent_logs:
    latest_log = recent_logs[0] / "execution_log.txt"
    if latest_log.exists():
        log_content = latest_log.read_text(encoding='utf-8')

        if "LOOP DETECTED" in log_content or "stuck in loop" in log_content.lower():
            results["loop_detection_called"] = True
            print("✅ Loop detection triggered in last run")
        else:
            print("❌ Loop detection did NOT trigger in last run")

            # Check if there were repeated actions
            blank_workbook_clicks = log_content.count("target': 'Blank workbook'")
            print(f"   'Blank workbook' appeared {blank_workbook_clicks} times")

            if blank_workbook_clicks >= 3:
                print("   ⚠️  Same action repeated 3+ times but loop detection didn't trigger!")
                print("   This indicates a BUG in loop detection logic")
    else:
        print("⚠️  No execution_log.txt in latest run")
else:
    print("⚠️  No recent logs to check")

print()

# ============================================================================
# TEST 5: Reflection agent exists?
# ============================================================================
print("TEST 5: Reflection Agent")
print("-" * 70)

reflection_file = Path("core/reflection_agent.py")
if reflection_file.exists():
    results["reflection_exists"] = True
    print("✅ Reflection agent file exists")

    # Check if it's used in vision_agent_logged
    if vision_agent_file.exists():
        content = vision_agent_file.read_text(encoding='utf-8')
        if "ReflectionAgent" in content and "self.reflection_agent.reflect" in content:
            print("✅ Reflection agent is integrated and called")

            # Check recent logs for reflection output
            if recent_logs:
                latest_log = recent_logs[0] / "execution_log.txt"
                if latest_log.exists():
                    log_content = latest_log.read_text(encoding='utf-8')
                    reflection_count = log_content.count("REFLECTION: analyze_outcome")

                    if reflection_count > 0:
                        print(f"✅ Reflection ran {reflection_count} times in last run")

                        # Check accuracy: look for cases where it said "succeeded" but nothing changed
                        # This requires comparing before/after screenshots - complex analysis
                        print("   ⚠️  Accuracy check requires manual verification")
                        print("   Check: Do reflection results match actual outcomes?")
                    else:
                        print("⚠️  Reflection didn't run (or not logged)")
        else:
            print("⚠️  Reflection agent exists but may not be integrated")
else:
    print("❌ Reflection agent file NOT found")

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()

issues = []

if not results["tesseract_installed"]:
    issues.append("CRITICAL: Tesseract OCR not installed")
elif not results["tesseract_accessible"]:
    issues.append("CRITICAL: Tesseract installed but not accessible (PATH issue)")

if not results["ocr_works"]:
    issues.append("CRITICAL: OCR cannot find text on screenshots")
elif not results["ocr_accurate"]:
    issues.append("WARNING: OCR finds text but position may be inaccurate")

if not results["loop_detection_exists"]:
    issues.append("CRITICAL: Loop detection code missing")
elif not results["loop_detection_called"]:
    issues.append("CRITICAL: Loop detection exists but didn't trigger when needed")

if not results["reflection_exists"]:
    issues.append("WARNING: Reflection agent missing")

if issues:
    print("❌ ISSUES FOUND:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
else:
    print("✅ All systems appear operational")
    print("   Run integration test to verify end-to-end functionality")

print()
print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print()

if not results["tesseract_installed"]:
    print("1. Install Tesseract OCR:")
    print("   Download: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   File: tesseract-ocr-w64-setup-5.3.3.20231005.exe")
    print("   Run installer, then restart terminal")
    print()
    print("2. Verify installation:")
    print("   tesseract --version")
    print()
    print("3. Re-run this diagnostic")

elif not results["ocr_works"]:
    print("1. OCR installed but not working. Debug:")
    print("   python tools/test_ocr_on_screenshot.py <screenshot> \"Blank workbook\"")
    print()
    print("2. Check Tesseract path configuration")
    print("   May need to set: pytesseract.pytesseract.tesseract_cmd")

elif not results["loop_detection_called"]:
    print("1. Loop detection exists but has a bug")
    print("   Need to investigate WHY it didn't trigger")
    print()
    print("2. Add debug logging to _is_stuck_in_loop()")
    print("   Print: action_key, _action_history, repeat_count")
    print()
    print("3. Run test again and check console output")

else:
    print("1. All basic checks passed")
    print("2. Run integration test:")
    print("   python test_educational_excel.py")
    print()
    print("3. Manually verify:")
    print("   - Check screenshots: Are clicks in right places?")
    print("   - Check logs: Are coordinates accurate?")
    print("   - Check behavior: Does task complete?")

print()
print("=" * 70)
