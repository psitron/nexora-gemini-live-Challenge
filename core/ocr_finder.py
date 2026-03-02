"""
OCR-based text finder for Windows (uses native WinRT OCR for speed).
Finds text on screen and returns bounding boxes.

Supports hint-based disambiguation: when the same text appears in
multiple places on screen, prefers the match closest to a given
hint position (from the AI's approximate coordinates).

NEW: Also supports finding ALL matches for visual verification.
"""

from __future__ import annotations

import math
from typing import Tuple, Optional, List
import time

try:
    import screen_ocr
    HAS_SCREEN_OCR = True

    # Configure Tesseract path for screen_ocr
    import os
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        os.environ['TESSERACT_CMD'] = tesseract_path
except ImportError:
    HAS_SCREEN_OCR = False


def find_text_on_screen(
    text: str,
    region: Tuple[int, int, int, int] | None = None,
    timeout: float = 3.0,
    hint_pos: Tuple[int, int] | None = None,
) -> Tuple[int, int, int, int] | None:
    """
    Find text on screen using Windows OCR and return its bounding box.

    Args:
        text: Text to search for (case-insensitive, partial match OK)
        region: Optional (x, y, w, h) region to search in
        timeout: Max seconds to search
        hint_pos: (x, y) approximate position hint from AI vision.
                  When multiple matches exist, picks the closest one.

    Returns:
        (x, y, w, h) bounding box if found, None otherwise
    """
    matches = find_all_text_on_screen(text, region, timeout, hint_pos)
    return matches[0] if matches else None


def find_text_in_image(
    image: "Image.Image",
    text: str,
    hint_pos: Tuple[int, int] | None = None,
    region: Tuple[int, int, int, int] | None = None,
) -> Tuple[int, int, int, int] | None:
    """
    Find text in a PIL Image using OCR (no screen re-capture).

    Args:
        image: PIL Image to search in
        text: Text to search for (case-insensitive, partial match OK)
        hint_pos: (x, y) approximate position hint from AI vision
        region: Optional (x, y, w, h) to crop the image before searching

    Returns:
        (x, y, w, h) bounding box if found, None otherwise
    """
    matches = find_all_text_in_image(image, text, hint_pos, region)
    return matches[0] if matches else None


def find_all_text_in_image(
    image: "Image.Image",
    text: str,
    hint_pos: Tuple[int, int] | None = None,
    region: Tuple[int, int, int, int] | None = None,
) -> List[Tuple[int, int, int, int]]:
    """
    Find ALL occurrences of text in a PIL Image using OCR (no screen re-capture).

    This is the KEY FIX: Uses the same image that Gemini analyzed, avoiding the
    timing gap where the screen might change between analysis and OCR.

    Args:
        image: PIL Image to search in (same one Gemini analyzed)
        text: Text to search for (case-insensitive, partial match OK)
        hint_pos: (x, y) approximate position hint for sorting results
        region: Optional (x, y, w, h) to crop the image before searching

    Returns:
        List of (x, y, w, h) bounding boxes, sorted by distance from hint
    """
    from core.ocr_pytesseract_fallback import find_text_in_image as pytesseract_search

    # Crop to region if specified
    search_image = image
    offset_x, offset_y = 0, 0

    if region:
        x, y, w, h = region
        search_image = image.crop((x, y, x + w, y + h))
        offset_x, offset_y = x, y

    # Adjust hint_pos for cropped region
    adjusted_hint = None
    if hint_pos:
        adjusted_hint = (hint_pos[0] - offset_x, hint_pos[1] - offset_y)

    # Use pytesseract on the provided image
    matches = pytesseract_search(search_image, text, hint_pos=adjusted_hint)

    # Adjust coordinates back to full image space
    if matches and region:
        matches = [(x + offset_x, y + offset_y, w, h) for (x, y, w, h) in matches]

    return matches


def find_all_text_on_screen(
    text: str,
    region: Tuple[int, int, int, int] | None = None,
    timeout: float = 3.0,
    hint_pos: Tuple[int, int] | None = None,
) -> List[Tuple[int, int, int, int]]:
    """
    Find ALL occurrences of text on screen using Windows OCR.

    Args:
        text: Text to search for (case-insensitive, partial match OK)
        region: Optional (x, y, w, h) region to search in
        timeout: Max seconds to search
        hint_pos: (x, y) approximate position hint for sorting results

    Returns:
        List of (x, y, w, h) bounding boxes, sorted by distance from hint
    """
    if not HAS_SCREEN_OCR:
        print(f"  [OCR] screen-ocr not available, trying pytesseract fallback...")
        return _pytesseract_fallback(text, region, hint_pos)

    # Try screen_ocr first (fast path)
    try:
        reader = screen_ocr.Reader.create_fast_reader()
    except Exception as e:
        # COM error -2147467259 or DXCamera failure - fall back to pytesseract
        error_msg = str(e)
        if "-2147467259" in error_msg or "DXCamera" in error_msg or "is_capturing" in error_msg:
            print(f"  [OCR] screen-ocr failed (COM/DXCamera error), using pytesseract fallback...")
            return _pytesseract_fallback(text, region, hint_pos)
        else:
            print(f"  [OCR reader creation failed: {e}]")
            return []

    start_time = time.time()
    attempts = 0
    max_attempts = 3

    while time.time() - start_time < timeout and attempts < max_attempts:
        attempts += 1
        try:
            if region:
                x, y, w, h = region
                bounding_box = (x, y, x + w, y + h)
                screen_contents = reader.read_screen(bounding_box=bounding_box)
            else:
                screen_contents = reader.read_screen()

            matches = screen_contents.find_matching_words(text)
            if matches:
                # Convert all matches to bounding boxes
                all_boxes = []
                for word_locations in matches:
                    left = min(loc.left for loc in word_locations)
                    top = min(loc.top for loc in word_locations)
                    right = max(loc.right for loc in word_locations)
                    bottom = max(loc.bottom for loc in word_locations)

                    # Validate coordinates (fix DPI/multi-monitor issues)
                    if right <= left or bottom <= top:
                        print(f"  [OCR] Skipping invalid box: left={left}, right={right}, top={top}, bottom={bottom}")
                        continue

                    width = right - left
                    height = bottom - top

                    # Skip boxes that are too small (likely OCR errors)
                    if width < 5 or height < 5:
                        continue

                    all_boxes.append((left, top, width, height))

                # Sort by distance from hint if provided
                if hint_pos:
                    hint_x, hint_y = hint_pos
                    all_boxes.sort(key=lambda b: math.hypot(
                        (b[0] + b[2]/2) - hint_x,
                        (b[1] + b[3]/2) - hint_y
                    ))

                # Log success
                print(f"  [OCR-screen_ocr] Found {len(all_boxes)} match(es) for '{text}' (attempt {attempts})")
                return all_boxes

            time.sleep(0.5)
        except Exception as e:
            error_msg = str(e)
            # If screen_ocr fails mid-execution with COM/DXCamera errors, fall back
            if "-2147467259" in error_msg or "DXCamera" in error_msg or "is_capturing" in error_msg:
                print(f"  [OCR] screen-ocr runtime error, switching to pytesseract fallback...")
                return _pytesseract_fallback(text, region, hint_pos)

            print(f"  [OCR attempt {attempts}/{max_attempts} failed: {type(e).__name__}: {str(e)[:100]}]")
            time.sleep(0.5)

    print(f"  [OCR] No matches found for '{text}' after {attempts} attempts")
    return []


def _pytesseract_fallback(
    text: str,
    region: Tuple[int, int, int, int] | None = None,
    hint_pos: Tuple[int, int] | None = None,
) -> List[Tuple[int, int, int, int]]:
    """
    Fallback OCR using pytesseract directly (avoids DXCamera COM errors).
    Captures screenshot using mss library (same as agent uses).
    """
    try:
        from core.ocr_pytesseract_fallback import find_text_in_image
        import mss
        from PIL import Image

        # Capture screenshot using mss (same library agent uses)
        with mss.mss() as sct:
            if region:
                x, y, w, h = region
                monitor = {"left": x, "top": y, "width": w, "height": h}
            else:
                # Capture primary monitor
                monitor = sct.monitors[1]

            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # Adjust hint_pos to be relative to captured region
            adjusted_hint = None
            if hint_pos and region:
                adjusted_hint = (hint_pos[0] - region[0], hint_pos[1] - region[1])
            elif hint_pos:
                adjusted_hint = hint_pos

            # Use pytesseract on the captured image
            matches = find_text_in_image(img, text, hint_pos=adjusted_hint)

            # Adjust matches back to screen coordinates if we captured a region
            if region and matches:
                matches = [(x + region[0], y + region[1], w, h) for (x, y, w, h) in matches]

            return matches

    except Exception as e:
        print(f"  [OCR-Pytesseract] Fallback failed: {type(e).__name__}: {str(e)[:100]}")
        return []


def _select_best_match(matches: list, hint_pos: Tuple[int, int] | None) -> list:
    """
    From multiple OCR matches, pick the best one.
    If hint_pos is given, prefer the match closest to it.
    Otherwise return the first match.
    """
    if len(matches) == 1 or hint_pos is None:
        return matches[0]

    hint_x, hint_y = hint_pos
    best_match = matches[0]
    best_dist = float("inf")

    for match in matches:
        cx = sum((loc.left + loc.right) / 2 for loc in match) / len(match)
        cy = sum((loc.top + loc.bottom) / 2 for loc in match) / len(match)
        dist = math.hypot(cx - hint_x, cy - hint_y)
        if dist < best_dist:
            best_dist = dist
            best_match = match

    return best_match
