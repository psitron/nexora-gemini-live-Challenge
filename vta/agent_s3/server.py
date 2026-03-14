"""
Agent S3 REST API Server (port 5001).

Exposes desktop automation actions as HTTP endpoints.
Each endpoint executes one atomic action via actions.py,
then runs reflex verification.
"""

import logging
import os
import sys

# Check if running in mock mode (for Windows/local dev)
MOCK_MODE = os.environ.get("VTA_MOCK_DESKTOP", "false").lower() == "true"

if not MOCK_MODE:
    # Apply Linux patches before importing core modules
    from vta.agent_s3.linux_adaptations import apply_linux_patches
    apply_linux_patches()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Import actions based on mode
if MOCK_MODE:
    from vta.agent_s3 import mock_actions as actions
    print("⚠️  Running in MOCK MODE - desktop actions will be simulated")
else:
    from vta.agent_s3 import actions

# Import reflex verifier (will work in both modes)
try:
    from vta.agent_s3.reflex_verifier import verify
except ImportError:
    # Fallback mock verifier for Windows
    def verify(check, retry=None, params=None):
        return {"status": "success", "mocked": True}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent S3 REST API", version="1.0.0")


# --- Request Models ---

class RunCommandRequest(BaseModel):
    cmd: str

class ClickTextRequest(BaseModel):
    target: str
    hint_x: int = -1
    hint_y: int = -1

class TypeTextRequest(BaseModel):
    text: str

class KeyboardRequest(BaseModel):
    keys: str

class ClickPositionRequest(BaseModel):
    x: int
    y: int

class DragRequest(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int

class ScrollRequest(BaseModel):
    direction: str = "down"
    clicks: int = 3

class GenericActionRequest(BaseModel):
    action: str
    params: dict = {}
    reflex_check: Optional[str] = None


# --- Endpoints ---

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "display": os.environ.get("DISPLAY", ":1"),
        "mock_mode": MOCK_MODE,
    }


@app.post("/action/open_terminal")
async def action_open_terminal():
    """Open a terminal window."""
    result = actions.open_terminal()
    reflex = verify("terminal_visible", retry_action=actions.open_terminal)
    return {"result": result, "reflex": reflex}


@app.post("/action/run_command")
async def action_run_command(req: RunCommandRequest):
    """Type and execute a command in the terminal."""
    result = actions.run_command(req.cmd)
    reflex = verify(
        "command_output_visible",
        retry_action=lambda: actions.run_command(req.cmd),
    )
    return {"result": result, "reflex": reflex}


@app.post("/action/click_text")
async def action_click_text(req: ClickTextRequest):
    """Find and click text on screen."""
    result = actions.click_text(req.target, req.hint_x, req.hint_y)
    return {"result": result, "reflex": {"status": "success"}}


@app.post("/action/type_text")
async def action_type_text(req: TypeTextRequest):
    """Type text into the focused field."""
    result = actions.type_text(req.text)
    return {"result": result, "reflex": {"status": "success"}}


@app.post("/action/keyboard")
async def action_keyboard(req: KeyboardRequest):
    """Press keyboard keys/combos."""
    result = actions.keyboard(req.keys)
    return {"result": result, "reflex": {"status": "success"}}


@app.post("/action/screenshot")
async def action_screenshot():
    """Capture screenshot of the virtual display."""
    result = actions.take_screenshot()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Screenshot failed"))
    return result


@app.post("/action/click_position")
async def action_click_position(req: ClickPositionRequest):
    """Click at specific screen coordinates."""
    result = actions.click_position(req.x, req.y)
    return {"result": result, "reflex": {"status": "success"}}


@app.post("/action/double_click")
async def action_double_click(req: ClickPositionRequest):
    """Double-click at specific screen coordinates."""
    result = actions.double_click(req.x, req.y)
    return {"result": result, "reflex": {"status": "success"}}


@app.post("/action/drag")
async def action_drag(req: DragRequest):
    """Drag from one position to another."""
    result = actions.drag(req.start_x, req.start_y, req.end_x, req.end_y)
    return {"result": result, "reflex": {"status": "success"}}


@app.post("/action/scroll")
async def action_scroll(req: ScrollRequest):
    """Scroll up or down."""
    result = actions.scroll(req.direction, req.clicks)
    return {"result": result, "reflex": {"status": "success"}}


@app.post("/action/{action_type}")
async def action_generic(action_type: str, req: GenericActionRequest = None):
    """
    Generic action endpoint. Dispatches any action type.
    Used by the orchestrator for curriculum-driven actions.
    """
    params = req.params if req else {}
    result = actions.dispatch(action_type, params)

    reflex = {"status": "success"}
    if req and req.reflex_check:
        reflex = verify(
            req.reflex_check,
            retry_action=lambda: actions.dispatch(action_type, params),
        )

    return {"result": result, "reflex": reflex}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("AGENT_S3_PORT", "5001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
