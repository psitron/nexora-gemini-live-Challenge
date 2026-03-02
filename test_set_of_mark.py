"""
Test Set-of-Mark approach for element detection
"""

from PIL import Image
from pathlib import Path
from core.vision_agent import VisionAgent

print("="*70)
print("TESTING: Set-of-Mark Element Detection")
print("="*70)
print()

# Use Excel screenshot
screenshot_path = Path("logs/20260302_184759/screenshots/step_6_before.png")

if not screenshot_path.exists():
    print(f"ERROR: Screenshot not found: {screenshot_path}")
    exit(1)

print(f"Loading: {screenshot_path}")
img = Image.open(screenshot_path)
print(f"Image size: {img.width}x{img.height}")
print()

# Create agent
agent = VisionAgent()
agent._current_screenshot = img

print("TEST: Find 'Blank workbook' button with Set-of-Mark")
print("-"*70)

bbox = agent._find_element_with_vision(
    element_description="Blank workbook",
    hint_pos=(382, 802)  # AI's hint
)

if bbox:
    x, y, w, h = bbox
    cx, cy = x + w // 2, y + h // 2
    print()
    print(f"SUCCESS: Found element!")
    print(f"  Bounding box: ({x}, {y}, {w}, {h})")
    print(f"  Click center: ({cx}, {cy})")
    print()
    print(f"Expected: Around (382, 802)")
    print(f"Difference: ({abs(cx - 382)}, {abs(cy - 802)}) pixels")
else:
    print(f"FAILED: Could not find element")

print()
print("="*70)
print("Check debug_sessions/ for set_of_mark_*.png to see numbered overlay")
print("="*70)
