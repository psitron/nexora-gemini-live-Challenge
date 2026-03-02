# Implementing Vision-Based Element Detection (Agent S3 Approach)

**Date**: 2026-03-02
**Status**: 🚧 IN PROGRESS

---

## Problem Summary

**Current (Broken):**
```
AI: "Click 'Blank workbook' at ~(382, 802)"
  ↓
Agent: Try Tesseract OCR to find "Blank workbook"
  ↓
OCR: 0 matches found (can't read button text)
  ↓
Fallback: Click inaccurate hint (382, 802)
  ↓
Result: Clicks wrong position ❌
```

**Test results on Excel screenshot:**
- "Blank workbook": 0 matches ❌
- "Blank": 0 matches ❌
- "workbook": 0 matches ❌
- "Excel": 12 matches ✅ (proves Tesseract works, just can't read buttons)

---

## Solution: Vision-Based Element Detection

**New Flow:**
```
AI: "Click 'Blank workbook'"
  ↓
Agent: Ask vision model to find element with bounding box
  ↓
Vision Model: Returns {x: 350, y: 480, w: 120, h: 60}
  ↓
Agent: Click center of bounding box
  ↓
Result: Clicks accurate position ✅
```

---

## Implementation Plan

### Step 1: Add Vision-Based Element Finder

**New method in `vision_agent.py`:**

```python
def _find_element_with_vision(
    self,
    element_description: str,
    hint_pos: Tuple[int, int] = None
) -> Optional[Tuple[int, int, int, int]]:
    """
    Use vision model to find element and return bounding box.

    Args:
        element_description: What to find (e.g., "Blank workbook button")
        hint_pos: Optional approximate location

    Returns:
        (x, y, w, h) bounding box or None
    """
    if not self._current_screenshot:
        return None

    prompt = f"""Find the UI element: "{element_description}"

Return ONLY a JSON object with the bounding box:
{{"x": <left>, "y": <top>, "w": <width>, "h": <height>}}

The bounding box should tightly encompass the clickable element.
If element not found, return: {{"x": -1, "y": -1, "w": 0, "h": 0}}

JSON only, no explanation:"""

    response = self._vision_model.generate_content(
        prompt=prompt,
        image=self._current_screenshot,
        max_tokens=256
    )

    # Parse JSON response
    bbox = self._parse_bbox_response(response)

    if bbox and bbox[0] >= 0:
        return bbox
    return None
```

---

### Step 2: Update `_do_click_text()` to Use Vision

**Modify `vision_agent.py` line 745:**

```python
def _do_click_text(self, action: VisionAction) -> bool:
    """Find text on screen using VISION, draw red box, then click."""
    import pyautogui
    from core.visual_annotator_adapter import highlight_bbox

    text = action.target
    hint = (action.hint_x, action.hint_y) if action.hint_x >= 0 else None

    print(f"  Finding '{text}' with vision-based detection...")

    # NEW: Try vision-based element detection FIRST
    bbox = self._find_element_with_vision(
        element_description=f"{text} (clickable element)",
        hint_pos=hint
    )

    if bbox:
        x, y, w, h = bbox
        print(f"  Vision found '{text}' at ({x},{y}) size {w}x{h}")

        # Draw red box around element
        highlight_bbox(
            f"{x},{y},{w},{h}",
            duration=0.8, fade_out_seconds=1.0
        )

        # Click center
        cx, cy = x + w // 2, y + h // 2
        self._smooth_click(cx, cy)
        return True

    # Fallback: Try OCR (may still work for simple text)
    print(f"  Vision failed, trying OCR fallback...")
    all_matches = self._find_all_text_matches(text, hint_pos=hint)

    if not all_matches:
        # Last resort: AI hint coordinates
        if action.hint_x >= 0 and action.hint_y >= 0:
            print(f"  OCR also failed, using AI hint ({action.hint_x},{action.hint_y})")
            pad = 15
            highlight_bbox(
                f"{action.hint_x-pad},{action.hint_y-pad},{pad*2},{pad*2}",
                duration=0.6, fade_out_seconds=0.8,
            )
            self._smooth_click(action.hint_x, action.hint_y)
            return True
        print(f"  [X] '{text}' not found by any method")
        return False

    # If OCR found matches, use them
    # ... (rest of existing code)
```

---

### Step 3: Improve Vision Prompt for Better Grounding

**Enhance main vision prompt to encourage precise coordinates:**

```python
prompt = f"""You are a Windows PC automation agent with PIXEL-PRECISE vision.

GOAL: {goal}
{history}{assessment}

When you choose an action that targets a UI element:
1. Look CAREFULLY at the element's EXACT position
2. Provide hint_x/hint_y at the CENTER of that element
3. Be PRECISE - coordinates must be accurate within ±10 pixels

For "click_text" actions:
- The vision system will find the exact bounding box using your hint
- Your hint guides the search, so be as accurate as possible
- Look at the element's visual center, not approximate location

Screenshot size: {img_w}x{img_h} pixels

...rest of prompt...
```

---

## Expected Improvements

| Metric | Before (OCR) | After (Vision) |
|--------|-------------|----------------|
| **Element detection rate** | ~30% (OCR fails on buttons) | ~90% (Vision sees all) |
| **Click accuracy** | ±200 pixels | ±10 pixels |
| **Latency** | 2-5s (OCR scan) | 1-2s (1 vision call) |
| **"Blank workbook" detection** | 0 matches ❌ | Should work ✅ |

---

## Testing Plan

1. **Test on Excel screenshot**:
   ```bash
   python -c "
   from PIL import Image
   from core.vision_agent import VisionAgent

   agent = VisionAgent()
   img = Image.open('logs/20260302_184759/screenshots/step_6_before.png')
   agent._current_screenshot = img

   bbox = agent._find_element_with_vision('Blank workbook')
   print(f'Result: {bbox}')
   "
   ```

2. **Run full test**:
   ```bash
   echo "2" | python test_educational_excel.py
   ```

3. **Check logs for**:
   - "Vision found 'Blank workbook' at (x,y)"
   - No more "OCR missed, using AI coordinates"
   - Accurate clicks (within ±10 pixels)

---

## Fallback Strategy

**Priority order:**
1. 🥇 **Vision-based element detection** (new, most accurate)
2. 🥈 **OCR text search** (existing, works for plain text)
3. 🥉 **AI hint coordinates** (existing, least accurate)

This ensures we always have a fallback if vision fails.

---

## Next Steps

1. Implement `_find_element_with_vision()` method
2. Update `_do_click_text()` to use vision first
3. Test on Excel screenshot
4. Run full educational test
5. Verify accuracy improvements

---

**Status: Ready to implement. Should I proceed?**
