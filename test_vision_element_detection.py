"""
Test vision-based element detection on Excel screenshot
"""

from PIL import Image
from pathlib import Path
from core.vision_agent import VisionAgent

print("="*70)
print("TESTING: Vision-Based Element Detection")
print("="*70)
print()

# Use Excel screenshot with "Blank workbook" button
screenshot_path = Path("logs/20260302_184759/screenshots/step_6_before.png")

if not screenshot_path.exists():
    print(f"ERROR: Screenshot not found: {screenshot_path}")
    exit(1)

print(f"Loading screenshot: {screenshot_path}")
img = Image.open(screenshot_path)
print(f"Image size: {img.width}x{img.height}")
print()

# Create agent and set current screenshot
agent = VisionAgent()
agent._current_screenshot = img

print("TEST 1: Find 'Blank workbook' button")
print("-"*70)

bbox = agent._find_element_with_vision(
    element_description="Blank workbook button",
    hint_pos=(382, 802)  # AI's approximate hint
)

if bbox:
    x, y, w, h = bbox
    cx, cy = x + w // 2, y + h // 2
    print(f"SUCCESS: Found element!")
    print(f"  Bounding box: x={x}, y={y}, w={w}, h={h}")
    print(f"  Click center: ({cx}, {cy})")
    print()

    # Validate it's reasonable
    if 0 <= x < 1920 and 0 <= y < 1080:
        print(f"  Coordinates look valid")
    else:
        print(f"  WARNING: Coordinates seem off")
else:
    print(f"FAILED: Could not find element")

print()
print("TEST 2: Find 'Excel' text (should also work)")
print("-"*70)

bbox = agent._find_element_with_vision(
    element_description="Excel application icon or text",
    hint_pos=None
)

if bbox:
    x, y, w, h = bbox
    print(f"SUCCESS: Found Excel")
    print(f"  Bounding box: x={x}, y={y}, w={w}, h={h}")
else:
    print(f"FAILED: Could not find Excel")

print()
print("="*70)
print("CONCLUSION")
print("="*70)

if bbox:
    print("Vision-based element detection is WORKING!")
    print("This should replace broken OCR approach.")
    print()
    print("Next step: Run full test with:")
    print("  echo '2' | python test_educational_excel.py")
else:
    print("Vision detection not working. Check:")
    print("  1. Vision model API key configured?")
    print("  2. Network connectivity?")
    print("  3. Check error messages above")
