"""
Confirmation Flow Handler - Yes/No/Repeat flow for student confirmations.

Uses asyncio.Event to pause the orchestrator until the student responds.
Supports both button clicks and voice-detected confirmations.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConfirmationManager:
    """Manages student confirmation flow with asyncio events."""

    def __init__(self):
        self._event: Optional[asyncio.Event] = None
        self._response: Optional[str] = None

    async def wait_for_confirmation(self, timeout: float = None) -> str:
        """
        Wait for student to respond with yes/no/repeat.

        Args:
            timeout: Optional timeout in seconds (None = wait forever)

        Returns:
            "yes", "no", or "repeat"
        """
        self._event = asyncio.Event()
        self._response = None

        if timeout:
            try:
                await asyncio.wait_for(self._event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Confirmation timeout after {timeout}s - auto-advancing with 'yes'")
                return "yes"
        else:
            # No timeout - wait indefinitely
            await self._event.wait()

        return self._response or "no"

    def receive_response(self, response: str):
        """
        Called when student responds (via button or voice).

        Args:
            response: "yes", "no", or "repeat"
        """
        valid_responses = {"yes", "no", "repeat"}
        if response not in valid_responses:
            logger.warning(f"Invalid confirmation response: {response}")
            response = "no"

        self._response = response
        if self._event:
            self._event.set()
        logger.info(f"Confirmation received: {response}")

    def has_pending_response(self) -> bool:
        """Check if a response has been received but not consumed."""
        return self._response is not None

    def get_pending_response(self) -> Optional[str]:
        """Get and clear the pending response."""
        response = self._response
        self._response = None
        return response

    def reset(self):
        """Reset confirmation state for next use."""
        self._event = None
        self._response = None
