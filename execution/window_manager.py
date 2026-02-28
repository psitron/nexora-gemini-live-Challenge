"""
Window manager - moves windows to the PRIMARY_MONITOR.
Ensures opened apps appear on the correct monitor.
"""

from __future__ import annotations

import time
from typing import Tuple

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


def move_foreground_window_to_monitor(monitor_rect: Tuple[int, int, int, int]) -> bool:
    """
    Move the current foreground window to the center of the specified monitor.
    
    Args:
        monitor_rect: (left, top, right, bottom) of target monitor
    
    Returns:
        True if window was moved successfully
    """
    try:
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            print("  [Window] No foreground window found")
            return False
        
        left, top, right, bottom = monitor_rect
        mon_w = right - left
        mon_h = bottom - top
        
        # Get current window size
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]
        
        win_rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(win_rect))
        win_w = win_rect.right - win_rect.left
        win_h = win_rect.bottom - win_rect.top
        
        # Center the window on the target monitor
        new_x = left + (mon_w - win_w) // 2
        new_y = top + (mon_h - win_h) // 2
        
        # Ensure window fits on monitor
        if win_w > mon_w:
            new_x = left
            win_w = mon_w
        if win_h > mon_h:
            new_y = top
            win_h = mon_h
        
        user32.MoveWindow(hwnd, new_x, new_y, win_w, win_h, True)
        print(f"  [Window] Moved to monitor at ({left},{top})-({right},{bottom})")
        return True
        
    except Exception as e:
        print(f"  [Window] Failed to move: {e}")
        return False


def move_foreground_to_primary_monitor() -> bool:
    """Move the foreground window to the PRIMARY_MONITOR."""
    from core.monitor_utils import get_selected_monitor
    
    monitor_rect = get_selected_monitor()
    if not monitor_rect:
        print("  [Window] Could not determine PRIMARY_MONITOR")
        return False
    
    return move_foreground_window_to_monitor(monitor_rect)
