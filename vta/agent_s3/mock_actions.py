"""
Mock actions for local development on Windows.

Returns success for all actions without actually executing them.
Useful for testing orchestrator + frontend without Linux desktop.
"""

import logging
import time
import base64
import io
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def _create_mock_screenshot(text: str = "Mock Desktop") -> str:
    """Create a fake screenshot image."""
    img = Image.new('RGB', (1280, 800), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)

    # Draw some fake UI elements
    draw.rectangle([50, 50, 1230, 750], outline=(100, 100, 120), width=2)

    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (1280 - text_width) // 2
    y = (800 - text_height) // 2
    draw.text((x, y), text, fill=(200, 200, 220), font=font)

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def open_terminal() -> dict:
    """Mock: Open terminal."""
    logger.info("[MOCK] Opening terminal")
    time.sleep(0.5)
    return {"success": True, "action": "open_terminal", "mocked": True}


def run_command(cmd: str) -> dict:
    """Mock: Run command."""
    logger.info(f"[MOCK] Running command: {cmd}")
    time.sleep(0.3)
    return {"success": True, "action": "run_command", "cmd": cmd, "mocked": True}


def click_text(target: str, hint_x: int = -1, hint_y: int = -1) -> dict:
    """Mock: Click text."""
    logger.info(f"[MOCK] Clicking text: {target}")
    time.sleep(0.2)
    return {
        "success": True,
        "action": "click_text",
        "target": target,
        "x": hint_x if hint_x >= 0 else 640,
        "y": hint_y if hint_y >= 0 else 400,
        "mocked": True,
    }


def type_text(text: str) -> dict:
    """Mock: Type text."""
    logger.info(f"[MOCK] Typing text: {text[:50]}...")
    time.sleep(0.2)
    return {"success": True, "action": "type_text", "text": text, "mocked": True}


def keyboard(keys: str) -> dict:
    """Mock: Press keyboard keys."""
    logger.info(f"[MOCK] Pressing keys: {keys}")
    time.sleep(0.1)
    return {"success": True, "action": "keyboard", "keys": keys, "mocked": True}


def take_screenshot() -> dict:
    """Mock: Take screenshot."""
    logger.info("[MOCK] Taking screenshot")
    img_b64 = _create_mock_screenshot("VTA Mock Desktop")
    return {
        "success": True,
        "action": "screenshot",
        "image": img_b64,
        "width": 1280,
        "height": 800,
        "mocked": True,
    }


def click_position(x: int, y: int) -> dict:
    """Mock: Click position."""
    logger.info(f"[MOCK] Clicking position: ({x}, {y})")
    time.sleep(0.2)
    return {"success": True, "action": "click_position", "x": x, "y": y, "mocked": True}


def double_click(x: int, y: int) -> dict:
    """Mock: Double-click."""
    logger.info(f"[MOCK] Double-clicking: ({x}, {y})")
    time.sleep(0.2)
    return {"success": True, "action": "double_click", "x": x, "y": y, "mocked": True}


def drag(start_x: int, start_y: int, end_x: int, end_y: int) -> dict:
    """Mock: Drag."""
    logger.info(f"[MOCK] Dragging: ({start_x}, {start_y}) → ({end_x}, {end_y})")
    time.sleep(0.3)
    return {
        "success": True,
        "action": "drag",
        "start": (start_x, start_y),
        "end": (end_x, end_y),
        "mocked": True,
    }


def scroll(direction: str = "down", clicks: int = 3) -> dict:
    """Mock: Scroll."""
    logger.info(f"[MOCK] Scrolling {direction}")
    time.sleep(0.1)
    return {"success": True, "action": "scroll", "direction": direction, "mocked": True}


# Action dispatch table (same interface as real actions)
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
    """Dispatch an action by type (mock version)."""
    handler = ACTION_DISPATCH.get(action_type)
    if not handler:
        return {
            "success": False,
            "action": action_type,
            "error": f"Unknown action type: {action_type}",
            "mocked": True,
        }
    return handler(params)
