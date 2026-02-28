from __future__ import annotations

"""
Hybrid AI Agent – latency thresholds.

Central place for confidence thresholds used by the vision stack.
"""

VLM_LOCAL_CONFIDENCE_THRESHOLD: float = 0.60  # below this → escalate to L5 cloud
VLM_CLOUD_CONFIDENCE_THRESHOLD: float = 0.50  # below this → escalate to L6 human
OMNIPARSER_MIN_CONFIDENCE: float = 0.40       # discard elements below this

