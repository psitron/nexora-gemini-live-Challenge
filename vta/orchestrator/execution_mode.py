"""
Execution Mode Configuration for VTA.

Three modes control how the orchestrator sequences narration and actions:

- DEMO_ONLY: Student watches the demo. Batched narration + execution.
- FOLLOW_ALONG_REALTIME: Student follows in real-time. Quick pacing.
- FOLLOW_ALONG_PACED: Demo then per-subtask confirmation from student.

Mode logic is in orchestrator.py — this module only defines the config.
"""

import logging
import os
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    DEMO_ONLY = "demo_only"
    FOLLOW_ALONG_REALTIME = "follow_along_realtime"
    FOLLOW_ALONG_PACED = "follow_along_paced"


class ExecutionConfig:
    """Timing and behavior configuration for each execution mode."""

    def __init__(self, mode: ExecutionMode):
        self.mode = mode

        if mode == ExecutionMode.DEMO_ONLY:
            self.subtask_confirmation = False
            self.task_confirmation = True

        elif mode == ExecutionMode.FOLLOW_ALONG_REALTIME:
            self.subtask_confirmation = False
            self.task_confirmation = True

        elif mode == ExecutionMode.FOLLOW_ALONG_PACED:
            self.subtask_confirmation = True
            self.task_confirmation = True


def get_execution_config(mode_str: str = None) -> ExecutionConfig:
    """Create an ExecutionConfig from a mode string or environment variable."""
    if not mode_str:
        mode_str = os.environ.get("VTA_EXECUTION_MODE", "demo_only")

    try:
        mode = ExecutionMode(mode_str)
    except ValueError:
        logger.warning(f"Unknown execution mode '{mode_str}', defaulting to demo_only")
        mode = ExecutionMode.DEMO_ONLY

    config = ExecutionConfig(mode)
    logger.info(f"Execution mode: {config.mode.value}")
    return config
