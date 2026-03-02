"""
Platform Abstraction Layer for Visual Annotation.

Automatically selects the correct visual annotator implementation based on the platform:
- Windows: Win32 API layered windows
- macOS: AppKit/Quartz transparent windows
- Linux: GTK+ transparent windows

Usage:
    from core.visual_annotator_adapter import highlight_bbox

    # Works on all platforms!
    highlight_bbox("100,200,300,50", duration=0.8, fade_out_seconds=1.2)
"""

from __future__ import annotations

import platform
from typing import Callable

# Platform detection
_system = platform.system()

# Import appropriate implementation
_highlight_bbox_impl: Callable[[str, float, float], None] | None = None

if _system == "Windows":
    try:
        from core.visual_annotator import highlight_bbox as _highlight_bbox_impl
        _PLATFORM_NAME = "Windows (Win32 API)"
    except ImportError as e:
        _PLATFORM_NAME = f"Windows (unavailable: {e})"

elif _system == "Darwin":  # macOS
    try:
        from core.visual_annotator_macos import highlight_bbox as _highlight_bbox_impl
        _PLATFORM_NAME = "macOS (AppKit/Quartz)"
    except ImportError as e:
        _PLATFORM_NAME = f"macOS (unavailable: {e})"

elif _system == "Linux":
    try:
        from core.visual_annotator_linux import highlight_bbox as _highlight_bbox_impl
        _PLATFORM_NAME = "Linux (GTK+)"
    except ImportError as e:
        _PLATFORM_NAME = f"Linux (unavailable: {e})"

else:
    _PLATFORM_NAME = f"Unsupported ({_system})"


def highlight_bbox(
    bbox: str,
    duration: float = 0.8,
    fade_out_seconds: float = 1.2,
) -> None:
    """
    Draw a red rectangle on screen at exact coordinates (cross-platform).

    Automatically uses the appropriate implementation for the current platform:
    - Windows: Win32 API layered windows
    - macOS: AppKit/Quartz transparent windows
    - Linux: GTK+ transparent windows

    Args:
        bbox: "x,y,w,h" in screen coordinates
        duration: How long to show at full opacity (seconds)
        fade_out_seconds: Duration of fade-out animation (seconds)

    Example:
        >>> highlight_bbox("100,200,300,50", duration=0.8, fade_out_seconds=1.2)
        [Red box at (100,200) 300x50]
    """
    if _highlight_bbox_impl is None:
        print(f"  [Annotation unavailable on {_PLATFORM_NAME}]")
        return

    try:
        _highlight_bbox_impl(bbox, duration, fade_out_seconds)
    except Exception as e:
        print(f"  [Annotation error: {e}]")


def get_platform_info() -> dict[str, str]:
    """
    Get information about visual annotation platform support.

    Returns:
        Dictionary with:
        - system: Platform name (Windows/Darwin/Linux)
        - implementation: Implementation technology
        - available: Whether annotation is available

    Example:
        >>> info = get_platform_info()
        >>> print(info)
        {
            'system': 'Darwin',
            'implementation': 'AppKit/Quartz',
            'available': True
        }
    """
    return {
        'system': _system,
        'implementation': _PLATFORM_NAME,
        'available': _highlight_bbox_impl is not None,
    }


# Export same interface as platform-specific versions
__all__ = ['highlight_bbox', 'get_platform_info']


if __name__ == "__main__":
    """Test visual annotator adapter."""
    print("=" * 60)
    print("Visual Annotator Platform Adapter Test")
    print("=" * 60)

    # Print platform info
    info = get_platform_info()
    print(f"\nPlatform: {info['system']}")
    print(f"Implementation: {info['implementation']}")
    print(f"Available: {info['available']}")

    if info['available']:
        print("\nTesting annotation (should see red box for 2 seconds)...")
        print("Drawing box at center of screen: 500,400,200,100")

        try:
            highlight_bbox("500,400,200,100", duration=1.0, fade_out_seconds=1.0)
            print("[OK] Annotation test completed")
        except Exception as e:
            print(f"[FAIL] Annotation test failed: {e}")
    else:
        print("\n[WARN] Visual annotation not available on this platform")
        print(f"Reason: {info['implementation']}")

        if _system == "Darwin":
            print("\nTo enable macOS support:")
            print("  pip install pyobjc-framework-Cocoa")
            print("  pip install pyobjc-framework-Quartz")
        elif _system == "Linux":
            print("\nTo enable Linux support:")
            print("  sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0")
            print("  pip install PyGObject")

    print("=" * 60)
