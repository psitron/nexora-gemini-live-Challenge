"""
Educational Mouse Controller - Visible Mouse Movements for Learning

This controller is designed for students to learn by watching:
- Shows actual mouse movement (not instant teleport)
- Uses both mouse clicks AND keyboard shortcuts
- Slower, deliberate movements
- Visual feedback at each step
- Combines multiple input methods for comprehensive learning

Purpose: Students learn better when they can SEE what the agent is doing
"""

import time
import pyautogui
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class MouseMoveResult:
    """Result of mouse movement operation"""
    success: bool
    message: str
    start_pos: Optional[Tuple[int, int]] = None
    end_pos: Optional[Tuple[int, int]] = None
    duration_ms: float = 0.0


class EducationalMouseController:
    """
    Mouse controller designed for educational purposes.

    Features:
    - Visible mouse movement (students can follow)
    - Slower, deliberate pace (easier to understand)
    - Combination of mouse + keyboard (comprehensive learning)
    - Visual annotations showing what's happening
    """

    # Configuration for educational pacing
    MOVEMENT_DURATION = 0.8  # Seconds to move mouse (slower = easier to follow)
    PAUSE_BEFORE_CLICK = 0.3  # Pause before clicking (builds anticipation)
    PAUSE_AFTER_CLICK = 0.5  # Pause after clicking (show result)

    def __init__(self, educational_mode: bool = True):
        """
        Initialize educational mouse controller.

        Args:
            educational_mode: If True, uses slower visible movements.
                             If False, uses faster direct movements.
        """
        self.educational_mode = educational_mode

        # Safety settings
        pyautogui.FAILSAFE = True  # Move to corner to abort
        pyautogui.PAUSE = 0.1  # Small pause between actions

    def move_to(self, x: int, y: int, show_path: bool = True) -> MouseMoveResult:
        """
        Move mouse to position with visible movement.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            show_path: If True, shows smooth movement path

        Returns:
            MouseMoveResult with details
        """
        start_time = time.time()
        start_pos = pyautogui.position()

        try:
            if self.educational_mode and show_path:
                # Smooth, visible movement for students to follow
                pyautogui.moveTo(
                    x, y,
                    duration=self.MOVEMENT_DURATION,
                    tween=pyautogui.easeInOutQuad  # Direct function reference
                )
                message = f"Mouse moved from {start_pos} to ({x}, {y})"
            else:
                # Direct movement (faster)
                pyautogui.moveTo(x, y)
                message = f"Mouse moved to ({x}, {y})"

            end_pos = pyautogui.position()
            duration_ms = (time.time() - start_time) * 1000

            return MouseMoveResult(
                success=True,
                message=message,
                start_pos=start_pos,
                end_pos=end_pos,
                duration_ms=duration_ms
            )

        except Exception as e:
            return MouseMoveResult(
                success=False,
                message=f"Mouse movement failed: {e}",
                start_pos=start_pos,
                end_pos=None,
                duration_ms=0
            )

    def click_at(self, x: int, y: int, button: str = 'left',
                 show_movement: bool = True) -> MouseMoveResult:
        """
        Move to position and click with visible movement.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            button: 'left', 'right', or 'middle'
            show_movement: If True, shows mouse moving to target

        Returns:
            MouseMoveResult with click details
        """
        start_time = time.time()
        start_pos = pyautogui.position()

        try:
            # Move to target with visible movement
            if show_movement:
                move_result = self.move_to(x, y, show_path=True)
                if not move_result.success:
                    return move_result
            else:
                pyautogui.moveTo(x, y)

            # Pause before clicking (let students see where we're clicking)
            if self.educational_mode:
                time.sleep(self.PAUSE_BEFORE_CLICK)

            # Perform click
            pyautogui.click(button=button)

            # Pause after clicking (let students see the result)
            if self.educational_mode:
                time.sleep(self.PAUSE_AFTER_CLICK)

            end_pos = pyautogui.position()
            duration_ms = (time.time() - start_time) * 1000

            return MouseMoveResult(
                success=True,
                message=f"Clicked {button} button at ({x}, {y})",
                start_pos=start_pos,
                end_pos=end_pos,
                duration_ms=duration_ms
            )

        except Exception as e:
            return MouseMoveResult(
                success=False,
                message=f"Click failed: {e}",
                start_pos=start_pos,
                end_pos=None,
                duration_ms=0
            )

    def double_click_at(self, x: int, y: int, show_movement: bool = True) -> MouseMoveResult:
        """Double-click at position with visible movement."""
        start_time = time.time()
        start_pos = pyautogui.position()

        try:
            # Move to target
            if show_movement:
                move_result = self.move_to(x, y, show_path=True)
                if not move_result.success:
                    return move_result
            else:
                pyautogui.moveTo(x, y)

            # Pause before double-clicking
            if self.educational_mode:
                time.sleep(self.PAUSE_BEFORE_CLICK)

            # Perform double-click
            pyautogui.doubleClick()

            # Pause after double-clicking
            if self.educational_mode:
                time.sleep(self.PAUSE_AFTER_CLICK)

            end_pos = pyautogui.position()
            duration_ms = (time.time() - start_time) * 1000

            return MouseMoveResult(
                success=True,
                message=f"Double-clicked at ({x}, {y})",
                start_pos=start_pos,
                end_pos=end_pos,
                duration_ms=duration_ms
            )

        except Exception as e:
            return MouseMoveResult(
                success=False,
                message=f"Double-click failed: {e}",
                start_pos=start_pos,
                end_pos=None,
                duration_ms=0
            )

    def right_click_at(self, x: int, y: int, show_movement: bool = True) -> MouseMoveResult:
        """Right-click at position with visible movement."""
        return self.click_at(x, y, button='right', show_movement=show_movement)

    def drag_to(self, start_x: int, start_y: int, end_x: int, end_y: int) -> MouseMoveResult:
        """
        Drag from start position to end position.

        Useful for:
        - Selecting text
        - Moving windows
        - Resizing elements
        - Drawing/painting
        """
        start_time = time.time()
        original_pos = pyautogui.position()

        try:
            # Move to start position
            move_result = self.move_to(start_x, start_y, show_path=True)
            if not move_result.success:
                return move_result

            # Pause before dragging
            if self.educational_mode:
                time.sleep(self.PAUSE_BEFORE_CLICK)

            # Perform drag
            pyautogui.drag(
                end_x - start_x,
                end_y - start_y,
                duration=self.MOVEMENT_DURATION,
                button='left'
            )

            # Pause after dragging
            if self.educational_mode:
                time.sleep(self.PAUSE_AFTER_CLICK)

            end_pos = pyautogui.position()
            duration_ms = (time.time() - start_time) * 1000

            return MouseMoveResult(
                success=True,
                message=f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})",
                start_pos=(start_x, start_y),
                end_pos=end_pos,
                duration_ms=duration_ms
            )

        except Exception as e:
            return MouseMoveResult(
                success=False,
                message=f"Drag failed: {e}",
                start_pos=original_pos,
                end_pos=None,
                duration_ms=0
            )

    def hover_at(self, x: int, y: int, hover_duration: float = 1.0) -> MouseMoveResult:
        """
        Move mouse to position and hover (useful for tooltips, menus).

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            hover_duration: How long to hover (seconds)
        """
        start_time = time.time()

        # Move to target
        move_result = self.move_to(x, y, show_path=True)
        if not move_result.success:
            return move_result

        # Hover (useful for tooltips, dropdown menus)
        time.sleep(hover_duration)

        duration_ms = (time.time() - start_time) * 1000

        return MouseMoveResult(
            success=True,
            message=f"Hovered at ({x}, {y}) for {hover_duration}s",
            start_pos=move_result.start_pos,
            end_pos=move_result.end_pos,
            duration_ms=duration_ms
        )

    def demonstrate_action(self, action_name: str, x: int, y: int) -> MouseMoveResult:
        """
        Demonstrate an action with extra-clear visual feedback.

        Steps:
        1. Move mouse slowly to target
        2. Pause (let students see the target)
        3. Perform action
        4. Pause (let students see the result)

        Args:
            action_name: Name of action ("click", "double-click", "right-click")
            x: Target X coordinate
            y: Target Y coordinate
        """
        print(f"  [Educational] Demonstrating: {action_name} at ({x}, {y})")

        # Move slowly to show students where we're going
        move_result = self.move_to(x, y, show_path=True)
        if not move_result.success:
            return move_result

        # Extra pause to highlight the target
        time.sleep(0.5)

        # Perform the action based on type
        if action_name == "double-click":
            result = self.double_click_at(x, y, show_movement=False)
        elif action_name == "right-click":
            result = self.right_click_at(x, y, show_movement=False)
        else:  # default to click
            result = self.click_at(x, y, show_movement=False)

        return result


# Global instance for easy access
_educational_controller = EducationalMouseController(educational_mode=True)


def click_with_movement(x: int, y: int, show_annotation: bool = True) -> MouseMoveResult:
    """
    Click at position with visible mouse movement (educational).

    This function combines:
    - Visible mouse movement (students can follow)
    - Visual annotation (red box showing target)
    - Deliberate pacing (easier to understand)

    Args:
        x: Target X coordinate
        y: Target Y coordinate
        show_annotation: If True, shows red box annotation

    Returns:
        MouseMoveResult with details
    """
    # Show annotation if requested
    if show_annotation:
        try:
            from core.visual_annotator_adapter import highlight_bbox
            # Create a small box around the click point
            box_size = 40
            bbox_str = f"{x - box_size//2},{y - box_size//2},{box_size},{box_size}"
            highlight_bbox(bbox_str, duration=0.5, fade_out_seconds=0.5)
        except Exception as e:
            print(f"  [Warning] Could not show annotation: {e}")

    # Perform click with visible movement
    return _educational_controller.click_at(x, y, show_movement=True)


def set_educational_mode(enabled: bool):
    """
    Enable or disable educational mode.

    Educational mode (enabled=True):
    - Slower, visible mouse movements
    - Pauses to let students observe
    - Combines mouse and keyboard

    Fast mode (enabled=False):
    - Direct, instant movements
    - Minimal pauses
    - Optimized for speed
    """
    global _educational_controller
    _educational_controller.educational_mode = enabled
    print(f"[Educational Mouse] Mode: {'EDUCATIONAL (slow, visible)' if enabled else 'FAST (direct)'}")


# Example usage
if __name__ == "__main__":
    print("Educational Mouse Controller Test")
    print("=" * 60)

    controller = EducationalMouseController(educational_mode=True)

    # Get screen center
    screen_width, screen_height = pyautogui.size()
    center_x = screen_width // 2
    center_y = screen_height // 2

    print(f"\nScreen size: {screen_width}x{screen_height}")
    print(f"Center point: ({center_x}, {center_y})")

    print("\n1. Moving to screen center with visible movement...")
    result = controller.move_to(center_x, center_y, show_path=True)
    print(f"   Result: {result.message}")
    print(f"   Duration: {result.duration_ms:.0f}ms")

    print("\n2. Hovering for 1 second...")
    result = controller.hover_at(center_x, center_y, hover_duration=1.0)
    print(f"   Result: {result.message}")

    print("\n3. Moving to top-left corner...")
    result = controller.move_to(100, 100, show_path=True)
    print(f"   Result: {result.message}")

    print("\nTest complete!")
    print("=" * 60)
