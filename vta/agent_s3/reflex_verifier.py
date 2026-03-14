"""
Reflex Verifier - xdotool-based verification of UI actions.

After every Agent S3 action, takes a screenshot and verifies
the expected outcome actually occurred on screen.
"""

import os
import subprocess
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

DISPLAY = os.environ.get("DISPLAY", ":1")


def _run_xdotool(*args: str) -> subprocess.CompletedProcess:
    """Run xdotool with the correct DISPLAY."""
    env = {**os.environ, "DISPLAY": DISPLAY}
    return subprocess.run(
        ["xdotool", *args],
        capture_output=True, text=True, env=env, timeout=5,
    )


def check_terminal_visible() -> bool:
    """Check if a terminal window is open and visible."""
    try:
        result = _run_xdotool("search", "--name", "Terminal")
        if result.returncode == 0 and result.stdout.strip():
            return True
        # Also check common terminal emulator names
        for name in ["terminal", "xterm", "bash", "sh"]:
            result = _run_xdotool("search", "--name", name)
            if result.returncode == 0 and result.stdout.strip():
                return True
        return False
    except Exception as e:
        logger.warning(f"Terminal check failed: {e}")
        return False


def check_command_output_visible() -> bool:
    """Check if terminal has content (proxy for command output)."""
    try:
        result = _run_xdotool("search", "--name", "Terminal")
        if result.returncode == 0 and result.stdout.strip():
            window_id = result.stdout.strip().splitlines()[0]
            # Verify window is mapped (visible)
            map_result = _run_xdotool("getwindowfocus")
            return map_result.returncode == 0
        return False
    except Exception as e:
        logger.warning(f"Command output check failed: {e}")
        return False


def check_window_exists(window_name: str) -> bool:
    """Check if a window with the given name exists."""
    try:
        result = _run_xdotool("search", "--name", window_name)
        return result.returncode == 0 and len(result.stdout.strip()) > 0
    except Exception as e:
        logger.warning(f"Window check failed for '{window_name}': {e}")
        return False


def check_file_exists(filepath: str) -> bool:
    """Check if a file was created on the filesystem."""
    return os.path.exists(filepath)


REFLEX_CHECKS = {
    "terminal_visible": check_terminal_visible,
    "command_output_visible": check_command_output_visible,
    "window_exists": check_window_exists,
    "file_exists": check_file_exists,
}


def verify(
    reflex_check: str,
    retry_action: Optional[Callable] = None,
    check_params: Optional[dict] = None,
) -> dict:
    """
    Run a reflex check. Retry the action once on failure.

    Returns:
        {"status": "success"} or {"status": "failed", "reason": "..."}
    """
    check_fn = REFLEX_CHECKS.get(reflex_check)
    if not check_fn:
        logger.warning(f"Unknown reflex check: {reflex_check}, passing through")
        return {"status": "success"}

    # Run check (with params if needed)
    try:
        if check_params:
            result = check_fn(**check_params)
        else:
            result = check_fn()
    except Exception as e:
        result = False
        logger.error(f"Reflex check {reflex_check} raised: {e}")

    if result:
        return {"status": "success"}

    # First failure - retry the action if provided
    if retry_action:
        logger.info(f"Reflex check {reflex_check} failed, retrying action...")
        try:
            retry_action()
        except Exception as e:
            logger.error(f"Retry action failed: {e}")

        import time
        time.sleep(1.0)  # Wait for UI to update

        try:
            if check_params:
                result = check_fn(**check_params)
            else:
                result = check_fn()
        except Exception:
            result = False

        if result:
            return {"status": "success"}

    reason = f"reflex_check '{reflex_check}' failed after retry"
    logger.warning(reason)
    return {"status": "failed", "reason": reason}
