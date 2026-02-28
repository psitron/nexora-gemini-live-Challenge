from __future__ import annotations

"""
Hybrid AI Agent – Level 4 local vision execution.

Uses Qwen2-VL (or compatible local VLM) with the grounding prompt to
locate UI elements based on OmniParser/NormalisedEnvironment output.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import io

from config.latency_thresholds import VLM_LOCAL_CONFIDENCE_THRESHOLD
from config.settings import get_settings
from perception.schemas import NormalisedEnvironment
from perception.visual.vlm_reader import build_grounding_prompt, parse_vlm_response, VLMResult
from perception.visual.screenshot import capture_primary_monitor
from execution.level0_programmatic import ActionResult


@dataclass
class LocalVLMExecutor:
    """
    Minimal wrapper around a Qwen2-VL style HTTP API.
    """

    endpoint: str
    api_key: str
    model: str

    def call(self, prompt: str, image_bytes: bytes) -> str:
        """
        Perform a blocking HTTP call to the local VLM endpoint.
        NOTE: This is a placeholder; implement your actual HTTP client here.
        """
        # To avoid adding heavy HTTP deps, leave this as a stub that raises
        # until the user wires in their own client.
        raise NotImplementedError(
            "LocalVLMExecutor.call is not implemented. "
            "Wire this to your Qwen2-VL HTTP endpoint."
        )


class Level4LocalVisionExecutor:
    """
    Level 4 executor using local Qwen2-VL with grounding prompt.
    """

    def __init__(self) -> None:
        settings = get_settings()
        endpoint = settings.models.qwen_endpoint or "http://localhost:8000/v1/chat/completions"
        api_key = settings.models.qwen_api_key or ""
        model = settings.models.qwen_model
        self._client = LocalVLMExecutor(endpoint=endpoint, api_key=api_key, model=model)

    def coordinate_denormalise(self, bbox_str: str, original_size: Tuple[int, int]) -> str:
        """
        Convert bbox from 1280x720 space back to original resolution.
        """
        x, y, w, h = [int(v) for v in bbox_str.split(",")]
        orig_w, orig_h = original_size
        scale_x = orig_w / 1280.0
        scale_y = orig_h / 720.0
        nx = int(x * scale_x)
        ny = int(y * scale_y)
        nw = int(w * scale_x)
        nh = int(h * scale_y)
        return f"{nx},{ny},{nw},{nh}"

    def execute(
        self,
        env: NormalisedEnvironment,
        action_description: str,
        element_description: str,
    ) -> ActionResult:
        """
        Build grounding prompt, call local VLM, and return a matched bbox
        if confidence is high enough.
        """
        # Build prompt
        prompt = build_grounding_prompt(env, action_description, element_description)

        # Capture and resize screenshot to 1280x720
        img = capture_primary_monitor()
        original_size = img.size
        resized = img.resize((1280, 720))
        buf = io.BytesIO()
        resized.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        try:
            raw_response = self._client.call(prompt, image_bytes)
        except NotImplementedError as exc:
            return ActionResult(False, f"Local VLM not wired: {exc}")
        except Exception as exc:
            return ActionResult(False, f"Local VLM call failed: {exc}")

        try:
            vlm_result: VLMResult = parse_vlm_response(raw_response)
        except Exception as exc:
            return ActionResult(False, f"Failed to parse VLM response: {exc}")

        if vlm_result.not_found:
            return ActionResult(False, "VLM reported ELEMENT_NOT_FOUND.")

        if vlm_result.confidence < VLM_LOCAL_CONFIDENCE_THRESHOLD:
            return ActionResult(
                False,
                f"VLM confidence {vlm_result.confidence:.2f} below threshold "
                f"{VLM_LOCAL_CONFIDENCE_THRESHOLD:.2f}.",
            )

        if not vlm_result.bbox:
            return ActionResult(False, "VLM response missing bbox.")

        denorm_bbox = self.coordinate_denormalise(vlm_result.bbox, original_size)
        data = {
            "bbox": denorm_bbox,
            "element_id": vlm_result.element_id,
            "element_label": vlm_result.element_label,
            "confidence": vlm_result.confidence,
        }
        return ActionResult(True, "Local VLM matched element.", data=data)

