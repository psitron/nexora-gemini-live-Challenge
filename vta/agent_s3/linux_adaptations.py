"""
Linux adaptations for Agent S3 running on Xvfb virtual display.

Monkey-patches core modules to work on EC2 Ubuntu with Xvfb
instead of Windows multi-monitor setup.
"""

import os
import subprocess
import sys


def get_xvfb_dimensions() -> tuple[int, int]:
    """Read Xvfb display dimensions from xdpyinfo or env vars."""
    width = int(os.environ.get("VTA_DISPLAY_WIDTH", "1280"))
    height = int(os.environ.get("VTA_DISPLAY_HEIGHT", "800"))

    try:
        result = subprocess.run(
            ["xdpyinfo"],
            capture_output=True, text=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")},
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "dimensions:" in line:
                dim_str = line.split("dimensions:")[1].strip().split()[0]
                w, h = dim_str.split("x")
                width, height = int(w), int(h)
                break
    except Exception:
        pass

    return width, height


def apply_linux_patches():
    """
    Apply all monkey-patches for Linux/Xvfb environment.
    Call this once at Agent S3 server startup, before importing core modules.
    """
    # Set DISPLAY for Xvfb
    os.environ.setdefault("DISPLAY", ":1")

    # Patch monitor_utils to return Xvfb dimensions
    #_patch_monitor_utils()

    # Patch Tesseract path for Linux
    _patch_tesseract()

    # Disable Windows-specific imports
    _patch_platform_specifics()


def _patch_monitor_utils():
    """Replace get_selected_monitor() to return Xvfb rect."""
    width, height = get_xvfb_dimensions()
    xvfb_rect = (0, 0, width, height)

    try:
        from core import monitor_utils

        monitor_utils.get_selected_monitor = lambda: xvfb_rect
        monitor_utils.get_all_monitors = lambda: [xvfb_rect]
        monitor_utils.get_primary_monitor_index = lambda: 1
        monitor_utils.get_monitor_by_index = lambda idx: xvfb_rect
        monitor_utils.get_monitor_rect_containing_cursor = lambda: xvfb_rect
    except ImportError:
        # Add project root to path and retry
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from core import monitor_utils

        monitor_utils.get_selected_monitor = lambda: xvfb_rect
        monitor_utils.get_all_monitors = lambda: [xvfb_rect]
        monitor_utils.get_primary_monitor_index = lambda: 1
        monitor_utils.get_monitor_by_index = lambda idx: xvfb_rect
        monitor_utils.get_monitor_rect_containing_cursor = lambda: xvfb_rect


def _patch_tesseract():
    """Set Tesseract binary path for Linux."""
    linux_tesseract = "/usr/bin/tesseract"
    if os.path.exists(linux_tesseract):
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = linux_tesseract
        except ImportError:
            pass


def _patch_platform_specifics():
    """Disable Windows-specific modules that fail on Linux."""
    import importlib

    # Stub out Windows-only modules
    class _StubModule:
        def __getattr__(self, name):
            return lambda *a, **kw: None

    windows_modules = [
        "ctypes.windll",
        "win32gui",
        "win32con",
        "win32api",
    ]
    for mod_name in windows_modules:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = _StubModule()
