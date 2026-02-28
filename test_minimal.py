#!/usr/bin/env python
"""Minimal test to find the hanging import."""

print("1. Starting...")

import ctypes as _ctypes
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)
    print("2. DPI awareness set")
except Exception as e:
    print(f"2. DPI awareness failed: {e}")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
print("3. Path setup done")

print("4. Importing VisionAgent...")
from core.vision_agent import VisionAgent
print("5. VisionAgent imported")

print("6. Creating VisionAgent instance...")
agent = VisionAgent()
print("7. VisionAgent instance created")

print("8. All done!")
