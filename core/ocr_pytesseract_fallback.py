"""
Direct pytesseract OCR fallback (avoids screen_ocr DXCamera COM errors)

This module provides OCR functionality by calling pytesseract directly on
PIL images, avoiding the screen_ocr library's DXCamera backend which fails
with COM error -2147467259 in certain runtime contexts.

Usage:
    from core.ocr_pytesseract_fallback import find_text_in_image

    # Pass the PIL Image directly (agent already captures these)
    matches = find_text_in_image(pil_image, "Blank workbook")
"""

from __future__ import annotations

import math
import subprocess
from typing import List, Tuple, Optional
from PIL import Image

try:
    import pytesseract
    HAS_PYTESSERACT = True

    # Configure Tesseract path
    import os
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    HAS_PYTESSERACT = False


def find_text_in_image(
    image: Image.Image,
    search_text: str,
    hint_pos: Tuple[int, int] | None = None,
    case_sensitive: bool = False
) -> List[Tuple[int, int, int, int]]:
    """
    Find all occurrences of text in a PIL Image using pytesseract.

    Args:
        image: PIL Image to search in
        search_text: Text to find (partial match OK)
        hint_pos: (x, y) approximate position hint for sorting results
        case_sensitive: Whether to match case exactly

    Returns:
        List of (x, y, w, h) bounding boxes, sorted by distance from hint
    """
    if not HAS_PYTESSERACT:
        print(f"  [OCR] pytesseract not available")
        return []

    try:
        # Get OCR data with bounding boxes
        # pytesseract.image_to_data returns detailed word-level data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Build list of words with their positions
        n_boxes = len(data['text'])
        matches = []

        # Prepare search text
        search_lower = search_text.lower() if not case_sensitive else search_text
        search_words = search_lower.split()
        first_word = search_words[0]

        # Strategy: Find first word, then check if subsequent words form the phrase
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text:
                continue

            text_compare = text if case_sensitive else text.lower()
            conf = data['conf'][i]

            # Skip low confidence
            if conf < 30:
                continue

            # Check if this is the first word of our search phrase
            if first_word in text_compare:
                # Found first word - now check if it's a multi-word phrase
                if len(search_words) == 1:
                    # Single word search - match found
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]

                    if w < 5 or h < 5:
                        continue

                    matches.append((x, y, w, h))
                else:
                    # Multi-word phrase - check consecutive words
                    phrase_match = True
                    phrase_boxes = [(data['left'][i], data['top'][i], data['width'][i], data['height'][i])]

                    for j in range(1, len(search_words)):
                        if i + j >= n_boxes:
                            phrase_match = False
                            break

                        next_word = data['text'][i + j].strip()
                        if not next_word:
                            phrase_match = False
                            break

                        next_compare = next_word if case_sensitive else next_word.lower()
                        if search_words[j] not in next_compare:
                            phrase_match = False
                            break

                        # Words must be on same line (y coordinate similar)
                        if abs(data['top'][i] - data['top'][i + j]) > 10:
                            phrase_match = False
                            break

                        phrase_boxes.append((data['left'][i + j], data['top'][i + j],
                                           data['width'][i + j], data['height'][i + j]))

                    if phrase_match:
                        # Combine all boxes into one bounding box
                        xs = [b[0] for b in phrase_boxes]
                        ys = [b[1] for b in phrase_boxes]
                        rights = [b[0] + b[2] for b in phrase_boxes]
                        bottoms = [b[1] + b[3] for b in phrase_boxes]

                        x = min(xs)
                        y = min(ys)
                        w = max(rights) - x
                        h = max(bottoms) - y

                        if w < 5 or h < 5:
                            continue

                        matches.append((x, y, w, h))

        # Sort by distance from hint if provided
        if hint_pos and matches:
            hint_x, hint_y = hint_pos
            matches.sort(key=lambda b: math.hypot(
                (b[0] + b[2]/2) - hint_x,
                (b[1] + b[3]/2) - hint_y
            ))

        if matches:
            print(f"  [OCR-Pytesseract] Found {len(matches)} match(es) for '{search_text}'")
        else:
            print(f"  [OCR-Pytesseract] No matches found for '{search_text}'")

        return matches

    except Exception as e:
        print(f"  [OCR-Pytesseract] Error: {type(e).__name__}: {str(e)[:100]}")
        return []


def test_pytesseract_available() -> bool:
    """Test if pytesseract is available and working"""
    if not HAS_PYTESSERACT:
        return False

    try:
        # Try to get version
        version = pytesseract.get_tesseract_version()
        print(f"  [OCR-Pytesseract] Tesseract version: {version}")
        return True
    except Exception as e:
        print(f"  [OCR-Pytesseract] Not available: {e}")
        return False
