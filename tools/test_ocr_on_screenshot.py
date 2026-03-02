"""
Test OCR on a specific screenshot to see if it can find text.

Usage:
    python tools/test_ocr_on_screenshot.py <screenshot_path> <search_text>

Example:
    python tools/test_ocr_on_screenshot.py logs/20260302_145003/screenshots/step_8_before.png "Blank workbook"
"""

import sys
from pathlib import Path
from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ocr_finder import find_all_text_on_screen


def test_ocr(screenshot_path: str, search_text: str):
    """Test if OCR can find text in a screenshot."""

    print(f"Testing OCR on: {screenshot_path}")
    print(f"Searching for: '{search_text}'")
    print(f"{'-' * 60}")

    # Load image
    img = Image.open(screenshot_path)
    print(f"Image size: {img.width} x {img.height}")

    # Test OCR
    print(f"\nSearching for '{search_text}'...")
    matches = find_all_text_on_screen(search_text, region=None, timeout=5.0)

    if not matches:
        print(f"❌ OCR did NOT find '{search_text}'")
        print(f"\nThis means the agent will fall back to AI's hint coordinates,")
        print(f"which are often inaccurate!")
        return False

    print(f"✅ OCR found {len(matches)} match(es):")
    for i, (x, y, w, h) in enumerate(matches, 1):
        center_x = x + w // 2
        center_y = y + h // 2
        print(f"  Match {i}: bbox=({x}, {y}, {w}, {h})")
        print(f"           center=({center_x}, {center_y})")
        print(f"           This is where the agent SHOULD click")

    return True


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nExample:")
        print("  python tools/test_ocr_on_screenshot.py logs/20260302_145003/screenshots/step_8_before.png \"Blank workbook\"")
        sys.exit(1)

    screenshot_path = sys.argv[1]
    search_text = sys.argv[2]

    if not Path(screenshot_path).exists():
        print(f"Error: Screenshot not found: {screenshot_path}")
        sys.exit(1)

    success = test_ocr(screenshot_path, search_text)

    print(f"\n{'-' * 60}")
    if success:
        print("✅ OCR is working - coordinates should be accurate")
    else:
        print("❌ OCR failed - this is why clicks are in wrong places!")
        print("\nPossible reasons:")
        print("  1. Text is too small for OCR")
        print("  2. Text has unusual font/styling")
        print("  3. OCR timeout too short")
        print("  4. Text is part of an image, not actual text")


if __name__ == "__main__":
    main()
