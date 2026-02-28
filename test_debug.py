#!/usr/bin/env python
"""Quick test of VisionAgent initialization."""

import os
os.environ["DEBUG_MODE"] = "true"

import sys
sys.path.insert(0, "E:/ui-agent")

print("Creating VisionAgent...")
from core.vision_agent import VisionAgent
agent = VisionAgent()
print("Done! Debug dir:", agent._debug_dir)
print("Debug mode:", agent._debug_mode)
