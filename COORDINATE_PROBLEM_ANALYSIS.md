# 🔴 COORDINATE PROBLEM - Root Cause Analysis

**Date**: 2026-03-02
**Problem**: Agent clicking in WRONG positions despite correct logging

---

## Evidence from Latest Run (20260302_145003)

### Step 8: Try to click "Blank workbook"

**What agent logged**:
```json
{
  "target": "Blank workbook",
  "coordinates": {
    "raw_x": 133,
    "raw_y": 250,
    "scaled_x": 249,
    "scaled_y": 468
  }
}
```

**Math verification**:
- 133 * 1.875 = 249 ✓
- 250 * 1.875 = 468 ✓

**Click position**: (249, 468)

**Visual inspection** (screenshot step_8_before.png):
- "Blank workbook" template is at TOP-LEFT of screen
- Approximate actual position: (~60-70, ~60-80)
- Screen size: 1920 x 1080

**The problem**:
- Agent clicked at (249, 468)
- "Blank workbook" is actually at (~65, ~70)
- Agent clicked **400 pixels too low**!

---

## Root Cause Hypothesis

### The AI is giving WRONG coordinates

Looking at the data:
1. AI returns `raw_x=133, raw_y=250` (in 1024px space)
2. This gets scaled to `scaled_x=249, scaled_y=468` (screen space)
3. Agent clicks at (249, 468)
4. **But the target is actually at (~65, ~70)**

### Why is the AI wrong?

**Possible causes**:

1. **AI sees resized image (1024px wide)**
   - Screenshot is 1920x1080 → resized to 1024x576 (maintaining aspect ratio)
   - AI analyzes the 1024x576 image
   - Returns coordinates in that space
   - If "Blank workbook" is at (35, 38) in the 1024px image...
   - Scaled: 35 * 1.875 = 65 ✓ (close!)
   - BUT AI returned 133, not 35!

2. **AI is hallucinating coordinates**
   - AI doesn't have accurate spatial understanding
   - Guessing approximate position
   - Off by 2-3x the correct value

3. **OCR hint is being used AFTER scaling**
   - OCR finds "Blank workbook" at real position (65, 70)
   - But somehow the wrong coordinates are being logged

---

## What We Need to Verify

### Test 1: Use the Coordinate Validator Tool

**File**: `tools/coordinate_validator.html`

**Steps**:
1. Open `coordinate_validator.html` in browser
2. Upload `logs/20260302_145003/screenshots/step_8_before.png`
3. Click on "Blank workbook" template
4. Extract REAL coordinates
5. Compare with agent's coordinates

**Expected**:
- Real position: (~65, ~70)
- Agent's position: (249, 468)
- Difference: ~180px horizontal, ~400px vertical

### Test 2: Check What AI Actually Sees

The vision agent resizes screenshots before sending to AI:

**File**: `core/vision_agent.py` line 236
```python
small_screenshot = self._resize_screenshot(screenshot)
```

**Question**: What size is the resized image?
- Original: 1920 x 1080
- Resized: 1024 x ??? (maintains aspect ratio)
- Expected: 1024 x 576

**If "Blank workbook" is at (65, 70) on 1920x1080 screen**:
- On 1024px image: 65 / 1.875 = ~35
- AI should return: raw_x=35, raw_y=37
- **But AI returned: raw_x=133, raw_y=250** ❌

**The AI is wrong by 4x!**

---

## Debugging Steps

### Step 1: Validate Real Coordinates

Open `tools/coordinate_validator.html` and mark:
1. Where is "Blank workbook" template?
2. Where is the text "Blank workbook"?
3. Where did the agent actually click?

### Step 2: Check OCR Output

The vision agent uses OCR to refine coordinates:

**File**: `core/vision_agent.py` method `_execute_action()`

Check if OCR is finding "Blank workbook" correctly:
- Does OCR find the text?
- What bounding box does OCR return?
- Is that bbox being used for the click?

### Step 3: Check What AI Receives

Add debug logging to see:
1. Original screenshot size
2. Resized screenshot size
3. What AI returns (raw coordinates)
4. What OCR finds (if OCR is used)
5. Final click position

---

## Possible Fixes

### Fix Option 1: AI Coordinates Are Unreliable - Use OCR

**Problem**: AI's spatial understanding is poor
**Solution**: Always use OCR to find exact text position

**Implementation**:
```python
# Instead of trusting AI coordinates:
if action.action_type in ["click_text", "click_icon"]:
    # Use OCR to find exact position
    bbox = ocr_find(action.target, screenshot)
    if bbox:
        # Use OCR bbox center
        click_x = bbox.x + bbox.w // 2
        click_y = bbox.y + bbox.h // 2
    else:
        # Fallback to AI coordinates
        click_x = scaled_x
        click_y = scaled_y
```

### Fix Option 2: Better AI Prompting

**Problem**: AI is guessing coordinates without proper grounding
**Solution**: Use OmniParser or similar to detect UI elements first

**Implementation**:
- Run element detection BEFORE asking AI
- Overlay element markers on image
- AI references marker IDs instead of coordinates
- Map marker ID → actual coordinates

### Fix Option 3: Verify Coordinates Before Click

**Problem**: No validation that target is at click position
**Solution**: Check if target text exists near click position

**Implementation**:
```python
# Before clicking:
region = screenshot.crop((click_x - 50, click_y - 50, click_x + 50, click_y + 50))
found_text = ocr_extract(region)
if action.target.lower() in found_text.lower():
    # Good, target is near click position
    click(click_x, click_y)
else:
    # Bad, target not found near click position
    # Search entire screenshot for target
    bbox = ocr_find(action.target, screenshot)
    click(bbox.center)
```

---

## Immediate Action Required

1. **Use coordinate validator tool** to confirm real position of "Blank workbook"

2. **Check if OCR is working**:
   ```python
   # Add debug logging in vision_agent.py
   if self._use_ocr_hints:
       print(f"[OCR] Searching for: {action.target}")
       bbox = find_text_bbox(...)
       print(f"[OCR] Found at: {bbox}")
   ```

3. **Compare**:
   - Real position (from validator tool)
   - AI's coordinates (from logs)
   - OCR's bbox (from debug logs)
   - Final click position (from logs)

---

## Tool Created

**File**: `tools/coordinate_validator.html`

**How to use**:
```bash
# Open in browser:
start tools/coordinate_validator.html

# Or:
python -m http.server 8000
# Then open: http://localhost:8000/tools/coordinate_validator.html
```

**Features**:
- Upload any screenshot
- Click to mark element positions
- Extracts exact (x, y) coordinates
- Calculates bbox for 40x40 marker
- Copy coordinates to clipboard
- Compare with agent's logged coordinates

---

## Next Steps

1. Open coordinate validator tool
2. Upload `logs/20260302_145003/screenshots/step_8_before.png`
3. Mark where "Blank workbook" actually is
4. Share the real coordinates
5. I'll compare with agent's coordinates and find the bug

**Then we can implement the correct fix!**
