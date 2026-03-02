"""
Debug what vision model returns for element detection
"""

from PIL import Image
from pathlib import Path
from core.vision_agent import VisionAgent

screenshot_path = Path("logs/20260302_184759/screenshots/step_6_before.png")
img = Image.open(screenshot_path)

agent = VisionAgent()
agent._current_screenshot = img

# Call vision model directly
prompt = """Find the UI element: "Blank workbook button"

Hint: Element is approximately at (382, 802). Look near this area.

Look at this 1920x1080 screenshot and locate the element.
Return the bounding box as a tight rectangle around the CLICKABLE area.

Return ONLY a JSON object in this EXACT format:
{"x": <left>, "y": <top>, "w": <width>, "h": <height>}

Rules:
- x,y = top-left corner of the element
- w,h = width and height of the clickable area
- If element not found or not visible, return: {"x": -1, "y": -1, "w": 0, "h": 0}
- No explanation, ONLY the JSON object
- Coordinates must be in the 1920x1080 image space

JSON only:"""

print("Sending prompt to vision model...")
print("="*70)

response = agent._vision_model.generate_content(
    prompt=prompt,
    image=img,
    max_tokens=256
)

print("RAW RESPONSE OBJECT:")
print(type(response))
print()

print("RESPONSE TEXT:")
response_text = response.text if hasattr(response, 'text') else str(response)
print(f"Length: {len(response_text)} characters")
print(response_text)
print()

print("="*70)
print("Attempting to parse...")

import json
import re

text = response_text.strip()
text = re.sub(r'```json\s*', '', text)
text = re.sub(r'```\s*', '', text)
text = text.strip()

print(f"After cleanup: '{text}'")
print()

# Try different regex patterns
patterns = [
    r'\{[^}]*\}',  # Current
    r'\{.*?\}',    # Non-greedy
    r'\{.+\}',     # Greedy
]

for pattern in patterns:
    print(f"Testing pattern: {pattern}")
    match = re.search(pattern, text, re.DOTALL)
    if match:
        json_str = match.group(0)
        print(f"  Matched: {json_str}")
        try:
            data = json.loads(json_str)
            print(f"  Parsed successfully: {data}")
        except json.JSONDecodeError as e:
            print(f"  Failed to parse: {e}")
    else:
        print(f"  No match")
    print()
