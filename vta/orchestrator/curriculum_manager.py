"""
Curriculum Manager - Loads tutorial content from local JSON files.

Scans the curriculum directory for JSON files and matches by tutorial_id.
Supports dynamically uploaded tutorials.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class CurriculumManager:
    """Loads curriculum from local JSON files."""

    def __init__(self, curriculum_dir: str = None):
        self.curriculum_dir = curriculum_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "curriculum"
        )

    def load_tutorial(self, tutorial_id: str) -> dict:
        """Load tutorial from local JSON file."""
        logger.info(f"Loading tutorial '{tutorial_id}' from local directory: {self.curriculum_dir}")

        if not os.path.exists(self.curriculum_dir):
            raise ValueError(f"Curriculum directory not found: {self.curriculum_dir}")

        # Try to find matching file
        for filename in os.listdir(self.curriculum_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.curriculum_dir, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                if data.get("tutorial_id") == tutorial_id:
                    logger.info(f"Successfully loaded tutorial from {filename}")
                    return data

        # List available tutorials for better error message
        available = [f for f in os.listdir(self.curriculum_dir) if f.endswith(".json")]
        raise ValueError(
            f"Tutorial '{tutorial_id}' not found locally. "
            f"Available files in {self.curriculum_dir}: {available}"
        )

    def load_task(self, tutorial_id: str, task_id: str) -> Optional[dict]:
        tutorial = self.load_tutorial(tutorial_id)
        for task in tutorial.get("tasks", []):
            if task["task_id"] == task_id:
                return task
        return None

    def list_tutorials(self) -> list[dict]:
        tutorials = []
        if not os.path.exists(self.curriculum_dir):
            return tutorials
        for filename in os.listdir(self.curriculum_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.curriculum_dir, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                tutorials.append({
                    "tutorial_id": data.get("tutorial_id", filename.replace(".json", "")),
                    "title": data.get("title", filename),
                    "description": data.get("description", ""),
                })
        return tutorials


# Keep backward compatibility
LocalCurriculumManager = CurriculumManager


def get_curriculum_manager():
    """Return the curriculum manager (always local now)."""
    return CurriculumManager()
