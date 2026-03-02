from __future__ import annotations

"""
Trajectory Manager - Manages action history with image flushing.

Keeps a rolling window of recent screenshots while preserving full text history.
This prevents context window overflow while maintaining decision-making context.

Key features:
- Keeps last N screenshots (default: 8)
- Keeps ALL text descriptions of actions
- Automatically flushes old images
- Provides formatted context for LLM prompts
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from PIL import Image


@dataclass
class TrajectoryStep:
    """A single step in the execution trajectory."""
    step_number: int
    action_description: str
    screenshot_before: Optional[Image.Image] = None
    screenshot_after: Optional[Image.Image] = None
    outcome: str = "unknown"  # "success", "failure", "unknown"
    observations: str = ""


class TrajectoryManager:
    """
    Manages execution trajectory with automatic image flushing.

    Keeps recent screenshots for visual context while preserving complete
    text history of all actions taken.
    """

    def __init__(self, max_images: int = 8):
        """
        Initialize trajectory manager.

        Args:
            max_images: Maximum number of screenshots to keep in memory
        """
        self.max_images = max_images
        self._steps: List[TrajectoryStep] = []

    def add_step(
        self,
        step_number: int,
        action_description: str,
        screenshot_before: Optional[Image.Image] = None,
        screenshot_after: Optional[Image.Image] = None,
        outcome: str = "unknown",
        observations: str = ""
    ) -> None:
        """
        Add a step to the trajectory.

        Args:
            step_number: Sequential step number
            action_description: Human-readable description of the action
            screenshot_before: Optional screenshot before action
            screenshot_after: Optional screenshot after action
            outcome: "success", "failure", or "unknown"
            observations: Any observations about the step
        """
        step = TrajectoryStep(
            step_number=step_number,
            action_description=action_description,
            screenshot_before=screenshot_before,
            screenshot_after=screenshot_after,
            outcome=outcome,
            observations=observations
        )

        self._steps.append(step)
        self._flush_old_images()

    def _flush_old_images(self) -> None:
        """
        Keep only the most recent N screenshots.

        Flushes old screenshots while preserving text descriptions.
        """
        # Count total images (both before and after screenshots)
        image_count = 0
        for step in reversed(self._steps):
            if step.screenshot_before is not None:
                image_count += 1
            if step.screenshot_after is not None:
                image_count += 1

            # If we're within limit, stop counting
            if image_count <= self.max_images:
                continue

            # Beyond limit - flush images from this step
            if image_count > self.max_images and step.screenshot_before is not None:
                step.screenshot_before = None
                image_count -= 1

            if image_count > self.max_images and step.screenshot_after is not None:
                step.screenshot_after = None
                image_count -= 1

    def get_text_summary(self, last_n_steps: Optional[int] = None) -> str:
        """
        Get text summary of trajectory.

        Returns text description of all steps (or last N steps) without images.
        This can be included in LLM prompts without consuming image tokens.

        Args:
            last_n_steps: If specified, only return last N steps

        Returns:
            Formatted text summary
        """
        if not self._steps:
            return "No steps executed yet."

        steps_to_include = self._steps[-last_n_steps:] if last_n_steps else self._steps

        lines = [f"Execution History ({len(steps_to_include)} steps):"]
        for step in steps_to_include:
            outcome_symbol = {
                "success": "✓",
                "failure": "✗",
                "unknown": "?"
            }.get(step.outcome, "?")

            lines.append(f"  {step.step_number}. {outcome_symbol} {step.action_description}")
            if step.observations:
                lines.append(f"     → {step.observations}")

        return "\n".join(lines)

    def get_recent_images(self) -> List[Tuple[int, Image.Image, str]]:
        """
        Get list of recent images with metadata.

        Returns:
            List of (step_number, image, description) tuples
        """
        images = []
        for step in self._steps:
            if step.screenshot_before is not None:
                images.append((step.step_number, step.screenshot_before, f"Before: {step.action_description}"))
            if step.screenshot_after is not None:
                images.append((step.step_number, step.screenshot_after, f"After: {step.action_description}"))

        # Return only the most recent max_images
        return images[-self.max_images:]

    def get_step_count(self) -> int:
        """Get total number of steps in trajectory."""
        return len(self._steps)

    def get_last_step(self) -> Optional[TrajectoryStep]:
        """Get the most recent step, or None if trajectory is empty."""
        return self._steps[-1] if self._steps else None

    def clear(self) -> None:
        """Clear all trajectory data. Call when starting a new task."""
        self._steps.clear()

    def get_image_count(self) -> int:
        """Get count of images currently in memory."""
        count = 0
        for step in self._steps:
            if step.screenshot_before is not None:
                count += 1
            if step.screenshot_after is not None:
                count += 1
        return count

    def get_full_context(self) -> dict:
        """
        Get complete trajectory context for decision-making.

        Returns:
            Dictionary with text_summary, recent_images, and statistics
        """
        return {
            "text_summary": self.get_text_summary(),
            "recent_images": self.get_recent_images(),
            "total_steps": self.get_step_count(),
            "images_in_memory": self.get_image_count(),
            "last_step": self.get_last_step()
        }
