"""
Quick test: Check if OCR works by reading text from Start menu.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyautogui
import time
from core.monitor_utils import get_selected_monitor

# Open Start menu search
print("Opening Start Menu (Win+S)...")
pyautogui.hotkey("win", "s")
time.sleep(1)

# Type "Control Panel"
print("Typing 'Control Panel'...")
pyautogui.write("Control Panel", interval=0.05)
time.sleep(2)

# Try OCR
print("\nTrying OCR on search results...")
try:
    from core.ocr_finder import find_text_on_screen
    
    monitor_rect = get_selected_monitor()
    if monitor_rect:
        left, top, right, bottom = monitor_rect
        # Search region: left half of screen
        search_x = left
        search_y = top + int((bottom - top) * 0.2)
        search_w = int((right - left) * 0.5)
        search_h = int((bottom - top) * 0.6)
        search_region = (search_x, search_y, search_w, search_h)
        print(f"Search region: x={search_x}, y={search_y}, w={search_w}, h={search_h}")
        
        result_bbox = find_text_on_screen("Control", region=search_region, timeout=3.0)
        if result_bbox:
            x, y, w, h = result_bbox
            print(f"SUCCESS: Found 'Control' at ({x},{y}) size {w}x{h}")
            
            # Draw red box
            from core.visual_annotator import highlight_bbox
            highlight_bbox(f"{x},{y},{w},{h}", duration=2.0, fade_out_seconds=2.0)
        else:
            print("FAILED: 'Control' not found")
    else:
        print("ERROR: Could not get monitor rect")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Close Start menu
print("\nClosing Start menu (Esc)...")
time.sleep(1)
pyautogui.press("escape")
print("Done.")
