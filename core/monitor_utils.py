"""
Multi-monitor utilities for Windows automation.
Provides monitor enumeration, selection by index, and coordinate helpers.
"""

from __future__ import annotations

import os
from typing import Tuple, List

# Load .env file to ensure PRIMARY_MONITOR is available
from dotenv import load_dotenv
load_dotenv()

try:
    import pyautogui
except ImportError:
    pyautogui = None


def get_all_monitors() -> List[Tuple[int, int, int, int]]:
    """
    Returns list of all monitor rects as [(left, top, right, bottom), ...].
    Monitors are ordered by their position (typically left-to-right).
    """
    try:
        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        monitors = []

        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                r = info.rcMonitor
                monitors.append((r.left, r.top, r.right, r.bottom))
            return 1

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
        )
        ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
        return sorted(monitors, key=lambda r: (r[0], r[1]))  # Sort left-to-right, top-to-bottom
    except Exception:
        return []


def get_primary_monitor_index() -> int:
    """
    Returns the index (1-based) of the primary monitor from PRIMARY_MONITOR env var.
    Defaults to 2 if not set (middle monitor for 3-monitor setup).
    """
    env_val = os.getenv("PRIMARY_MONITOR", "2")
    try:
        return max(1, int(env_val))
    except ValueError:
        return 2


def get_monitor_by_index(index: int) -> Tuple[int, int, int, int] | None:
    """
    Returns (left, top, right, bottom) of monitor at 1-based index.
    If index is out of range, returns the last monitor.
    """
    monitors = get_all_monitors()
    if not monitors:
        return None
    idx = min(index - 1, len(monitors) - 1)
    return monitors[idx]


def get_selected_monitor() -> Tuple[int, int, int, int] | None:
    """
    Returns the monitor rect for the user's PRIMARY_MONITOR env setting.
    """
    idx = get_primary_monitor_index()
    return get_monitor_by_index(idx)


def get_monitor_rect_containing_cursor() -> Tuple[int, int, int, int] | None:
    """
    Returns (left, top, right, bottom) of the monitor that contains the cursor,
    in virtual screen coordinates. Returns None if unavailable.
    """
    if not pyautogui:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        user32 = ctypes.windll.user32
        cx, cy = pyautogui.position()
        pt = POINT(cx, cy)
        hmon = user32.MonitorFromPoint(pt, 2)  # 2 = MONITOR_DEFAULTTONEAREST
        if not hmon:
            return None
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            return None
        r = info.rcMonitor
        return (r.left, r.top, r.right, r.bottom)
    except Exception:
        return None


def center_of_monitor_containing_cursor() -> Tuple[int, int] | None:
    """(center_x, center_y) of the monitor that contains the cursor."""
    rect = get_monitor_rect_containing_cursor()
    if not rect:
        return None
    left, top, right, bottom = rect
    return ((left + right) // 2, (top + bottom) // 2)


def search_box_bbox_on_selected_monitor() -> str | None:
    """
    Estimated "x,y,w,h" for the Windows search box on the PRIMARY_MONITOR.
    For Windows 11: taskbar search icon is bottom-left.
    For Windows 10: search box is also bottom-left in taskbar.
    """
    rect = get_selected_monitor()
    if not rect:
        return None
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    
    # Windows taskbar search: bottom-left corner, ~15% from left, ~4% height
    # Positioned just above the taskbar bottom
    x = left + int(width * 0.02)  # 2% from left edge
    y = bottom - int(height * 0.05)  # 5% from bottom (taskbar area)
    w = int(width * 0.20)  # 20% width for search box
    h = int(height * 0.04)  # 4% height
    if h < 40:
        h = 40
    if w < 200:
        w = 200
    return f"{x},{y},{w},{h}"
