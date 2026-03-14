"""
Session State Manager - DynamoDB-backed session and task state tracking.

Tracks per-session task completion status with state transitions:
pending → running → awaiting_confirmation → completed
                 └→ failed
                 └→ replaying → awaiting_confirmation
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


class SessionStateManager:
    """Manages session and task state in DynamoDB."""

    def __init__(self, region: str = None):
        self.region = region or REGION
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.state_table = self.dynamodb.Table("vta_session_state")
        self.sessions_table = self.dynamodb.Table("vta_sessions")

    async def create_session(
        self, session_id: str, tutorial_id: str, student_id: str,
    ):
        """Create a new tutorial session."""
        self.sessions_table.put_item(Item={
            "session_id": session_id,
            "tutorial_id": tutorial_id,
            "student_id": student_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        })
        logger.info(f"Created session {session_id}")

    async def update_state(
        self,
        session_id: str,
        task_id: str,
        subtask_id: Optional[str],
        status: str,
    ):
        """Update task/subtask state."""
        sort_key = f"{task_id}#{subtask_id or 'null'}"
        self.state_table.put_item(Item={
            "session_id": session_id,
            "task_sort_key": sort_key,
            "task_id": task_id,
            "subtask_id": subtask_id,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.debug(f"State: {session_id}/{sort_key} → {status}")

    async def get_task_state(
        self,
        session_id: str,
        task_id: str,
        subtask_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Get current state of a task/subtask."""
        sort_key = f"{task_id}#{subtask_id or 'null'}"
        response = self.state_table.get_item(
            Key={"session_id": session_id, "task_sort_key": sort_key}
        )
        return response.get("Item")

    async def get_all_session_state(self, session_id: str) -> list[dict]:
        """Get all task states for a session."""
        response = self.state_table.query(
            KeyConditionExpression=Key("session_id").eq(session_id)
        )
        return response.get("Items", [])

    async def end_session(self, session_id: str):
        """Mark session as completed."""
        self.sessions_table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET #s = :s, ended_at = :t",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "completed",
                ":t": datetime.now(timezone.utc).isoformat(),
            },
        )


class InMemorySessionState:
    """In-memory session state for development/testing."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}
        self.states: dict[str, dict[str, dict]] = {}

    async def create_session(
        self, session_id: str, tutorial_id: str, student_id: str,
    ):
        self.sessions[session_id] = {
            "session_id": session_id,
            "tutorial_id": tutorial_id,
            "student_id": student_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        self.states[session_id] = {}

    async def update_state(
        self,
        session_id: str,
        task_id: str,
        subtask_id: Optional[str],
        status: str,
    ):
        sort_key = f"{task_id}#{subtask_id or 'null'}"
        if session_id not in self.states:
            self.states[session_id] = {}
        self.states[session_id][sort_key] = {
            "session_id": session_id,
            "task_sort_key": sort_key,
            "task_id": task_id,
            "subtask_id": subtask_id,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_task_state(
        self,
        session_id: str,
        task_id: str,
        subtask_id: Optional[str] = None,
    ) -> Optional[dict]:
        sort_key = f"{task_id}#{subtask_id or 'null'}"
        return self.states.get(session_id, {}).get(sort_key)

    async def get_all_session_state(self, session_id: str) -> list[dict]:
        return list(self.states.get(session_id, {}).values())

    async def end_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "completed"


def get_session_state_manager():
    """Factory: return DynamoDB or in-memory state manager."""
    use_local = os.environ.get("VTA_LOCAL_STATE", "false").lower() == "true"
    if use_local:
        return InMemorySessionState()
    return SessionStateManager()
