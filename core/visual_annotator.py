"""
Screen annotation: draws a precise red box around the target UI element.

Uses Win32 layered windows for smooth display with fade-out.
Key properties:
  - WS_EX_TRANSPARENT: click-through (doesn't steal focus/clicks)
  - WS_EX_TOPMOST: always on top of all windows
  - WS_EX_NOACTIVATE: doesn't activate/flash taskbar
  - Threaded fade-out: returns quickly, fade continues in background
  - Unique window class per overlay: avoids RegisterClassEx conflicts
"""

from __future__ import annotations

import time
import threading
import ctypes
from ctypes import wintypes
from typing import Tuple

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

_class_counter = 0
_class_lock = threading.Lock()


def _next_class_name() -> bytes:
    global _class_counter
    with _class_lock:
        _class_counter += 1
        return f"AnnotBox{_class_counter}".encode("ascii")


def _parse_bbox(bbox: str) -> Tuple[int, int, int, int]:
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
    Draw a red rectangle on screen at exact coordinates.

    Non-blocking: shows the box, holds briefly for visual registration,
    then returns. The fade-out continues in a background thread.

    bbox: "x,y,w,h" in screen coordinates
    """
    try:
        x, y, w, h = _parse_bbox(bbox)
    except Exception:
        return

    if not HAS_PIL:
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

    visible_event.wait(timeout=2.0)
    time.sleep(min(duration, 0.4))


# ---- Win32 overlay implementation ----

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, ctypes.c_ulonglong, ctypes.c_longlong
)

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
SW_SHOWNOACTIVATE = 4
ULW_ALPHA = 0x00000002
AC_SRC_ALPHA = 0x01


def _build_red_box_image(w: int, h: int, border: int = 4, pad: int = 6):
    """Create RGBA image with red rectangle border, transparent fill."""
    img_w = w + 2 * pad
    img_h = h + 2 * pad

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i in range(border):
        draw.rectangle(
            [pad - i, pad - i, w + pad + i - 1, h + pad + i - 1],
            outline=(255, 0, 0, 255),
        )

    # Convert RGBA to pre-multiplied BGRA for Windows
    raw = bytearray(img_w * img_h * 4)
    pixels = img.tobytes()
    for idx in range(img_w * img_h):
        off = idx * 4
        r, g, b, a = pixels[off], pixels[off + 1], pixels[off + 2], pixels[off + 3]
        raw[off] = b * a // 255
        raw[off + 1] = g * a // 255
        raw[off + 2] = r * a // 255
        raw[off + 3] = a

    return img_w, img_h, bytes(raw)


def _create_overlay(
    x: int, y: int, w: int, h: int,
    hold_secs: float, fade_secs: float,
    visible_event: threading.Event,
) -> None:
    """Create layered window with red box, show, hold, fade, cleanup."""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32

    pad = 6
    img_w, img_h, bits = _build_red_box_image(w, h)
    win_x = x - pad
    win_y = y - pad

    # Create DIB section
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = img_w
    bmi.bmiHeader.biHeight = -img_h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32

    ptr = ctypes.c_void_p()
    hdc_screen = user32.GetDC(None)
    hbm = gdi32.CreateDIBSection(
        hdc_screen, ctypes.byref(bmi), 0, ctypes.byref(ptr), None, 0
    )
    if not hbm:
        user32.ReleaseDC(None, hdc_screen)
        visible_event.set()
        return
    ctypes.memmove(ptr.value, bits, len(bits))

    # Window class (unique name avoids RegisterClassEx conflicts)
    WC = _next_class_name()
    hinst = kernel32.GetModuleHandleA(None)

    user32.DefWindowProcA.argtypes = [
        wintypes.HWND, wintypes.UINT, ctypes.c_ulonglong, ctypes.c_longlong
    ]
    user32.DefWindowProcA.restype = LRESULT

    def wndproc(hwnd, msg, wp, lp):
        return user32.DefWindowProcA(hwnd, msg, wp, lp)

    _wndproc_ref = WNDPROC(wndproc)

    class WNDCLASSEXA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT), ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HANDLE),
            ("hIcon", wintypes.HANDLE), ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HANDLE), ("lpszMenuName", ctypes.c_void_p),
            ("lpszClassName", ctypes.c_void_p), ("hIconSm", wintypes.HANDLE),
        ]

    wc = WNDCLASSEXA()
    wc.cbSize = ctypes.sizeof(WNDCLASSEXA)
    wc.lpfnWndProc = _wndproc_ref
    wc.hInstance = hinst
    wc.lpszClassName = ctypes.cast(ctypes.c_char_p(WC), ctypes.c_void_p)

    if not user32.RegisterClassExA(ctypes.byref(wc)):
        gdi32.DeleteObject(hbm)
        user32.ReleaseDC(None, hdc_screen)
        visible_event.set()
        return

    # Create layered, click-through, always-on-top window
    ex_style = WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
    hwnd = user32.CreateWindowExA(
        ex_style, WC, None, WS_POPUP,
        win_x, win_y, img_w, img_h,
        None, None, hinst, None,
    )
    if not hwnd:
        gdi32.DeleteObject(hbm)
        user32.UnregisterClassA(WC, hinst)
        user32.ReleaseDC(None, hdc_screen)
        visible_event.set()
        return

    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    old_bm = gdi32.SelectObject(hdc_mem, hbm)

    pt_pos = POINT(win_x, win_y)
    pt_src = POINT(0, 0)
    sz = SIZE(img_w, img_h)

    def update_alpha(alpha: int):
        blend = BLENDFUNCTION(0, 0, alpha, AC_SRC_ALPHA)
        user32.UpdateLayeredWindow(
            hwnd, hdc_screen,
            ctypes.byref(pt_pos), ctypes.byref(sz),
            hdc_mem, ctypes.byref(pt_src),
            0, ctypes.byref(blend), ULW_ALPHA,
        )

    # Show at full opacity
    update_alpha(255)
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

    visible_event.set()

    # Hold at full opacity
    time.sleep(hold_secs)

    # Fade out
    steps = max(12, int(fade_secs * 12))
    for i in range(steps, -1, -1):
        alpha = int(255 * i / steps)
        update_alpha(alpha)
        time.sleep(fade_secs / (steps + 1))

    # Cleanup
    gdi32.SelectObject(hdc_mem, old_bm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(None, hdc_screen)
    user32.DestroyWindow(hwnd)
    gdi32.DeleteObject(hbm)
    user32.UnregisterClassA(WC, hinst)
