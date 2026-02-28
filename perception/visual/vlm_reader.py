from __future__ import annotations

"""
Hybrid AI Agent – VLM reader.

Builds the grounding prompt for Qwen2-VL / local VLM using the
NormalisedEnvironment.interactive list.
"""

from dataclasses import dataclass
from typing import Any, Dict, List
import json

from perception.schemas import NormalisedEnvironment, NormalisedElement


GROUNDING_TEMPLATE = """
SYSTEM:

You are a GUI agent. You must identify the exact UI element to interact with.

You will be given:

1. A screenshot of the current screen
2. A list of detected UI elements with their labels and positions
3. The action you need to perform

Rules:
- Only reference elements from the provided element list
- Never invent element positions --- use the bbox from the list
- If the target element is not in the list, respond with ELEMENT_NOT_FOUND
- Return ONLY the JSON response format below --- no other text

USER:

Current screen elements (detected by OmniParser):

{element_list_json}

Action to perform: {action_description}

Target element description: {element_description}

Respond ONLY with this JSON:

{{
  "element_id": "el_001",
  "element_label": "Submit Button",
  "action": "click",
  "bbox": "450,320,80,30",
  "click_point": "490,335",
  "confidence": 0.94,
  "reasoning": "Matched 'Submit Button' to target 'submit form button'"
}}

If element not found:

{{"element_id": null, "confidence": 0.0, "reasoning": "ELEMENT_NOT_FOUND: <reason>"}}
""".strip()


@dataclass
class VLMResult:
    element_id: str | None
    element_label: str | None
    action: str
    bbox: str | None
    click_point: str | None
    confidence: float
    reasoning: str
    not_found: bool


def build_grounding_prompt(
    env: NormalisedEnvironment,
    action_description: str,
    element_description: str,
) -> str:
    """
    Format NormalisedEnvironment.interactive into the grounding prompt
    expected by the local VLM.
    """
    elements_payload: List[Dict[str, Any]] = []
    for el in env.interactive:
        elements_payload.append(
            {
                "id": el.id,
                "label": el.label,
                "type": el.element_type,
                "bbox": el.bbox,
                "confidence": el.confidence,
            }
        )

    element_list_json = json.dumps(elements_payload, indent=2)
    prompt = GROUNDING_TEMPLATE.format(
        element_list_json=element_list_json,
        action_description=action_description,
        element_description=element_description,
    )
    return prompt


def parse_vlm_response(response: str) -> VLMResult:
    """
    Parse raw VLM response text into VLMResult. Strips any surrounding
    fences and expects pure JSON.
    """
    text = response.strip()
    # Strip common JSON fences like ```json ... ``` if present.
    if text.startswith("```"):
        text = text.strip("`")
        # Remove possible language tag prefix `json\n`
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    data = json.loads(text)

    element_id = data.get("element_id")
    element_label = data.get("element_label")
    action = data.get("action", "")
    bbox = data.get("bbox")
    click_point = data.get("click_point")
    confidence = float(data.get("confidence", 0.0))
    reasoning = data.get("reasoning", "")
    not_found = bool(
        element_id is None
        and "ELEMENT_NOT_FOUND" in reasoning
    )

    return VLMResult(
        element_id=element_id,
        element_label=element_label,
        action=action,
        bbox=bbox,
        click_point=click_point,
        confidence=confidence,
        reasoning=reasoning,
        not_found=not_found,
    )

