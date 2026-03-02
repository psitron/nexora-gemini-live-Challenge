"""
Screen annotation for macOS: draws a precise red box around the target UI element.

Uses AppKit/Quartz for transparent overlay windows with fade-out.
Key properties:
  - NSWindow with transparent background
  - NSWindowLevel.floating (always on top)
  - ignoresMouseEvents (click-through)
  - Non-activating (doesn't steal focus)
  - Threaded fade-out: returns quickly, fade continues in background
"""

from __future__ import annotations

import time
import threading
from typing import Tuple, Optional

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import Cocoa
    import Quartz
    from AppKit import (
        NSWindow, NSView, NSColor, NSBezierPath, NSApp,
        NSBackingStoreBuffered, NSWindowStyleMaskBorderless,
        NSScreen, NSGraphicsContext, NSCompositingOperationSourceOver
    )
    from Foundation import NSRect, NSPoint, NSSize, NSMakeRect
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


def _parse_bbox(bbox: str) -> Tuple[int, int, int, int]:
    """Parse bbox string 'x,y,w,h' into tuple."""
    parts = [int(p.strip()) for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Expected 'x,y,w,h', got: {bbox}")
    return parts[0], parts[1], parts[2], parts[3]


def highlight_bbox(
    bbox: str,
    duration: float = 0.8,
    fade_out_seconds: float = 1.2,
) -> None:
    """
    Draw a red rectangle on screen at exact coordinates (macOS).

    Non-blocking: shows the box, holds briefly for visual registration,
    then returns. The fade-out continues in a background thread.

    Args:
        bbox: "x,y,w,h" in screen coordinates
        duration: How long to show at full opacity (seconds)
        fade_out_seconds: Duration of fade-out animation (seconds)
    """
    if not HAS_APPKIT:
        print("  [Annotation unavailable: pyobjc not installed]")
        return

    try:
        x, y, w, h = _parse_bbox(bbox)
    except Exception as e:
        print(f"  [Annotation error: invalid bbox: {e}]")
        return

    if not HAS_PIL:
        print("  [Annotation unavailable: PIL not installed]")
        return

    print(f"  [Red box at ({x},{y}) {w}x{h}]")

    visible_event = threading.Event()

    def _overlay():
        try:
            _create_overlay(x, y, w, h, duration, fade_out_seconds, visible_event)
        except Exception as e:
            print(f"  [Annotation error: {e}]")
            visible_event.set()

    t = threading.Thread(target=_overlay, daemon=True)
    t.start()

    # Wait for window to become visible
    visible_event.wait(timeout=2.0)
    time.sleep(min(duration, 0.4))


# ---- macOS AppKit overlay implementation ----


class RedBoxView(NSView):
    """Custom view that draws a red rectangle border."""

    def initWithFrame_border_padding_(self, frame, border: int, padding: int):
        """Initialize with frame and drawing parameters."""
        self = super(RedBoxView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._border = border
        self._padding = padding
        self._alpha = 1.0

        return self

    def drawRect_(self, dirty_rect):
        """Draw the red rectangle border."""
        # Clear background (transparent)
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(self.bounds())

        # Get inner rectangle dimensions (subtract padding)
        pad = self._padding
        inner_rect = NSMakeRect(
            pad,
            pad,
            self.bounds().size.width - 2 * pad,
            self.bounds().size.height - 2 * pad
        )

        # Draw red border (multiple strokes for thickness)
        context = NSGraphicsContext.currentContext()
        context.saveGraphicsState()

        # Set red color with current alpha
        red_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(
            1.0, 0.0, 0.0, self._alpha
        )
        red_color.set()

        # Draw multiple strokes for border thickness
        for i in range(self._border):
            offset = i
            stroke_rect = NSMakeRect(
                inner_rect.origin.x - offset,
                inner_rect.origin.y - offset,
                inner_rect.size.width + 2 * offset,
                inner_rect.size.height + 2 * offset
            )
            path = NSBezierPath.bezierPathWithRect_(stroke_rect)
            path.setLineWidth_(1.0)
            path.stroke()

        context.restoreGraphicsState()

    def setAlpha_(self, alpha: float):
        """Update alpha value and redraw."""
        self._alpha = alpha
        self.setNeedsDisplay_(True)


def _create_overlay(
    x: int, y: int, w: int, h: int,
    hold_secs: float, fade_secs: float,
    visible_event: threading.Event,
) -> None:
    """Create transparent window with red box, show, hold, fade, cleanup."""

    # Create autorelease pool for this thread
    pool = Cocoa.NSAutoreleasePool.alloc().init()

    try:
        pad = 6
        border = 4

        # Calculate window dimensions
        win_w = w + 2 * pad
        win_h = h + 2 * pad

        # macOS uses bottom-left origin, need to convert from top-left
        # Get screen height for coordinate conversion
        main_screen = NSScreen.mainScreen()
        screen_height = main_screen.frame().size.height

        # Convert y coordinate (top-left to bottom-left)
        win_y = screen_height - y - win_h
        win_x = x - pad

        # Create window frame
        frame = NSMakeRect(win_x, win_y, win_w, win_h)

        # Create window with transparent style
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )

        # Configure window properties
        window.setOpaque_(False)
        window.setBackgroundColor_(NSColor.clearColor())
        window.setHasShadow_(False)
        window.setIgnoresMouseEvents_(True)  # Click-through
        window.setLevel_(Cocoa.NSFloatingWindowLevel)  # Always on top
        window.setCollectionBehavior_(
            Cocoa.NSWindowCollectionBehaviorCanJoinAllSpaces |
            Cocoa.NSWindowCollectionBehaviorStationary
        )

        # Create custom view
        view_frame = NSMakeRect(0, 0, win_w, win_h)
        view = RedBoxView.alloc().initWithFrame_border_padding_(
            view_frame, border, pad
        )

        window.setContentView_(view)

        # Show window at full opacity
        window.setAlphaValue_(1.0)
        window.orderFrontRegardless()

        visible_event.set()

        # Hold at full opacity
        time.sleep(hold_secs)

        # Fade out
        steps = max(12, int(fade_secs * 12))
        for i in range(steps, -1, -1):
            alpha = i / steps
            view.setAlpha_(alpha)
            window.setAlphaValue_(alpha)
            # Force redraw
            view.display()
            time.sleep(fade_secs / (steps + 1))

        # Cleanup
        window.orderOut_(None)
        window.close()

    finally:
        del pool


# Export same interface as Windows version
__all__ = ['highlight_bbox']
