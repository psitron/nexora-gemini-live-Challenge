from __future__ import annotations

"""
Hybrid AI Agent – Task Planner (high-level).

Turns a natural language goal into an ordered list of execution steps.

Behaviour:
- If Anthropic (Claude) API key is configured, prefer Claude Sonnet.
- Else if Gemini API key is configured, use Gemini Flash.
- Else fall back to a simple deterministic plan.
"""

from dataclasses import dataclass
from typing import List

from config.settings import get_settings


@dataclass
class PlannedStep:
    index: int
    description: str


@dataclass
class TaskPlan:
    goal: str
    steps: List[PlannedStep]


class TaskPlanner:
    """
    High-level planner that uses an LLM when available, with a safe
    deterministic fallback.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def plan(self, goal: str) -> TaskPlan:
        # Try Anthropics first, then Gemini, then Bedrock, then fallback.
        steps: List[PlannedStep]
        steps = self._try_claude(goal)
        if not steps:
            steps = self._try_gemini(goal)
        if not steps:
            steps = self._try_bedrock(goal)
        if not steps:
            steps = self._fallback_plan(goal)
        return TaskPlan(goal=goal, steps=steps)

    def _fallback_plan(self, goal: str) -> List[PlannedStep]:
        return [
            PlannedStep(index=1, description=f"Understand goal: {goal}"),
            PlannedStep(index=2, description="Inspect current environment state."),
            PlannedStep(index=3, description="Propose next concrete UI or programmatic action."),
        ]

    def _try_claude(self, goal: str) -> List[PlannedStep]:
        api_key = self._settings.models.anthropic_api_key
        if not api_key:
            return []

        try:
            import anthropic  # type: ignore
        except Exception:
            return []

        client = anthropic.Anthropic(api_key=api_key)
        model = self._settings.models.anthropic_task_model

        prompt = (
            "You are a task planner for a hybrid AI agent that can use browser, "
            "desktop UI, and filesystem tools.\n\n"
            "Goal:\n"
            f"{goal}\n\n"
            "Return a short numbered list of high-level steps (2–6 items), "
            "each on its own line, in the format:\n"
            "1. First step\n"
            "2. Second step\n"
            "...\n"
            "Do not add any extra text before or after the list."
        )

        try:
            msg = client.messages.create(
                model=model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            return []

        # Anthropics Python SDK v1 returns a list of content blocks.
        text_parts: List[str] = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        raw = "\n".join(text_parts).strip()
        if not raw:
            return []

        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        steps: List[PlannedStep] = []
        for idx, line in enumerate(lines, start=1):
            # Strip leading "1." / "1)" etc.
            cleaned = line
            if cleaned[:2].isdigit() and (cleaned[1:2] in {".", ")"}):
                cleaned = cleaned[2:].lstrip()
            elif cleaned[:3].isdigit() and (cleaned[2:3] in {".", ")"}):
                cleaned = cleaned[3:].lstrip()
            steps.append(PlannedStep(index=idx, description=cleaned))

        return steps

    def _try_gemini(self, goal: str) -> List[PlannedStep]:
        api_key = self._settings.models.gemini_api_key
        if not api_key:
            return []

        try:
            import google.generativeai as genai  # type: ignore
        except Exception:
            return []

        genai.configure(api_key=api_key)
        model_name = self._settings.models.gemini_vision_model
        model = genai.GenerativeModel(model_name)

        prompt = (
            "You are a task planner for a hybrid AI agent that can use browser, "
            "desktop UI, and filesystem tools.\n\n"
            "Goal:\n"
            f"{goal}\n\n"
            "Return a short numbered list of high-level steps (2–6 items), "
            "each on its own line, in the format:\n"
            "1. First step\n"
            "2. Second step\n"
            "...\n"
            "Do not add any extra text before or after the list."
        )

        try:
            resp = model.generate_content(prompt)
        except Exception:
            return []

        raw = (resp.text or "").strip()
        if not raw:
            return []

        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        steps: List[PlannedStep] = []
        for idx, line in enumerate(lines, start=1):
            cleaned = line
            if cleaned[:2].isdigit() and (cleaned[1:2] in {".", ")"}):
                cleaned = cleaned[2:].lstrip()
            elif cleaned[:3].isdigit() and (cleaned[2:3] in {".", ")"}):
                cleaned = cleaned[3:].lstrip()
            steps.append(PlannedStep(index=idx, description=cleaned))

        return steps

    def _try_bedrock(self, goal: str) -> List[PlannedStep]:
        """Plan via Amazon Bedrock Converse API (any Bedrock model)."""
        try:
            from core.bedrock_client import BedrockClient
        except Exception:
            return []

        model_id = self._settings.models.bedrock_text_model_id
        region = self._settings.models.bedrock_region

        prompt = (
            "You are a task planner for a hybrid AI agent that can use browser, "
            "desktop UI, and filesystem tools.\n\n"
            "Goal:\n"
            f"{goal}\n\n"
            "Return a short numbered list of high-level steps (2–6 items), "
            "each on its own line, in the format:\n"
            "1. First step\n"
            "2. Second step\n"
            "...\n"
            "Do not add any extra text before or after the list."
        )

        try:
            client = BedrockClient(region_name=region)
            raw = client.converse_text(
                model_id=model_id,
                prompt=prompt,
                max_tokens=256,
                temperature=0.3,
            )
        except Exception:
            return []

        if not raw:
            return []

        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        steps: List[PlannedStep] = []
        for idx, line in enumerate(lines, start=1):
            cleaned = line
            if cleaned[:2].isdigit() and (cleaned[1:2] in {".", ")"}):
                cleaned = cleaned[2:].lstrip()
            elif cleaned[:3].isdigit() and (cleaned[2:3] in {".", ")"}):
                cleaned = cleaned[3:].lstrip()
            steps.append(PlannedStep(index=idx, description=cleaned))

        return steps

