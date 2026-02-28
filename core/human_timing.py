from __future__ import annotations

"""
Hybrid AI Agent – Human Timing Module.

Provides realistic delays and pauses to make automation look human-like.
"""

import time
import random


class HumanTiming:
    """
    Realistic timing for human-like automation.
    
    All times are in seconds. Slight randomization makes it feel natural.
    """
    
    # Base timings (can be adjusted)
    CURSOR_MOVE_DURATION = 1.2  # seconds to move cursor
    BEFORE_CLICK_PAUSE = 0.3    # pause before clicking
    AFTER_CLICK_PAUSE = 0.5     # pause after clicking
    TYPING_INTERVAL = 0.1       # seconds between keystrokes
    WAIT_FOR_WINDOW = 1.5       # wait for window to appear
    WAIT_FOR_SEARCH = 0.8       # wait for search results
    
    @staticmethod
    def cursor_move_duration(distance_px: int = 500) -> float:
        """
        Calculate cursor move duration based on distance.
        Longer distances take slightly longer.
        """
        base = HumanTiming.CURSOR_MOVE_DURATION
        # Scale by distance (min 0.5s, max 2.5s)
        scaled = base * (distance_px / 500)
        scaled = max(0.5, min(2.5, scaled))
        # Add small randomness
        return scaled + random.uniform(-0.1, 0.1)
    
    @staticmethod
    def before_click() -> None:
        """Pause before clicking (slight randomness)."""
        time.sleep(HumanTiming.BEFORE_CLICK_PAUSE + random.uniform(-0.05, 0.05))
    
    @staticmethod
    def after_click() -> None:
        """Pause after clicking (slight randomness)."""
        time.sleep(HumanTiming.AFTER_CLICK_PAUSE + random.uniform(-0.1, 0.1))
    
    @staticmethod
    def typing_interval() -> float:
        """Get interval between keystrokes (slight randomness)."""
        return HumanTiming.TYPING_INTERVAL + random.uniform(-0.02, 0.03)
    
    @staticmethod
    def wait_for_window() -> None:
        """Wait for a window to appear."""
        time.sleep(HumanTiming.WAIT_FOR_WINDOW)
    
    @staticmethod
    def wait_for_search_results() -> None:
        """Wait for search results to appear."""
        time.sleep(HumanTiming.WAIT_FOR_SEARCH)
    
    @staticmethod
    def short_pause() -> None:
        """Short human-like pause (0.2-0.4s)."""
        time.sleep(random.uniform(0.2, 0.4))
