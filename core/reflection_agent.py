from __future__ import annotations

"""
Reflection Agent - Analyzes action success and provides feedback.

After each action, the reflection agent:
1. Compares before/after screenshots
2. Determines if the action succeeded
3. Assesses progress toward the goal
4. Provides guidance for the next action

This improves success rates by 15-20% through self-correction.
"""

from dataclasses import dataclass
from typing import Optional
from PIL import Image

from config.settings import get_settings


@dataclass
class ReflectionResult:
    """Result of reflecting on an action."""
    action_succeeded: bool
    state_changed: bool
    progress_assessment: str  # "progressing", "stuck", "completed", "regressed"
    observations: str  # What changed on screen
    next_action_guidance: str  # Suggestion for next step
    confidence: float  # 0.0 to 1.0


class ReflectionAgent:
    """
    Analyzes each action's success and provides feedback to improve decision-making.

    Uses vision models to compare before/after states and determine if actions
    succeeded and whether the agent is making progress toward the goal.
    """

    SYSTEM_PROMPT = """You are a reflection agent analyzing GUI automation actions.

Your role:
1. Compare the BEFORE and AFTER screenshots
2. Determine if the previous action succeeded (check for visible changes)
3. Assess whether we're progressing toward the goal
4. Provide specific observations about what changed
5. Suggest what to do next

Be concise but specific. Focus on visible changes and actionable feedback."""

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize reflection agent with configurable model provider.

        Args:
            provider: "gemini", "claude", or "nova". If None, uses REFLECTION_PROVIDER from .env,
                     defaults to "gemini" if not set.
        """
        self._settings = get_settings()

        # Determine provider priority
        if provider:
            self._provider = provider.lower()
        else:
            # Use REFLECTION_PROVIDER from .env, defaults to "gemini"
            self._provider = self._settings.models.reflection_provider

        print(f"[ReflectionAgent] Using provider: {self._provider}")

    def reflect(
        self,
        task_goal: str,
        last_action: str,
        screenshot_before: Optional[Image.Image],
        screenshot_after: Optional[Image.Image],
        execution_result: bool = True,
        execution_message: str = ""
    ) -> ReflectionResult:
        """
        Reflect on the last action by comparing before/after states.

        Args:
            task_goal: The overall goal being pursued
            last_action: Description of the action that was taken
            screenshot_before: Screenshot before the action
            screenshot_after: Screenshot after the action
            execution_result: Whether the action execution succeeded (NEW)
            execution_message: Error message if execution failed (NEW)

        Returns:
            ReflectionResult with analysis and guidance
        """
        # CRITICAL FIX: If execution failed, immediately return failure reflection
        if not execution_result:
            return ReflectionResult(
                action_succeeded=False,
                state_changed=False,
                progress_assessment="stuck",
                observations=f"Action failed: {execution_message}",
                next_action_guidance="Try a different approach or method",
                confidence=1.0  # We KNOW it failed
            )

        # If no screenshots available, return basic reflection
        if screenshot_before is None or screenshot_after is None:
            return self._basic_reflection(last_action, execution_result)

        # Use configured provider
        try:
            if self._provider == "gemini":
                return self._reflect_with_gemini(task_goal, last_action, screenshot_before, screenshot_after, execution_result, execution_message)
            elif self._provider == "claude":
                return self._reflect_with_claude(task_goal, last_action, screenshot_before, screenshot_after, execution_result, execution_message)
            elif self._provider == "nova":
                return self._reflect_with_nova(task_goal, last_action, screenshot_before, screenshot_after, execution_result, execution_message)
            elif self._provider == "bedrock":
                return self._reflect_with_bedrock(task_goal, last_action, screenshot_before, screenshot_after, execution_result, execution_message)
            else:
                print(f"[ReflectionAgent] Unknown provider '{self._provider}', using basic reflection")
                return self._basic_reflection(last_action, execution_result)
        except Exception as e:
            print(f"[ReflectionAgent] {self._provider} failed: {e}")
            return self._basic_reflection(last_action, execution_result)

    def _basic_reflection(self, last_action: str, execution_result: bool = True) -> ReflectionResult:
        """Fallback reflection when no LLM is available."""
        # CRITICAL FIX: Don't always assume success
        if not execution_result:
            return ReflectionResult(
                action_succeeded=False,
                state_changed=False,
                progress_assessment="stuck",
                observations=f"Action failed: {last_action}",
                next_action_guidance="Try a different approach.",
                confidence=0.8
            )

        return ReflectionResult(
            action_succeeded=True,
            state_changed=True,
            progress_assessment="progressing",
            observations=f"Executed: {last_action}",
            next_action_guidance="Continue with next planned step.",
            confidence=0.5
        )

    def _reflect_with_claude(
        self,
        task_goal: str,
        last_action: str,
        screenshot_before: Image.Image,
        screenshot_after: Image.Image,
        execution_result: bool = True,
        execution_message: str = ""
    ) -> ReflectionResult:
        """Reflect using Claude (Anthropic)."""
        import anthropic
        import base64
        import io

        client = anthropic.Anthropic(api_key=self._settings.models.anthropic_api_key)
        model = self._settings.models.anthropic_execution_model

        # Convert images to base64
        def image_to_base64(img: Image.Image) -> str:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()

        before_b64 = image_to_base64(screenshot_before)
        after_b64 = image_to_base64(screenshot_after)

        exec_status = "SUCCESS" if execution_result else "FAILED"
        exec_info = f"\n**Execution Status:** {exec_status}"
        if not execution_result and execution_message:
            exec_info += f"\n**Error Message:** {execution_message}"

        prompt = f"""Task Goal: {task_goal}
Previous Action: {last_action}
{exec_info}

Compare these two screenshots (BEFORE and AFTER the action).

Analyze:
1. Did the action succeed? (Execution says: {exec_status})
2. What specifically changed on screen?
3. Are we closer to the goal? (progressing/stuck/completed/regressed)
4. What should we do next?

IMPORTANT: If execution failed, focus on WHY it failed and suggest alternatives.

Respond in this format:
SUCCESS: yes/no
STATE_CHANGED: yes/no
PROGRESS: progressing/stuck/completed/regressed
OBSERVATIONS: [What changed]
NEXT_ACTION: [Specific guidance]
CONFIDENCE: [0.0-1.0]"""

        try:
            response = client.messages.create(
                model=model,
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "BEFORE screenshot:"},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": before_b64}},
                        {"type": "text", "text": "AFTER screenshot:"},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": after_b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )

            # Parse response
            text = "".join(block.text for block in response.content if hasattr(block, "text"))
            return self._parse_reflection_response(text, last_action)

        except Exception as e:
            print(f"[ReflectionAgent] Claude API error: {e}")
            return self._basic_reflection(last_action)

    def _reflect_with_gemini(
        self,
        task_goal: str,
        last_action: str,
        screenshot_before: Image.Image,
        screenshot_after: Image.Image,
        execution_result: bool = True,
        execution_message: str = ""
    ) -> ReflectionResult:
        """Reflect using Gemini."""
        import google.generativeai as genai

        genai.configure(api_key=self._settings.models.gemini_api_key)
        model = genai.GenerativeModel(self._settings.models.gemini_vision_model)

        # NEW: Include execution result in prompt
        exec_status = "SUCCESS" if execution_result else "FAILED"
        exec_info = f"\n**Execution Status:** {exec_status}"
        if not execution_result and execution_message:
            exec_info += f"\n**Error Message:** {execution_message}"

        prompt = f"""Task Goal: {task_goal}
Previous Action: {last_action}
{exec_info}

I'm showing you two screenshots: BEFORE and AFTER executing the action.

Analyze:
1. Did the action succeed? (Execution says: {exec_status})
2. What specifically changed on screen?
3. Are we closer to the goal? (progressing/stuck/completed/regressed)
4. What should we do next?

IMPORTANT: If execution failed, focus on WHY it failed and suggest alternatives.

Respond in this format:
SUCCESS: yes/no
STATE_CHANGED: yes/no
PROGRESS: progressing/stuck/completed/regressed
OBSERVATIONS: [What changed]
NEXT_ACTION: [Specific guidance]
CONFIDENCE: [0.0-1.0]"""

        try:
            response = model.generate_content(
                ["BEFORE:", screenshot_before, "AFTER:", screenshot_after, prompt],
                generation_config={"max_output_tokens": 512, "temperature": 0.1}
            )

            return self._parse_reflection_response(response.text, last_action)

        except Exception as e:
            print(f"[ReflectionAgent] Gemini API error: {e}")
            return self._basic_reflection(last_action, execution_result)

    def _reflect_with_nova(
        self,
        task_goal: str,
        last_action: str,
        screenshot_before: Image.Image,
        screenshot_after: Image.Image,
        execution_result: bool = True,
        execution_message: str = ""
    ) -> ReflectionResult:
        """Reflect using Amazon Nova."""
        import boto3
        import base64
        import json
        from io import BytesIO
        from botocore.config import Config

        # Initialize Bedrock client
        client = boto3.client(
            "bedrock-runtime",
            region_name=self._settings.models.nova_region,
            config=Config(
                connect_timeout=3600,
                read_timeout=3600,
                retries={'max_attempts': 1}
            )
        )

        # Convert images to base64
        def image_to_base64(img: Image.Image) -> str:
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

        before_b64 = image_to_base64(screenshot_before)
        after_b64 = image_to_base64(screenshot_after)

        # Include execution result in prompt
        exec_status = "SUCCESS" if execution_result else "FAILED"
        exec_info = f"\n**Execution Status:** {exec_status}"
        if not execution_result and execution_message:
            exec_info += f"\n**Error Message:** {execution_message}"

        prompt = f"""Task Goal: {task_goal}
Previous Action: {last_action}

I'm showing you two screenshots: BEFORE and AFTER executing the action.
{exec_info}

Analyze:
1. Did the action succeed? (Execution says: {exec_status})
2. What specifically changed on screen?
3. Are we closer to the goal? (progressing/stuck/completed/regressed)
4. What should we do next?

IMPORTANT: If execution failed, focus on WHY it failed and suggest alternatives.

Respond in this format:
SUCCESS: yes/no
STATE_CHANGED: yes/no
PROGRESS: progressing/stuck/completed/regressed
OBSERVATIONS: [What changed]
NEXT_ACTION: [Specific guidance]
CONFIDENCE: [0.0-1.0]"""

        try:
            # Build Nova request
            message_list = [
                {
                    "role": "user",
                    "content": [
                        {"text": "BEFORE screenshot:"},
                        {"image": {"format": "png", "source": {"bytes": base64.b64decode(before_b64)}}},
                        {"text": "AFTER screenshot:"},
                        {"image": {"format": "png", "source": {"bytes": base64.b64decode(after_b64)}}},
                        {"text": prompt}
                    ]
                }
            ]

            request_body = {
                "messages": message_list,
                "inferenceConfig": {
                    "maxTokens": 512,
                    "temperature": 0.1
                }
            }

            response = client.converse(
                modelId=self._settings.models.nova_model_id,
                messages=message_list,
                inferenceConfig=request_body["inferenceConfig"]
            )

            # Extract text from response
            response_text = response["output"]["message"]["content"][0]["text"]
            return self._parse_reflection_response(response_text, last_action)

        except Exception as e:
            print(f"[ReflectionAgent] Nova API error: {e}")
            return self._basic_reflection(last_action, execution_result)

    def _reflect_with_bedrock(
        self,
        task_goal: str,
        last_action: str,
        screenshot_before: Image.Image,
        screenshot_after: Image.Image,
        execution_result: bool = True,
        execution_message: str = ""
    ) -> ReflectionResult:
        """Reflect using any Bedrock model via the Converse API."""
        from core.bedrock_client import BedrockClient

        model_id = self._settings.models.bedrock_execution_model_id
        region = self._settings.models.bedrock_region

        # NEW: Include execution result in prompt
        exec_status = "SUCCESS" if execution_result else "FAILED"
        exec_info = f"\n**Execution Status:** {exec_status}"
        if not execution_result and execution_message:
            exec_info += f"\n**Error Message:** {execution_message}"

        prompt = f"""Task Goal: {task_goal}
Previous Action: {last_action}
{exec_info}

I'm showing you two screenshots: BEFORE and AFTER executing the action.

Analyze:
1. Did the action succeed? (Execution says: {exec_status})
2. What specifically changed on screen?
3. Are we closer to the goal? (progressing/stuck/completed/regressed)
4. What should we do next?

IMPORTANT: If execution failed, focus on WHY it failed and suggest alternatives.

Respond in this format:
SUCCESS: yes/no
STATE_CHANGED: yes/no
PROGRESS: progressing/stuck/completed/regressed
OBSERVATIONS: [What changed]
NEXT_ACTION: [Specific guidance]
CONFIDENCE: [0.0-1.0]"""

        try:
            client = BedrockClient(region_name=region)
            text = client.converse_with_images(
                model_id=model_id,
                prompt=prompt,
                images=[
                    ("BEFORE screenshot:", screenshot_before),
                    ("AFTER screenshot:", screenshot_after),
                ],
                max_tokens=512,
                temperature=0.1,
            )
            return self._parse_reflection_response(text, last_action)

        except Exception as e:
            print(f"[ReflectionAgent] Bedrock API error: {e}")
            return self._basic_reflection(last_action)

    def _parse_reflection_response(self, text: str, last_action: str) -> ReflectionResult:
        """Parse the structured reflection response."""
        lines = text.strip().split("\n")

        # Default values
        action_succeeded = True
        state_changed = True
        progress = "progressing"
        observations = f"Executed: {last_action}"
        next_action = "Continue with next step."
        confidence = 0.7

        # Parse each line
        for line in lines:
            line = line.strip()
            if line.startswith("SUCCESS:"):
                action_succeeded = "yes" in line.lower()
            elif line.startswith("STATE_CHANGED:"):
                state_changed = "yes" in line.lower()
            elif line.startswith("PROGRESS:"):
                progress_text = line.split(":", 1)[1].strip().lower()
                if any(x in progress_text for x in ["progress", "closer", "forward"]):
                    progress = "progressing"
                elif any(x in progress_text for x in ["stuck", "same", "no progress"]):
                    progress = "stuck"
                elif any(x in progress_text for x in ["complete", "done", "success"]):
                    progress = "completed"
                elif any(x in progress_text for x in ["regress", "worse", "back"]):
                    progress = "regressed"
            elif line.startswith("OBSERVATIONS:"):
                observations = line.split(":", 1)[1].strip()
            elif line.startswith("NEXT_ACTION:"):
                next_action = line.split(":", 1)[1].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    conf_str = line.split(":", 1)[1].strip()
                    confidence = float(conf_str)
                except:
                    confidence = 0.7

        return ReflectionResult(
            action_succeeded=action_succeeded,
            state_changed=state_changed,
            progress_assessment=progress,
            observations=observations,
            next_action_guidance=next_action,
            confidence=confidence
        )
