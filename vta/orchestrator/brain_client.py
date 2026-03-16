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
        self.model_id = self.MODEL_MAP.get(model_key, model_key)
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
- "repeat" — student wants to see/hear the task demonstrated again
- "question" — student is asking a question about the material (wants a verbal answer)
- "freestyle" — student is asking the AI to DO something on the computer (run a command, open an app, show something on screen). This is NOT a question — the student wants ACTION, not explanation.
- "wait" — student needs more time or is not ready
- "skip" — student wants to skip this section

Examples of "freestyle":
- "Can you run docker ps?" → freestyle, goal: "Run docker ps in the terminal"
- "Show me how to open a text editor" → freestyle, goal: "Open a text editor on the desktop"
- "Can you create a file called test.py?" → freestyle, goal: "Create a file called test.py"

Examples of "question":
- "What does the ls command do?" → question
- "Why do we use Python for this?" → question

Student said: "{transcript}"
Task context: {task_context}

Respond with ONLY a JSON object, no other text:
{{"action": "<intent>", "question_text": "<the question if intent is question, else empty>", "goal": "<the goal to execute on screen if intent is freestyle, else empty>"}}"""

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

    async def explain_slide(self, image_bytes: bytes, slide_title: str = "") -> str:
        """
        Analyze a slide image and generate a spoken explanation.

        Uses Gemini's vision capability to see the slide and describe it
        in a way suitable for a voice tutor to speak aloud.

        Args:
            image_bytes: PNG image of the slide.
            slide_title: Optional title for context.

        Returns:
            Explanation text suitable for voice delivery.
        """
        prompt = (
            f"You are a voice tutor explaining this slide to a student. "
            f"Look at the slide image carefully and explain the key concepts shown. "
            f"Give a clear, conversational explanation in 10 to 12 sentences. "
            f"Each sentence should add value. Cover the main topics and takeaways. "
            f"This will be spoken aloud, so be natural and engaging. "
            f"Do NOT just read the title — explain what the content means."
        )
        if slide_title:
            prompt += f"\n\nSlide title: {slide_title}"

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=[
                    genai.types.Content(
                        role="user",
                        parts=[
                            genai.types.Part(text=prompt),
                            genai.types.Part(
                                inline_data=genai.types.Blob(
                                    data=image_bytes,
                                    mime_type="image/png",
                                )
                            ),
                        ],
                    )
                ],
                config=genai.types.GenerateContentConfig(
                    max_output_tokens=1000,
                    temperature=0.5,
                ),
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"Brain explain_slide error: {e}")
            return f"This slide covers {slide_title}. Let me explain the key points."

    async def answer_question(self, question: str, context: str = "") -> str:
        """
        Generate a concise answer for spoken delivery (2-3 sentences).

        Args:
            question: The student's question
            context: Current task/slide context

        Returns:
            Concise answer string suitable for voice to speak
        """
        prompt = f"""Answer in 1-2 sentences. Spoken aloud, be brief.

Context: {context}
Question: {question}"""

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    max_output_tokens=128,
                    temperature=0.5,
                ),
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"Brain answer_question error: {e}")
            return "I'm sorry, I couldn't process that question. Let's continue with the tutorial."
