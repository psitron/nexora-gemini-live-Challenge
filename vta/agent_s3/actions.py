"""
Linux-adapted action dispatch for Agent S3.

Wraps VisionAgent's action methods for use on Xvfb/Linux.
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

DISPLAY = os.environ.get("DISPLAY", ":1")

# Configure pyautogui for headless Linux
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1


def _get_display_env() -> dict:
    """Return env dict with correct DISPLAY."""
    return {**os.environ, "DISPLAY": DISPLAY}


def open_terminal() -> dict:
    """Open XFCE terminal on the virtual display."""
    try:
        subprocess.Popen(
            ["xfce4-terminal"],
            env=_get_display_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)  # Wait for terminal to appear
        return {"success": True, "action": "open_terminal"}
    except FileNotFoundError:
        # Fallback to other terminals
        for terminal in ["gnome-terminal", "xterm", "lxterminal"]:
            try:
                subprocess.Popen(
                    [terminal],
                    env=_get_display_env(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(1.5)
                return {"success": True, "action": "open_terminal", "terminal": terminal}
            except FileNotFoundError:
                continue
        return {"success": False, "action": "open_terminal", "error": "No terminal found"}


def run_command(cmd: str) -> dict:
    """Type a command in the active terminal and press Enter."""
    try:
        # Ensure terminal is focused
        env = _get_display_env()
        subprocess.run(
            ["xdotool", "search", "--name", "Terminal", "windowactivate"],
            env=env, capture_output=True, timeout=3,
        )
        time.sleep(0.3)

        # Type the command using xdotool for better Linux compatibility
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "50", cmd],
            env=env, capture_output=True, timeout=10,
        )
        time.sleep(0.2)

        # Press Enter
        subprocess.run(
            ["xdotool", "key", "Return"],
            env=env, capture_output=True, timeout=3,
        )
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
        # Try using grounding agent for precise detection
        click_x, click_y = _find_text_coordinates(target, hint_x, hint_y)
        if click_x is not None:
            _smooth_click(click_x, click_y)
            return {
                "success": True, "action": "click_text",
                "target": target, "x": click_x, "y": click_y,
            }

        # Fall back to hint coordinates
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
    """Type text into the currently focused field."""
    try:
        env = _get_display_env()
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "30", text],
            env=env, capture_output=True, timeout=30,
        )
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
        env = _get_display_env()
        # Convert common key names to xdotool format
        xdotool_keys = _translate_keys(keys)
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", xdotool_keys],
            env=env, capture_output=True, timeout=5,
        )
        return {"success": True, "action": "keyboard", "keys": keys}
    except Exception as e:
        logger.error(f"keyboard failed: {e}")
        return {"success": False, "action": "keyboard", "error": str(e)}


def take_screenshot() -> dict:
    """Capture screenshot of the virtual display."""
    try:
        import mss

        with mss.mss() as sct:
            # On Linux with Xvfb, monitor 0 is the full virtual display
            monitors = sct.monitors
            if len(monitors) > 1:
                monitor = monitors[1]
            else:
                monitor = monitors[0]

            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        # Convert to base64
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


def _translate_keys(keys: str) -> str:
    """Translate common key names to xdotool format."""
    mapping = {
        "enter": "Return",
        "return": "Return",
        "tab": "Tab",
        "escape": "Escape",
        "esc": "Escape",
        "backspace": "BackSpace",
        "delete": "Delete",
        "space": "space",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
        "home": "Home",
        "end": "End",
        "pageup": "Prior",
        "pagedown": "Next",
        "ctrl": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "super": "super",
        "win": "super",
    }

    parts = keys.lower().replace(" ", "").split("+")
    translated = []
    for part in parts:
        translated.append(mapping.get(part, part))
    return "+".join(translated)


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
