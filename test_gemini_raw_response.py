"""
Check raw Gemini response to see why it's truncated
"""

from PIL import Image
from pathlib import Path
import google.generativeai as genai
from config.settings import get_settings

settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.models.gemini_api_key)
model = genai.GenerativeModel(settings.models.gemini_vision_model)

# Load screenshot
screenshot_path = Path("logs/20260302_184759/screenshots/step_6_before.png")
img = Image.open(screenshot_path)

prompt = """Find the UI element: "Blank workbook button"

Return ONLY a JSON object:
{"x": <left>, "y": <top>, "w": <width>, "h": <height>}

JSON only:"""

print("Calling Gemini...")
response = model.generate_content(
    [prompt, img],
    generation_config={
        "max_output_tokens": 256,
        "temperature": 0.1
    }
)

print("="*70)
print("RAW RESPONSE OBJECT:")
print(f"Type: {type(response)}")
print()

print("CANDIDATES:")
if hasattr(response, 'candidates'):
    print(f"Number of candidates: {len(response.candidates)}")
    for i, candidate in enumerate(response.candidates):
        print(f"\nCandidate {i}:")
        print(f"  finish_reason: {candidate.finish_reason}")
        if hasattr(candidate, 'content'):
            print(f"  content.parts: {len(candidate.content.parts)}")
            for j, part in enumerate(candidate.content.parts):
                print(f"    Part {j}: {part.text if hasattr(part, 'text') else part}")

print()
print("RESPONSE.TEXT:")
if hasattr(response, 'text'):
    print(f"Length: {len(response.text)}")
    print(response.text)
else:
    print("No .text attribute")

print()
print("PROMPT_FEEDBACK:")
if hasattr(response, 'prompt_feedback'):
    print(response.prompt_feedback)
