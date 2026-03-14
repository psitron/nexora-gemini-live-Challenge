"""
Curriculum Manager - Loads tutorial content from DynamoDB.

Retrieves tasks and metadata from the vta_curriculum table
and returns them in execution order.
"""

import json
import logging
import os
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


class CurriculumManager:
    """Loads and manages tutorial curricula from DynamoDB."""

    def __init__(self, region: str = None):
        self.region = region or REGION
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table("vta_curriculum")

    def load_tutorial(self, tutorial_id: str) -> dict:
        """
        Load a full tutorial with all tasks.

        Returns:
            {
                "tutorial_id": str,
                "title": str,
                "description": str,
                "pdf_s3_key": str,
                "tasks": [sorted list of task dicts]
            }
        """
        response = self.table.query(
            KeyConditionExpression=Key("tutorial_id").eq(tutorial_id)
        )
        items = response.get("Items", [])

        if not items:
            raise ValueError(f"Tutorial not found: {tutorial_id}")

        # Separate metadata from tasks
        meta = None
        tasks = []
        for item in items:
            if item["task_id"] == "__meta__":
                meta = item
            else:
                tasks.append(item)

        # Sort tasks by task_id (T1, T2, T3...)
        tasks.sort(key=lambda t: t["task_id"])

        # Deserialize subtasks if stored as string
        for task in tasks:
            if isinstance(task.get("subtasks"), str):
                task["subtasks"] = json.loads(task["subtasks"])

        return {
            "tutorial_id": tutorial_id,
            "title": meta.get("title", "") if meta else "",
            "description": meta.get("description", "") if meta else "",
            "pdf_s3_key": meta.get("pdf_s3_key", "") if meta else "",
            "tasks": tasks,
        }

    def load_task(self, tutorial_id: str, task_id: str) -> Optional[dict]:
        """Load a single task by ID."""
        response = self.table.get_item(
            Key={"tutorial_id": tutorial_id, "task_id": task_id}
        )
        item = response.get("Item")
        if item and isinstance(item.get("subtasks"), str):
            item["subtasks"] = json.loads(item["subtasks"])
        return item

    def list_tutorials(self) -> list[dict]:
        """List all available tutorials (metadata only)."""
        response = self.table.scan(
            FilterExpression=Key("task_id").eq("__meta__")
        )
        return response.get("Items", [])


# Fallback: load curriculum from local JSON file
class LocalCurriculumManager:
    """Loads curriculum from local JSON file (for development/testing)."""

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
        for filename in os.listdir(self.curriculum_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.curriculum_dir, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                tutorials.append({
                    "tutorial_id": data["tutorial_id"],
                    "title": data["title"],
                    "description": data.get("description", ""),
                })
        return tutorials


def get_curriculum_manager():
    """Factory: return DynamoDB manager or local fallback."""
    use_local = os.environ.get("VTA_LOCAL_CURRICULUM", "false").lower() == "true"
    if use_local:
        return LocalCurriculumManager()
    return CurriculumManager()
