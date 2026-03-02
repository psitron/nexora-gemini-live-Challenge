"""
Set-of-Mark element detection (Agent S3 approach)

Instead of asking vision model for coordinates (which it's bad at),
we overlay numbered markers on the screenshot, then ask "which number is X?"
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional
import random


def create_set_of_mark_image(
    screenshot: Image.Image,
    elements: List[Tuple[int, int, int, int]] = None
) -> Tuple[Image.Image, List[Tuple[int, int, int, int]]]:
    """
    Create a Set-of-Mark annotated screenshot.

    If elements are provided, numbers them.
    If not provided, creates a grid overlay for the vision model to reference.

    Args:
        screenshot: Original PIL Image
        elements: Optional list of (x, y, w, h) bounding boxes to number

    Returns:
        (annotated_image, element_list) - Image with numbers, list of elements
    """
    # Create a copy to draw on
    annotated = screenshot.copy()
    draw = ImageDraw.Draw(annotated, 'RGBA')

    # Try to load a font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 36)
        small_font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    if elements:
        # Number provided elements
        for i, (x, y, w, h) in enumerate(elements):
            # Draw semi-transparent overlay box
            draw.rectangle(
                [x, y, x + w, y + h],
                outline=(255, 0, 0, 255),
                width=3
            )

            # Draw number label in top-left corner
            label = str(i)
            # Background for number
            draw.rectangle(
                [x, y - 30, x + 40, y],
                fill=(255, 0, 0, 200)
            )
            draw.text(
                (x + 5, y - 28),
                label,
                fill=(255, 255, 255, 255),
                font=font
            )
    else:
        # Create grid overlay for general reference
        # This helps the vision model describe locations
        img_w, img_h = screenshot.size
        grid_size = 200  # 200px grid

        # Draw vertical lines
        for x in range(0, img_w, grid_size):
            draw.line([(x, 0), (x, img_h)], fill=(255, 0, 0, 100), width=2)
            # Label every other line
            if x % (grid_size * 2) == 0:
                draw.text((x + 5, 5), f"x={x}", fill=(255, 0, 0, 200), font=small_font)

        # Draw horizontal lines
        for y in range(0, img_h, grid_size):
            draw.line([(0, y), (img_w, y)], fill=(255, 0, 0, 100), width=2)
            if y % (grid_size * 2) == 0:
                draw.text((5, y + 5), f"y={y}", fill=(255, 0, 0, 200), font=small_font)

    return annotated, elements if elements else []


def detect_clickable_regions(screenshot: Image.Image) -> List[Tuple[int, int, int, int]]:
    """
    Heuristically detect likely clickable regions.

    This is a simple implementation that divides the screen into a grid.
    A better implementation would use actual UI detection (OmniParser, etc.)

    Returns:
        List of (x, y, w, h) bounding boxes for likely clickable areas
    """
    img_w, img_h = screenshot.size

    # Create a grid of potential clickable areas
    # This is very basic - real implementation would detect actual UI elements
    regions = []

    # Divide screen into 6x4 grid (24 regions)
    cols, rows = 6, 4
    region_w = img_w // cols
    region_h = img_h // rows

    for row in range(rows):
        for col in range(cols):
            x = col * region_w + region_w // 4
            y = row * region_h + region_h // 4
            w = region_w // 2
            h = region_h // 2
            regions.append((x, y, w, h))

    return regions


def create_smart_grid_overlay(
    screenshot: Image.Image,
    focus_area: Tuple[int, int] = None
) -> Tuple[Image.Image, List[Tuple[int, int, int, int]]]:
    """
    Create a smart grid that focuses on the area of interest.

    Args:
        screenshot: Original image
        focus_area: (x, y) approximate location to focus on

    Returns:
        (annotated_image, regions) - Image with numbered regions
    """
    img_w, img_h = screenshot.size

    if focus_area:
        # Create finer grid around focus area
        fx, fy = focus_area

        # Define focus region (400x400 around point)
        focus_size = 400
        fx_start = max(0, fx - focus_size // 2)
        fy_start = max(0, fy - focus_size // 2)
        fx_end = min(img_w, fx_start + focus_size)
        fy_end = min(img_h, fy_start + focus_size)

        # Create 3x3 grid in focus area
        regions = []
        for row in range(3):
            for col in range(3):
                x = fx_start + (fx_end - fx_start) * col // 3
                y = fy_start + (fy_end - fy_start) * row // 3
                w = (fx_end - fx_start) // 3
                h = (fy_end - fy_start) // 3
                regions.append((x, y, w, h))

        # Add coarse grid for rest of screen
        coarse_regions = []
        # Top area
        if fy_start > 100:
            coarse_regions.append((img_w // 2 - 100, fy_start // 2 - 50, 200, 100))
        # Bottom area
        if fy_end < img_h - 100:
            coarse_regions.append((img_w // 2 - 100, (fy_end + img_h) // 2 - 50, 200, 100))
        # Left area
        if fx_start > 100:
            coarse_regions.append((fx_start // 2 - 50, img_h // 2 - 100, 100, 200))
        # Right area
        if fx_end < img_w - 100:
            coarse_regions.append(((fx_end + img_w) // 2 - 50, img_h // 2 - 100, 100, 200))

        regions.extend(coarse_regions)
    else:
        # No focus - use general grid
        regions = detect_clickable_regions(screenshot)

    # Create annotated image
    annotated, _ = create_set_of_mark_image(screenshot, regions)

    return annotated, regions
