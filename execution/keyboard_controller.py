"""
Keyboard automation for Windows applications.
Handles keyboard shortcuts, typing, and key presses with visual annotations.
"""

from __future__ import annotations

import time
from typing import List
from dataclasses import dataclass

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


@dataclass
class KeyboardResult:
    success: bool
    message: str


def press_keys(*keys: str, annotation: bool = True) -> KeyboardResult:
    """
    Press a sequence of keys (hotkey).
    
    Args:
        *keys: Keys to press (e.g., 'ctrl', 'm' for Ctrl+M)
        annotation: Whether to show visual annotation
    
    Returns:
        KeyboardResult with success status
    """
    if not HAS_PYAUTOGUI:
        return KeyboardResult(False, "pyautogui not available")
    
    try:
        keys_str = "+".join(keys)
        print(f"  Pressing: {keys_str}")
        
        if annotation:
            try:
                from core.visual_annotator_adapter import highlight_bbox
                from core.monitor_utils import get_selected_monitor
                
                # Show annotation at top-center of monitor
                monitor_rect = get_selected_monitor()
                if monitor_rect:
                    left, top, right, bottom = monitor_rect
                    w = int((right - left) * 0.3)
                    h = 60
                    x = left + (right - left) // 2 - w // 2
                    y = top + 50
                    
                    # Annotate keyboard action
                    highlight_bbox(f"{x},{y},{w},{h}", duration=0.8, fade_out_seconds=1.0)
            except Exception:
                pass  # Annotation failed, continue anyway
        
        pyautogui.hotkey(*keys)
        time.sleep(0.5)
        
        return KeyboardResult(True, f"Pressed {keys_str}")
    except Exception as e:
        return KeyboardResult(False, f"Failed to press keys: {e}")


def type_text(text: str, interval: float = 0.05) -> KeyboardResult:
    """
    Type text character by character.
    
    Args:
        text: Text to type
        interval: Delay between characters
    
    Returns:
        KeyboardResult with success status
    """
    if not HAS_PYAUTOGUI:
        return KeyboardResult(False, "pyautogui not available")
    
    try:
        print(f"  Typing: {text}")
        pyautogui.write(text, interval=interval)
        return KeyboardResult(True, f"Typed '{text}'")
    except Exception as e:
        return KeyboardResult(False, f"Failed to type: {e}")


# Common keyboard shortcuts
SHORTCUTS = {
    # File operations
    "new": ["ctrl", "n"],
    "open": ["ctrl", "o"],
    "save": ["ctrl", "s"],
    "save_as": ["ctrl", "shift", "s"],
    "close": ["ctrl", "w"],
    "print": ["ctrl", "p"],
    
    # Edit operations
    "undo": ["ctrl", "z"],
    "redo": ["ctrl", "y"],
    "cut": ["ctrl", "x"],
    "copy": ["ctrl", "c"],
    "paste": ["ctrl", "v"],
    "select_all": ["ctrl", "a"],
    "find": ["ctrl", "f"],
    
    # PowerPoint specific
    "new_slide": ["ctrl", "m"],
    "duplicate_slide": ["ctrl", "d"],
    "delete_slide": ["delete"],
    
    # Windows system
    "screenshot": ["win", "shift", "s"],
    "task_view": ["win", "tab"],
    "settings": ["win", "i"],
    "file_explorer": ["win", "e"],
    
    # Volume
    "volume_up": ["volumeup"],
    "volume_down": ["volumedown"],
    "volume_mute": ["volumemute"],
}


def execute_shortcut(shortcut_name: str) -> KeyboardResult:
    """
    Execute a named keyboard shortcut.
    
    Args:
        shortcut_name: Name of shortcut (e.g., 'new_slide', 'save', 'copy')
    
    Returns:
        KeyboardResult with success status
    """
    if shortcut_name not in SHORTCUTS:
        return KeyboardResult(False, f"Unknown shortcut: {shortcut_name}")
    
    keys = SHORTCUTS[shortcut_name]
    return press_keys(*keys, annotation=True)
