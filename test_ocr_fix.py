"""Test the fixed OCR multi-word phrase search"""
from PIL import Image
from core.ocr_pytesseract_fallback import find_text_in_image

# Test on Excel screenshot
img = Image.open('logs/20260302_164226/screenshots/step_8_before.png')

# Test 1: Multi-word phrase "Blank workbook"
print("=" * 60)
print("TEST 1: Search for 'Blank workbook' (multi-word phrase)")
print("=" * 60)
matches = find_text_in_image(img, "Blank workbook")
if matches:
    print(f"✅ FOUND {len(matches)} match(es):")
    for i, (x, y, w, h) in enumerate(matches, 1):
        print(f"  {i}. Position: ({x}, {y}), Size: {w}x{h}, Center: ({x+w//2}, {y+h//2})")
else:
    print("❌ NOT FOUND")

print()

# Test 2: Single word "Excel"
print("=" * 60)
print("TEST 2: Search for 'Excel' (single word)")
print("=" * 60)
matches = find_text_in_image(img, "Excel")
if matches:
    print(f"✅ FOUND {len(matches)} match(es):")
    for i, (x, y, w, h) in enumerate(matches[:3], 1):
        print(f"  {i}. Position: ({x}, {y}), Size: {w}x{h}, Center: ({x+w//2}, {y+h//2})")
else:
    print("❌ NOT FOUND")

print()

# Test 3: Partial word "Blank" only
print("=" * 60)
print("TEST 3: Search for 'Blank' (first word only)")
print("=" * 60)
matches = find_text_in_image(img, "Blank")
if matches:
    print(f"✅ FOUND {len(matches)} match(es):")
    for i, (x, y, w, h) in enumerate(matches, 1):
        print(f"  {i}. Position: ({x}, {y}), Size: {w}x{h}, Center: ({x+w//2}, {y+h//2})")
else:
    print("❌ NOT FOUND")
