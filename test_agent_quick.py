#!/usr/bin/env python
"""Quick test to verify VisionAgent runs."""
import os
os.environ["DEBUG_MODE"] = "false"

import sys
sys.path.insert(0, "E:/ui-agent")

print("1. Importing VisionAgent...")
from core.vision_agent import VisionAgent

print("2. Creating agent...")
agent = VisionAgent()

print("3. All imports successful!")
print(f"   Model: {agent._model_name}")
print(f"   Monitor: {agent._monitor_rect}")
