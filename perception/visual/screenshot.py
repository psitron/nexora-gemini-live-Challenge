from __future__ import annotations

"""
Hybrid AI Agent – screenshot capture.

Uses mss to capture monitors as PIL Images.
Supports capturing specific monitors by index for multi-monitor setups.
"""

from typing import Optional, Tuple

import mss
from PIL import Image
import io


def capture_primary_monitor() -> Image.Image:
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.rgb)
        return img


def capture_monitor_region(rect: Tuple[int, int, int, int]) -> Image.Image:
    """
    Capture a specific screen region.
    
    Args:
        rect: (left, top, right, bottom) in virtual screen coordinates
    
    Returns:
        PIL Image of that region
    """
    left, top, right, bottom = rect
    with mss.mss() as sct:
        region = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.rgb)
        return img


def capture_selected_monitor() -> Image.Image:
    """Capture the PRIMARY_MONITOR (set in .env)."""
    from core.monitor_utils import get_selected_monitor
    
    rect = get_selected_monitor()
    if rect:
        return capture_monitor_region(rect)
    return capture_primary_monitor()

