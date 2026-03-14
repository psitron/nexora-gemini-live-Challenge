"""
Windows-adapted action dispatch for Agent S3.

Replaces xdotool/Xvfb calls with pyautogui and native Windows APIs.
Each function executes exactly one atomic UI action and returns
a result dict with success status.
"""

import base64
import io
import logging
import os
import subprocess
import time
from typing import Optional

import pyautogui
from PIL import Image

logger = logging.getLogger(__name__)

# Configure pyautogui for Windows
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1


def open_terminal() -> dict:
    """Open a terminal on Windows (Windows Terminal or cmd)."""
    try:
        # Try Windows Terminal first
        try:
            subprocess.Popen(
                ["wt"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(2.0)
            return {"success": True, "action": "open_terminal", "terminal": "wt"}
        except FileNotFoundError:
            pass

        # Fall back to cmd
        subprocess.Popen(
            ["cmd", "/c", "start", "cmd"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)
        return {"success": True, "action": "open_terminal", "terminal": "cmd"}
    except Exception as e:
        logger.error(f"open_terminal failed: {e}")
        return {"success": False, "action": "open_terminal", "error": str(e)}


def run_command(cmd: str) -> dict:
    """Type a command in the active terminal and press Enter."""
    try:
        # Small delay to ensure terminal is ready
        time.sleep(0.3)

        # Type the command character by character for reliability
        pyautogui.write(cmd, interval=0.03)
        time.sleep(0.2)

        # Press Enter
        pyautogui.press("enter")
        time.sleep(0.5)

        return {"success": True, "action": "run_command", "cmd": cmd}
    except Exception as e:
        logger.error(f"run_command failed: {e}")
        return {"success": False, "action": "run_command", "cmd": cmd, "error": str(e)}


def click_text(target: str, hint_x: int = -1, hint_y: int = -1) -> dict:
    """
    Find and click text on screen.

    Uses grounding agent for precise location if available,
    falls back to hint coordinates.
    """
    try:
        click_x, click_y = _find_text_coordinates(target, hint_x, hint_y)
        if click_x is not None:
            _smooth_click(click_x, click_y)
            return {
                "success": True, "action": "click_text",
                "target": target, "x": click_x, "y": click_y,
            }

        if hint_x >= 0 and hint_y >= 0:
            _smooth_click(hint_x, hint_y)
            return {
                "success": True, "action": "click_text",
                "target": target, "x": hint_x, "y": hint_y,
                "method": "hint_fallback",
            }

        return {
            "success": False, "action": "click_text",
            "target": target, "error": "Could not locate text",
        }
    except Exception as e:
        logger.error(f"click_text failed: {e}")
        return {"success": False, "action": "click_text", "error": str(e)}


def type_text(text: str) -> dict:
    """Type text into the currently focused field using pyautogui."""
    try:
        # pyautogui.write handles Unicode on Windows
        pyautogui.write(text, interval=0.02)
        return {"success": True, "action": "type_text", "text": text}
    except Exception as e:
        logger.error(f"type_text failed: {e}")
        return {"success": False, "action": "type_text", "error": str(e)}


def keyboard(keys: str) -> dict:
    """
    Press keyboard keys/combos.

    Supports formats like "enter", "ctrl+c", "alt+F4".
    """
    try:
        parts = keys.lower().replace(" ", "").split("+")
        translated = [_translate_key(k) for k in parts]

        if len(translated) == 1:
            pyautogui.press(translated[0])
        else:
            pyautogui.hotkey(*translated)

        return {"success": True, "action": "keyboard", "keys": keys}
    except Exception as e:
        logger.error(f"keyboard failed: {e}")
        return {"success": False, "action": "keyboard", "error": str(e)}


def take_screenshot() -> dict:
    """Capture screenshot of the primary display."""
    try:
        import mss

        with mss.mss() as sct:
            monitors = sct.monitors
            monitor = monitors[1] if len(monitors) > 1 else monitors[0]
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "success": True,
            "action": "screenshot",
            "image": b64_image,
            "width": img.width,
            "height": img.height,
        }
    except Exception as e:
        logger.error(f"screenshot failed: {e}")
        return {"success": False, "action": "screenshot", "error": str(e)}


def click_position(x: int, y: int) -> dict:
    """Click at specific screen coordinates."""
    try:
        _smooth_click(x, y)
        return {"success": True, "action": "click_position", "x": x, "y": y}
    except Exception as e:
        logger.error(f"click_position failed: {e}")
        return {"success": False, "action": "click_position", "error": str(e)}


def double_click(x: int, y: int) -> dict:
    """Double-click at specific screen coordinates."""
    try:
        pyautogui.moveTo(x, y, duration=0.5)
        time.sleep(0.1)
        pyautogui.doubleClick(x, y)
        return {"success": True, "action": "double_click", "x": x, "y": y}
    except Exception as e:
        logger.error(f"double_click failed: {e}")
        return {"success": False, "action": "double_click", "error": str(e)}


def drag(start_x: int, start_y: int, end_x: int, end_y: int) -> dict:
    """Drag from start position to end position."""
    try:
        pyautogui.moveTo(start_x, start_y, duration=0.3)
        time.sleep(0.1)
        pyautogui.mouseDown()
        pyautogui.moveTo(end_x, end_y, duration=0.8)
        pyautogui.mouseUp()
        return {
            "success": True, "action": "drag",
            "start": (start_x, start_y), "end": (end_x, end_y),
        }
    except Exception as e:
        logger.error(f"drag failed: {e}")
        return {"success": False, "action": "drag", "error": str(e)}


def scroll(direction: str = "down", clicks: int = 3) -> dict:
    """Scroll up or down."""
    try:
        amount = clicks if direction == "up" else -clicks
        pyautogui.scroll(amount)
        return {"success": True, "action": "scroll", "direction": direction}
    except Exception as e:
        logger.error(f"scroll failed: {e}")
        return {"success": False, "action": "scroll", "error": str(e)}


# --- Helper Functions ---

def _smooth_click(x: int, y: int):
    """Move mouse visibly then click (educational mode)."""
    pyautogui.moveTo(x, y, duration=0.5)
    time.sleep(0.2)
    pyautogui.click(x, y)
    time.sleep(0.3)


def _find_text_coordinates(
    target: str, hint_x: int, hint_y: int,
) -> tuple[Optional[int], Optional[int]]:
    """
    Try to find text on screen using grounding agent.
    Returns (x, y) center coordinates or (None, None).
    """
    try:
        from core.grounding_agent import GroundingAgent

        agent = GroundingAgent()
        screenshot_result = take_screenshot()
        if not screenshot_result["success"]:
            return None, None

        img_bytes = base64.b64decode(screenshot_result["image"])
        img = Image.open(io.BytesIO(img_bytes))

        hint = (hint_x, hint_y) if hint_x >= 0 and hint_y >= 0 else None
        bbox = agent.find_element(img, target, hint_position=hint)
        if bbox:
            x, y, w, h = bbox
            return x + w // 2, y + h // 2
    except Exception as e:
        logger.debug(f"Grounding agent lookup failed: {e}")

    return None, None


def _translate_key(key: str) -> str:
    """Translate common key names to pyautogui format."""
    mapping = {
        "return": "enter",
        "esc": "escape",
        "pageup": "pageup",
        "pagedown": "pagedown",
        "ctrl": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "super": "win",
        "win": "win",
        "backspace": "backspace",
        "delete": "delete",
        "space": "space",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "home": "home",
        "end": "end",
        "tab": "tab",
        "enter": "enter",
        "escape": "escape",
    }
    return mapping.get(key, key)


# Action dispatch table
ACTION_DISPATCH = {
    "open_terminal": lambda params: open_terminal(),
    "run_command": lambda params: run_command(params.get("cmd", "")),
    "click_text": lambda params: click_text(
        params.get("target", ""),
        params.get("hint_x", -1),
        params.get("hint_y", -1),
    ),
    "type_text": lambda params: type_text(params.get("text", "")),
    "keyboard": lambda params: keyboard(params.get("keys", "")),
    "screenshot": lambda params: take_screenshot(),
    "click_position": lambda params: click_position(
        params.get("x", 0), params.get("y", 0),
    ),
    "double_click": lambda params: double_click(
        params.get("x", 0), params.get("y", 0),
    ),
    "drag": lambda params: drag(
        params.get("start_x", 0), params.get("start_y", 0),
        params.get("end_x", 0), params.get("end_y", 0),
    ),
    "scroll": lambda params: scroll(
        params.get("direction", "down"), params.get("clicks", 3),
    ),
}


def dispatch(action_type: str, params: dict) -> dict:
    """Dispatch an action by type. Returns result dict."""
    handler = ACTION_DISPATCH.get(action_type)
    if not handler:
        return {
            "success": False,
            "action": action_type,
            "error": f"Unknown action type: {action_type}",
        }
    return handler(params)
