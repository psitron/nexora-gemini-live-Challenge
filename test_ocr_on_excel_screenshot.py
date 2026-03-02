"""
Test OCR on actual Excel screenshot to see if it can find "Blank workbook"
"""

from PIL import Image
from pathlib import Path

# Use a screenshot from the latest test
screenshot_path = Path("logs/20260302_184759/screenshots/step_4_before.png")

if not screenshot_path.exists():
    print(f"Screenshot not found: {screenshot_path}")
    print("Looking for latest screenshots...")
    logs_dir = Path("logs")
    latest_log = sorted(logs_dir.glob("*/screenshots/step_*_before.png"))[-1] if logs_dir.exists() else None
    if latest_log:
        screenshot_path = latest_log
        print(f"Using: {screenshot_path}")
    else:
        print("No screenshots found!")
        exit(1)

print(f"Testing OCR on: {screenshot_path}")
print("="*70)

# Load image
img = Image.open(screenshot_path)
print(f"Image size: {img.width}x{img.height}")
print()

# Test 1: Search for "Blank workbook" using OCR
print("TEST 1: Searching for 'Blank workbook'...")
print("-"*70)

from core.ocr_finder import find_all_text_in_image

matches = find_all_text_in_image(img, "Blank workbook")

if matches:
    print(f"✅ SUCCESS: Found {len(matches)} match(es)")
    for i, (x, y, w, h) in enumerate(matches):
        print(f"  Match {i+1}: x={x}, y={y}, w={w}, h={h}, center=({x+w//2}, {y+h//2})")
else:
    print(f"❌ FAILED: No matches found for 'Blank workbook'")

print()

# Test 2: Search for just "Blank"
print("TEST 2: Searching for 'Blank'...")
print("-"*70)

matches = find_all_text_in_image(img, "Blank")

if matches:
    print(f"✅ Found {len(matches)} match(es)")
    for i, (x, y, w, h) in enumerate(matches[:5]):  # Show first 5
        print(f"  Match {i+1}: x={x}, y={y}, w={w}, h={h}")
else:
    print(f"❌ No matches found for 'Blank'")

print()

# Test 3: Search for "workbook"
print("TEST 3: Searching for 'workbook'...")
print("-"*70)

matches = find_all_text_in_image(img, "workbook")

if matches:
    print(f"✅ Found {len(matches)} match(es)")
    for i, (x, y, w, h) in enumerate(matches[:5]):
        print(f"  Match {i+1}: x={x}, y={y}, w={w}, h={h}")
else:
    print(f"❌ No matches found for 'workbook'")

print()
print("="*70)
print("ANALYSIS:")
print("="*70)

# Show what AI thought the coordinates were
print("From execution log:")
print("  AI hint for 'Blank workbook': (382, 802)")
print("  (This is at 1920x1080 resolution)")
print()

if not find_all_text_in_image(img, "Blank workbook"):
    print("❌ PROBLEM: OCR cannot find 'Blank workbook' on this screenshot")
    print("   This means visual verification will NEVER run because OCR finds 0 matches")
    print("   Agent falls back to AI hint coordinates")
    print()
    print("   Possible reasons:")
    print("   1. Tesseract can't read the text (font/size issue)")
    print("   2. Text is not visible in screenshot")
    print("   3. OCR search is broken")
else:
    print("✅ OCR CAN find 'Blank workbook'")
    print("   But agent didn't use OCR - need to investigate why")
