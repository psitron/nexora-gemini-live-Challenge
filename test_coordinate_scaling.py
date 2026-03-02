"""
Test Coordinate Scaling Function

This directly tests the coordinate scaling logic to verify it works correctly
for multi-monitor setups.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from core.monitor_utils import get_selected_monitor, get_all_monitors

def test_coordinate_scaling():
    print("="*70)
    print("COORDINATE SCALING TEST")
    print("="*70)
    print()

    # Get monitor info
    all_monitors = get_all_monitors()
    selected_monitor = get_selected_monitor()
    primary_monitor_num = int(os.getenv("PRIMARY_MONITOR", "1"))

    print(f"PRIMARY_MONITOR setting: {primary_monitor_num}")
    print()
    print(f"All monitors detected:")
    for i, mon in enumerate(all_monitors, 1):
        left, top, right, bottom = mon
        width = right - left
        height = bottom - top
        print(f"  Monitor {i}: ({left}, {top}, {right}, {bottom}) - {width}x{height}")
    print()

    if selected_monitor:
        left, top, right, bottom = selected_monitor
        width = right - left
        height = bottom - top
        print(f"Selected monitor (#{primary_monitor_num}): ({left}, {top}, {right}, {bottom}) - {width}x{height}")
        print()

        # Calculate scale factor (assuming 1024px max width)
        MAX_WIDTH = 1024
        if width > MAX_WIDTH:
            scale = width / MAX_WIDTH
        else:
            scale = 1.0

        monitor_offset = (left, top)

        print(f"Scale factor: {scale:.4f}x")
        print(f"Monitor offset: {monitor_offset}")
        print()

        # Test some example coordinates
        print("="*70)
        print("COORDINATE TRANSFORMATION EXAMPLES:")
        print("="*70)

        test_coords = [
            (249, 468, "Blank workbook (from logs)"),
            (637, 1059, "Search button (from logs)"),
            (69, 590, "Cell A1 (from logs)"),
            (512, 512, "Center of 1024px image"),
        ]

        for hint_x, hint_y, description in test_coords:
            # Apply scaling (same as _scale_hint_to_screen)
            screen_x = int(hint_x * scale) + monitor_offset[0]
            screen_y = int(hint_y * scale) + monitor_offset[1]

            print(f"\n{description}:")
            print(f"  Input (1024px space): ({hint_x}, {hint_y})")
            print(f"  Calculation: ({hint_x} * {scale:.4f}) + {monitor_offset[0]} = {screen_x}")
            print(f"              ({hint_y} * {scale:.4f}) + {monitor_offset[1]} = {screen_y}")
            print(f"  Output (screen space): ({screen_x}, {screen_y})")

            # Check if in bounds
            in_bounds = (left <= screen_x < right and top <= screen_y < bottom)
            if in_bounds:
                print(f"  Status: [OK] Within monitor {primary_monitor_num} bounds")
            else:
                print(f"  Status: [ERROR] OUTSIDE monitor {primary_monitor_num} bounds!")
                print(f"          Monitor bounds: ({left}, {top}) to ({right}, {bottom})")
    else:
        print("ERROR: Could not get selected monitor!")

    print()
    print("="*70)

if __name__ == "__main__":
    test_coordinate_scaling()
