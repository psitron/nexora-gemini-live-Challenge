from __future__ import annotations

"""
Hybrid AI Agent – Level 3 pattern matching (OpenCV).

Minimal executor that:
- Loads a template image from the templates directory
- Captures a primary-monitor screenshot
- Runs template matching at multiple scales
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image

from config.template_matching import TemplateMatchingConfig
from perception.visual.screenshot import capture_primary_monitor
from execution.level0_programmatic import ActionResult


@dataclass
class MatchResult:
    element_id: str
    confidence: float
    bbox: str  # 'x,y,w,h'
    scale_factor: float
    monitor_id: int


class PatternMatchExecutor:
    def __init__(self, config: Optional[TemplateMatchingConfig] = None) -> None:
        self.config = config or TemplateMatchingConfig.default()

    def _load_template(self, label: str, app_name: str) -> Optional[np.ndarray]:
        # For now assume a single template named '{app_name}_{label}.png'
        path = self.config.template_dir / f"{app_name}_{label}.{self.config.template_format}"
        if not path.exists():
            return None
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        return img

    def _to_gray(self, img: Image.Image) -> np.ndarray:
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

    def capture_and_match(self, label: str, app_name: str = "app") -> ActionResult:
        template = self._load_template(label, app_name)
        if template is None:
            return ActionResult(False, f"Template for {label} not found.")

        screenshot = capture_primary_monitor()
        screen_gray = self._to_gray(screenshot)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        h, w = template_gray.shape[:2]
        best_conf = 0.0
        best_bbox = None
        best_scale = 1.0

        for scale in self.config.scale_factors:
            resized = cv2.resize(
                template_gray,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_AREA,
            )
            res = cv2.matchTemplate(screen_gray, resized, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val > best_conf:
                best_conf = max_val
                x, y = max_loc
                rw, rh = resized.shape[1], resized.shape[0]
                best_bbox = (x, y, rw, rh)
                best_scale = scale

        if best_bbox is None or best_conf < self.config.min_confidence:
            return ActionResult(False, f"No reliable match for {label} (best={best_conf:.2f}).")

        x, y, rw, rh = best_bbox
        bbox_str = f"{x},{y},{rw},{rh}"
        match = MatchResult(
            element_id=label,
            confidence=best_conf,
            bbox=bbox_str,
            scale_factor=best_scale,
            monitor_id=0,
        )
        return ActionResult(
            True,
            f"Matched {label} with confidence {best_conf:.2f}",
            data={"match": match},
        )

