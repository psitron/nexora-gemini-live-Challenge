from __future__ import annotations

"""
Hybrid AI Agent – TemplateMatchingConfig.

Defines configuration for Level 3 OpenCV template matching.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from config.settings import get_settings


@dataclass
class TemplateMatchingConfig:
    # Storage
    template_dir: Path
    template_format: str  # 'png'
    naming_convention: str  # '{app_name}_{label}_{width}x{height}.png'

    # Resolution policy
    normalise_to: Tuple[int, int]  # (width, height)
    scale_factors: List[float]

    # Confidence
    min_confidence: float
    multi_match_threshold: float

    # ROI
    roi_mode: str  # 'active_window' | 'full_screen'
    roi_padding_px: int

    # Multi-monitor
    monitor_strategy: str  # 'active_only' | 'all' | 'primary'

    @classmethod
    def default(cls) -> "TemplateMatchingConfig":
        settings = get_settings()
        template_dir = settings.paths.template_dir
        return cls(
            template_dir=template_dir,
            template_format="png",
            naming_convention="{app_name}_{label}_{width}x{height}.png",
            normalise_to=(1280, 720),
            scale_factors=[0.75, 1.0, 1.25],
            min_confidence=0.80,
            multi_match_threshold=0.95,
            roi_mode="active_window",
            roi_padding_px=20,
            monitor_strategy="active_only",
        )
