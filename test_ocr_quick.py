from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

img = Image.open('logs/20260302_164226/screenshots/step_8_before.png')
data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

# Search for "Blank workbook" (exact phrase)
matches_exact = []
search_exact = 'Blank workbook'.lower()
for i in range(len(data['text'])):
    text = data['text'][i].strip().lower()
    if search_exact in text:
        matches_exact.append((data['text'][i], data['left'][i], data['top'][i]))

print(f'Exact phrase "Blank workbook": {len(matches_exact)} matches')
print(matches_exact)

# Search for just "Blank"
matches_blank = []
for i in range(len(data['text'])):
    text = data['text'][i].strip().lower()
    if 'blank' in text:
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        matches_blank.append((data['text'][i], x, y, w, h, f"center=({x+w//2},{y+h//2})"))

print(f'\nPartial match "blank": {len(matches_blank)} matches')
for m in matches_blank:
    print(f"  {m}")

# All words found
all_words = [w for w in data['text'] if w.strip()]
print(f"\nTotal words found: {len(all_words)}")
print(f"Sample: {all_words[:20]}")
