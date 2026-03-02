from __future__ import annotations

"""
Hybrid AI Agent – Level 5 cloud vision execution.

Uses Gemini Flash (or compatible cloud VLM) as a slower, higher-reliability
fallback when local vision (Level 4) is uncertain or unavailable.

Now includes human-like cursor movement and timing.
"""

from dataclasses import dataclass
from typing import Tuple

import io

from config.latency_thresholds import VLM_CLOUD_CONFIDENCE_THRESHOLD
from config.settings import get_settings
from perception.schemas import NormalisedEnvironment
from perception.visual.vlm_reader import build_grounding_prompt, parse_vlm_response, VLMResult
from perception.visual.screenshot import capture_primary_monitor
from execution.level0_programmatic import ActionResult
from execution.mouse_controller import click_center_of_bbox
from core.human_timing import HumanTiming


@dataclass
class CloudVLMExecutor:
    """
    Wrapper around Gemini Flash via google-generativeai.
    """

    api_key: str
    model: str

    def call(self, prompt: str, image_bytes: bytes) -> str:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=FutureWarning)
                import google.generativeai as genai  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"google-generativeai not available: {exc}") from exc

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)

        # Gemini multimodal: [image, text]
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        resp = model.generate_content([img, prompt])
        text = (resp.text or "").strip()
        return text


class Level5CloudVisionExecutor:
    """
    Level 5 executor using Gemini Flash as cloud vision fallback.
    Now with human-like cursor movement and timing.
    """

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.models.gemini_api_key or ""
        model = settings.models.gemini_vision_model
        self._client = CloudVLMExecutor(api_key=api_key, model=model)
        self._timing = HumanTiming()

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
        environment: NormalisedEnvironment,
        action_description: str,
        element_description: str,
        perform_click: bool = False,
    ) -> ActionResult:
        """
        Build grounding prompt, call Gemini Flash, and return matched bbox.
        
        If perform_click=True, also moves cursor and clicks with human timing.
        """
        settings = get_settings()
        if not settings.models.gemini_api_key:
            return ActionResult(False, "GEMINI_API_KEY not configured; cannot use Level 5 vision.")

        prompt = build_grounding_prompt(environment, action_description, element_description)

        # Capture and resize screenshot to 1280x720
        img = capture_primary_monitor()
        original_size = img.size
        resized = img.resize((1280, 720))
        buf = io.BytesIO()
        resized.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        try:
            raw_response = self._client.call(prompt, image_bytes)
        except Exception as exc:
            return ActionResult(False, f"Cloud VLM call failed: {exc}")

        try:
            vlm_result: VLMResult = parse_vlm_response(raw_response)
        except Exception as exc:
            return ActionResult(False, f"Failed to parse cloud VLM response: {exc}")

        if vlm_result.not_found:
            return ActionResult(False, "Cloud VLM reported ELEMENT_NOT_FOUND.")

        if vlm_result.confidence < VLM_CLOUD_CONFIDENCE_THRESHOLD:
            return ActionResult(
                False,
                f"Cloud VLM confidence {vlm_result.confidence:.2f} below threshold "
                f"{VLM_CLOUD_CONFIDENCE_THRESHOLD:.2f}.",
            )

        if not vlm_result.bbox:
            return ActionResult(False, "Cloud VLM response missing bbox.")

        denorm_bbox = self.coordinate_denormalise(vlm_result.bbox, original_size)
        data = {
            "bbox": denorm_bbox,
            "element_id": vlm_result.element_id,
            "element_label": vlm_result.element_label,
            "confidence": vlm_result.confidence,
        }
        
        # If perform_click=True, show red box then move cursor and click
        if perform_click:
            print(f"  Vision found '{element_description}'")
            print(f"    Bbox (denormalized): {denorm_bbox}")
            
            # Draw red box around the element so viewer sees what we're clicking
            try:
                from core.visual_annotator_adapter import highlight_bbox
                highlight_bbox(denorm_bbox, duration=1.5)
            except Exception as e:
                print(f"  [Could not draw highlight: {e}]")
            
            # Parse and show where we're clicking
            try:
                parts = denorm_bbox.split(",")
                if len(parts) == 4:
                    x, y, w, h = [int(p) for p in parts]
                    cx, cy = x + w // 2, y + h // 2
                    print(f"    Will click at: ({cx}, {cy})")
                    print(f"    Screen resolution: {original_size[0]}x{original_size[1]}")
            except Exception:
                pass
            
            print(f"  Moving cursor and clicking...")
            
            # Calculate distance for timing
            try:
                import pyautogui
                parts = denorm_bbox.split(",")
                if len(parts) == 4:
                    x, y, w, h = [int(p) for p in parts]
                    cx, cy = x + w // 2, y + h // 2
                    curr_x, curr_y = pyautogui.position()
                    distance = ((cx - curr_x) ** 2 + (cy - curr_y) ** 2) ** 0.5
                    print(f"    Current cursor: ({curr_x}, {curr_y})")
                    print(f"    Distance: {distance:.0f}px")
                else:
                    distance = 500
            except Exception:
                distance = 500
            
            move_duration = self._timing.cursor_move_duration(int(distance))
            self._timing.before_click()
            
            mouse_result = click_center_of_bbox(denorm_bbox, move_duration=move_duration)
            
            self._timing.after_click()
            
            if not mouse_result.success:
                return ActionResult(False, f"Vision found element but click failed: {mouse_result.message}", data=data)
            
            return ActionResult(True, f"Vision clicked '{element_description}' successfully", data=data)
        
        return ActionResult(True, "Cloud VLM matched element.", data=data)

