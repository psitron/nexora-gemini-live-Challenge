"""
Brain Client - Gemini API for intent classification and Q&A.

Separates the "thinking" from voice: Gemini Live handles speech,
Brain handles understanding what the student said and generating answers.
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional

from google import genai

logger = logging.getLogger(__name__)

# Common confirmation phrases that skip the Brain LLM call entirely
_SIMPLE_YES_PATTERNS = re.compile(
    r"^\s*(yes|yeah|yep|yup|sure|ready|okay|ok|go|let'?s go|"
    r"continue|next|move on|proceed|i'?m ready|go ahead|let'?s do it)\s*[.!]?\s*$",
    re.IGNORECASE,
)


def is_simple_yes(transcript: str) -> bool:
    """Check if transcript is a simple confirmation that doesn't need Brain."""
    return bool(_SIMPLE_YES_PATTERNS.match(transcript.strip()))


class BrainClient:
    """Gemini API client for intent classification and Q&A."""

    MODEL_MAP = {
        "flash": "gemini-3-flash-preview",
        "pro": "gemini-2.5-pro-preview-05-06",
        # Legacy keys from frontend UI — map to flash
        "claude": "gemini-3-flash-preview",
        "nova": "gemini-3-flash-preview",
    }

    def __init__(self, model_key: str = "flash"):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model_id = self.MODEL_MAP.get(model_key, self.MODEL_MAP["flash"])
        logger.info(f"BrainClient initialized: model={model_key} ({self.model_id})")

    async def classify_intent(self, transcript: str, task_context: str = "") -> dict:
        """
        Classify student speech into an action.

        Returns:
            {"action": "continue"|"repeat"|"question"|"skip"|"wait",
             "question_text": "..." if action is "question"}
        """
        # Short-circuit common confirmations
        if is_simple_yes(transcript):
            return {"action": "continue"}

        prompt = f"""Classify the student's speech into one of these intents:
- "continue" — student wants to move on (yes, ready, next, etc.)
- "repeat" — student wants to hear the explanation again
- "question" — student is asking a question about the material
- "wait" — student needs more time or is not ready
- "skip" — student wants to skip this section

Student said: "{transcript}"
Task context: {task_context}

Respond with ONLY a JSON object, no other text:
{{"action": "<intent>", "question_text": "<the question if intent is question, else empty string>"}}"""

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    max_output_tokens=512,
                    temperature=0.1,
                ),
            )

            response_text = response.text.strip()
            # Strip markdown code blocks if present
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning(f"Brain returned non-JSON: {response_text}")
                return {"action": "continue", "question_text": ""}

        except Exception as e:
            logger.error(f"Brain classify_intent error: {e}")
            # Default to continue on error to avoid blocking
            return {"action": "continue", "question_text": ""}

    async def answer_question(self, question: str, context: str = "") -> str:
        """
        Generate a concise answer for spoken delivery (2-3 sentences).

        Args:
            question: The student's question
            context: Current task/slide context

        Returns:
            Concise answer string suitable for voice to speak
        """
        prompt = f"""Answer this student's question concisely (2-3 sentences max).
The answer will be spoken aloud by a voice tutor, so keep it conversational.

Context: {context}
Question: {question}

Answer:"""

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    max_output_tokens=512,
                    temperature=0.5,
                ),
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"Brain answer_question error: {e}")
            return "I'm sorry, I couldn't process that question. Let's continue with the tutorial."
