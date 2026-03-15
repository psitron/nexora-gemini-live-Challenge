"""
Agent S3 HTTP Client - Async client for the Agent S3 REST API.

Used by the orchestrator to dispatch UI actions to the Agent S3
server running on port 5001.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:5001"
DEFAULT_TIMEOUT = 30.0


class AgentS3Client:
    """Async HTTP client for Agent S3 REST API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def run(
        self,
        action: str,
        params: dict = None,
        reflex_check: Optional[str] = None,
        subtask_id: Optional[str] = None,
    ) -> dict:
        """
        Execute a UI action via Agent S3.

        Args:
            action: Action type (open_terminal, run_command, etc.)
            params: Action parameters
            reflex_check: Optional reflex check to run after action
            subtask_id: Optional subtask ID for tracking

        Returns:
            {"result": {...}, "reflex": {"status": "success"|"failed"}}
        """
        client = await self._get_client()
        params = params or {}

        try:
            # Send params directly as the request body.
            # Specific endpoints (run_command, click_text, etc.) expect
            # their own Pydantic models, not a wrapped payload.
            response = await client.post(
                f"/action/{action}",
                json=params,
            )
            response.raise_for_status()
            result = response.json()

            logger.info(
                f"Agent S3 action '{action}' "
                f"{'succeeded' if result.get('result', {}).get('success') else 'failed'}"
            )
            return result

        except httpx.TimeoutException:
            logger.error(f"Agent S3 timeout for action '{action}'")
            return {
                "result": {"success": False, "error": "Timeout"},
                "reflex": {"status": "failed", "reason": "timeout"},
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Agent S3 HTTP error: {e.response.status_code}")
            return {
                "result": {"success": False, "error": str(e)},
                "reflex": {"status": "failed", "reason": str(e)},
            }
        except Exception as e:
            logger.error(f"Agent S3 client error: {e}")
            return {
                "result": {"success": False, "error": str(e)},
                "reflex": {"status": "failed", "reason": str(e)},
            }

    async def health(self) -> dict:
        """Check Agent S3 health."""
        client = await self._get_client()
        try:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def screenshot(self) -> dict:
        """Capture a screenshot from the virtual display."""
        client = await self._get_client()
        try:
            response = await client.post("/action/screenshot")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def reset_desktop(self) -> dict:
        """
        Reset the Linux desktop to a clean state by killing user-spawned
        applications (terminals, browsers, file managers, editors).
        """
        reset_script = (
            "pkill -f xfce4-terminal 2>/dev/null; "
            "pkill -f gnome-terminal 2>/dev/null; "
            "pkill -f xterm 2>/dev/null; "
            "pkill -f bash 2>/dev/null; "
            "pkill -f chromium 2>/dev/null; "
            "pkill -f chrome 2>/dev/null; "
            "pkill -f firefox 2>/dev/null; "
            "pkill -f nautilus 2>/dev/null; "
            "pkill -f thunar 2>/dev/null; "
            "pkill -f nemo 2>/dev/null; "
            "pkill -f gedit 2>/dev/null; "
            "pkill -f mousepad 2>/dev/null; "
            "pkill -f code 2>/dev/null; "
            "wmctrl -l 2>/dev/null | awk '{print $1}' | xargs -I{} wmctrl -ic {} 2>/dev/null; "
            "true"
        )
        logger.info("Resetting Linux desktop — closing all user applications")
        try:
            result = await self.run(action="run_command", params={"cmd": reset_script})
            logger.info(f"Desktop reset result: {result}")
            return result
        except Exception as e:
            logger.warning(f"Desktop reset failed (non-fatal): {e}")
            return {"result": {"success": False, "error": str(e)}}

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
