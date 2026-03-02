"""
Screen annotation for Linux: draws a precise red box around the target UI element.

Uses GTK+ for transparent overlay windows with fade-out.
Key properties:
  - GTK Window with RGBA visual (transparency)
  - window.set_keep_above(True) (always on top)
  - input_shape_combine_region (click-through)
  - set_accept_focus(False) (doesn't steal focus)
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
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gtk, Gdk, GLib, cairo
    HAS_GTK = True
except (ImportError, ValueError):
    HAS_GTK = False


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
    Draw a red rectangle on screen at exact coordinates (Linux/GTK).

    Non-blocking: shows the box, holds briefly for visual registration,
    then returns. The fade-out continues in a background thread.

    Args:
        bbox: "x,y,w,h" in screen coordinates
        duration: How long to show at full opacity (seconds)
        fade_out_seconds: Duration of fade-out animation (seconds)
    """
    if not HAS_GTK:
        print("  [Annotation unavailable: GTK+ not installed]")
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


# ---- Linux GTK+ overlay implementation ----


class TransparentWindow(Gtk.Window):
    """Transparent GTK window that draws a red rectangle border."""

    def __init__(self, x: int, y: int, w: int, h: int, border: int = 4, padding: int = 6):
        """Initialize transparent window with red box."""
        super().__init__(type=Gtk.WindowType.POPUP)

        self._border = border
        self._padding = padding
        self._inner_w = w
        self._inner_h = h
        self._alpha = 1.0

        # Calculate window dimensions
        win_w = w + 2 * padding
        win_h = h + 2 * padding

        # Set up window properties
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)  # Always on top
        self.set_accept_focus(False)  # Don't steal focus
        self.set_default_size(win_w, win_h)
        self.move(x - padding, y - padding)

        # Enable transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Connect draw signal
        self.connect('draw', self._on_draw)

        # Make click-through after window is realized
        self.connect('realize', self._on_realize)

    def _on_realize(self, widget):
        """Make window click-through after it's realized."""
        # Create empty input region (makes window click-through)
        window = self.get_window()
        if window:
            region = cairo.Region()  # Empty region = click-through
            window.input_shape_combine_region(region, 0, 0)

    def _on_draw(self, widget, cr):
        """Draw the red rectangle border."""
        # Clear background (fully transparent)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Set red color with current alpha
        cr.set_source_rgba(1.0, 0.0, 0.0, self._alpha)

        # Draw red border (multiple strokes for thickness)
        pad = self._padding
        for i in range(self._border):
            offset = i
            cr.rectangle(
                pad - offset,
                pad - offset,
                self._inner_w + 2 * offset,
                self._inner_h + 2 * offset
            )
            cr.set_line_width(1.0)
            cr.stroke()

        return False

    def set_alpha_value(self, alpha: float):
        """Update alpha value and redraw."""
        self._alpha = alpha
        self.queue_draw()


def _create_overlay(
    x: int, y: int, w: int, h: int,
    hold_secs: float, fade_secs: float,
    visible_event: threading.Event,
) -> None:
    """Create transparent window with red box, show, hold, fade, cleanup."""

    # GTK must run in main thread, but we can use GLib.idle_add
    window_ref = {'window': None, 'ready': False}

    def create_window():
        """Create and show window (runs in GTK main thread)."""
        window = TransparentWindow(x, y, w, h)
        window.show_all()
        window_ref['window'] = window
        window_ref['ready'] = True
        visible_event.set()
        return False

    def fade_and_close():
        """Fade out and close window (runs in GTK main thread)."""
        window = window_ref['window']
        if not window:
            return False

        # Hold at full opacity
        time.sleep(hold_secs)

        # Fade out
        steps = max(12, int(fade_secs * 12))
        for i in range(steps, -1, -1):
            alpha = i / steps
            GLib.idle_add(window.set_alpha_value, alpha)
            time.sleep(fade_secs / (steps + 1))

        # Cleanup
        GLib.idle_add(window.destroy)
        return False

    # Check if GTK main loop is running
    if not Gtk.main_level():
        # GTK not initialized, initialize it
        # This happens if we're the first GTK usage
        GLib.idle_add(create_window)

        # Start fade/close in separate thread
        fade_thread = threading.Thread(target=fade_and_close, daemon=True)
        fade_thread.start()

        # Run GTK main loop in this thread
        # Note: This will block until window is destroyed
        try:
            Gtk.main()
        except KeyboardInterrupt:
            pass
    else:
        # GTK already running (e.g., if app uses GTK)
        GLib.idle_add(create_window)

        # Wait for window creation
        visible_event.wait(timeout=2.0)

        # Start fade/close in separate thread
        fade_thread = threading.Thread(target=fade_and_close, daemon=True)
        fade_thread.start()


# Export same interface as Windows version
__all__ = ['highlight_bbox']
