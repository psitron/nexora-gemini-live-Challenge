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
        print(f"  [OCR not available: screen-ocr not installed]")
        return []

    try:
        reader = screen_ocr.Reader.create_fast_reader()
    except Exception as e:
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
                    all_boxes.append((left, top, right - left, bottom - top))
                
                # Sort by distance from hint if provided
                if hint_pos:
                    hint_x, hint_y = hint_pos
                    all_boxes.sort(key=lambda b: math.hypot(
                        (b[0] + b[2]/2) - hint_x,
                        (b[1] + b[3]/2) - hint_y
                    ))
                
                # Log success
                print(f"  [OCR] Found {len(all_boxes)} match(es) for '{text}' (attempt {attempts})")
                return all_boxes

            time.sleep(0.5)
        except Exception as e:
            print(f"  [OCR attempt {attempts}/{max_attempts} failed: {type(e).__name__}: {str(e)[:100]}]")
            time.sleep(0.5)

    print(f"  [OCR] No matches found for '{text}' after {attempts} attempts")
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
