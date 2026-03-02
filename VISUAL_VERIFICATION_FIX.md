# Fixed: Visual Verification Debug Screenshots Missing

**Date**: 2026-03-02
**Status**: ✅ FIXED

---

## Problem

User reported: "in my previous version when we are using windows default ocr when we capture screenshots we are chopping the screenshot and merging it together and sending to gemini to identify what's right icon that i can click. i had that screenshots in my log as well which as annotated with red boxed with label, but i don't see those screenshots in logs now why?"

**Missing Screenshots:**
- `verify_01_crop_0_numbered.png` - Individual crops of each OCR match with number labels
- `verify_01_crop_1_numbered.png` - Second candidate crop
- `verify_01_composite_numbered.png` - Composite image showing all candidates for Gemini to choose from

**Root Cause:**
- Code to save debug screenshots exists in `_verify_correct_match()` method
- BUT: Conditional on `if self._debug_dir:`
- `self._debug_dir` was NEVER set in `VisionAgentLogged`
- It was only set if environment variable `VISION_DEBUG=1` was set (which user didn't have)
- Result: All visual verification debug images were silently skipped

---

## The Fix

### File: `core/vision_agent_logged.py`

**Change 1: Initialize debug directory (line 64-68)**
```python
# Initialize logger
self.logger = DetailedLogger(goal, self.log_dir)

# Enable debug directory for visual verification crops
# This ensures numbered crops (verify_01_crop_0.png, etc.) are saved
self._debug_dir = self.logger.screenshots_dir

print(f"\n[DetailedLogger] Logging enabled!")
print(f"[DetailedLogger] Logs will be saved to: {self.logger.output_dir}")
print(f"[DetailedLogger] Debug screenshots (visual verification crops) will be saved to: {self._debug_dir}\n")
```

**Change 2: Always save debug screenshots in logged mode (line 246-248)**
```python
# Save full and resized screenshots for debugging
if self._debug_dir:
    screenshot.save(self._debug_dir / f"step_{steps:02d}_full.png")
    small_screenshot.save(self._debug_dir / f"step_{steps:02d}_resized.png")
```

Changed from `if self._debug_mode:` (which required env var) to `if self._debug_dir:` (which is now always set in logged mode).

---

## What Gets Saved Now

**When Visual Verification Runs:**

1. **Individual Numbered Crops** (for each candidate match):
   ```
   logs/20260302_HHMMSS/screenshots/verify_01_crop_0_numbered.png
   logs/20260302_HHMMSS/screenshots/verify_01_crop_1_numbered.png
   logs/20260302_HHMMSS/screenshots/verify_01_crop_2_numbered.png
   ```
   - Each crop shows one OCR match with a number label at the top
   - Has colored border (alternating blue/green/orange)

2. **Composite Image** (all candidates side-by-side):
   ```
   logs/20260302_HHMMSS/screenshots/verify_01_composite_numbered.png
   ```
   - Grid layout (max 3 crops per row)
   - Gemini analyzes this to choose the correct match
   - Resized to max 1200x800 if too large

3. **Full and Resized Screenshots** (for each step):
   ```
   logs/20260302_HHMMSS/screenshots/step_01_full.png      (1920x1080)
   logs/20260302_HHMMSS/screenshots/step_01_resized.png   (1024x576)
   ```

---

## When Visual Verification Triggers

Visual verification runs when:
1. OCR finds **multiple matches** for the same text (e.g., two "Search" buttons)
2. AI provides a **hint coordinate** (approximate location)
3. Agent needs to **disambiguate** which match is correct

**Example Scenario:**
- Task: "Click Blank workbook"
- OCR finds 3 matches for "Blank workbook" on screen
- Visual verification:
  1. Captures 3 crops around each match
  2. Numbers them 0, 1, 2 with labels
  3. Creates composite image
  4. Asks Gemini: "Which of these 3 options is the 'Blank workbook' button?"
  5. Gemini responds: "Option 1"
  6. Agent clicks option 1

**Debug artifacts saved:**
- `verify_01_crop_0_numbered.png` - First candidate
- `verify_01_crop_1_numbered.png` - Second candidate ✓ (Gemini chose this)
- `verify_01_crop_2_numbered.png` - Third candidate
- `verify_01_composite_numbered.png` - All 3 side-by-side for comparison

---

## How to Verify Fix is Working

### 1. Run Test
```bash
python test_educational_excel.py
```

### 2. Check Console Output
Should see:
```
[DetailedLogger] Logging enabled!
[DetailedLogger] Logs will be saved to: E:\ui-agent\logs\20260302_HHMMSS
[DetailedLogger] Debug screenshots (visual verification crops) will be saved to: E:\ui-agent\logs\20260302_HHMMSS\screenshots
```

### 3. Check Screenshots Directory
```bash
ls logs/20260302_HHMMSS/screenshots/
```

Should contain:
```
step_01_full.png          # Full screenshot (1920x1080)
step_01_resized.png       # Resized for AI (1024x576)
step_01_before.png        # Before action
step_01_after.png         # After action
verify_01_crop_0_numbered.png    # Candidate 0
verify_01_crop_1_numbered.png    # Candidate 1
verify_01_composite_numbered.png # All candidates
...
```

### 4. Open Verification Composites
```bash
# Open composite to see what Gemini analyzed
start logs/20260302_HHMMSS/screenshots/verify_01_composite_numbered.png
```

Should see: Grid of numbered options (0, 1, 2...) with colored borders

---

## Impact

**Before Fix:**
- ❌ No visual verification debug images saved
- ❌ User couldn't see what Gemini was analyzing
- ❌ Hard to debug why agent clicked wrong element
- ❌ No evidence of multiple candidates

**After Fix:**
- ✅ All verification crops saved to logs/screenshots/
- ✅ User can see exactly what Gemini analyzed
- ✅ Easy to debug visual verification failures
- ✅ Full transparency into disambiguation process

---

## Related Code

### Where Debug Screenshots Are Saved

**`core/vision_agent.py` line 1078-1082:**
```python
# Debug: save individual numbered crops
if self._debug_dir:
    self._verify_save_count += 1
    n = self._verify_save_count
    for i, crop, bbox in numbered_crops:
        crop.save(self._debug_dir / f"verify_{n:02d}_crop_{i}_numbered.png")
```

**`core/vision_agent.py` line 1112-1113:**
```python
# Debug: save composite
if self._debug_dir:
    composite.save(self._debug_dir / f"verify_{n:02d}_composite_numbered.png")
```

### Why It Works Now

**Before:**
- `self._debug_dir` only set if `VISION_DEBUG=1` env var (user didn't have it)
- All `if self._debug_dir:` checks failed
- No images saved

**After:**
- `self._debug_dir = self.logger.screenshots_dir` (always set in logged mode)
- All `if self._debug_dir:` checks pass
- Images saved to same directory as regular screenshots

---

## Success Criteria

✅ Console shows: "Debug screenshots (visual verification crops) will be saved to: ..."
✅ `verify_XX_crop_Y_numbered.png` files appear in logs/screenshots/
✅ `verify_XX_composite_numbered.png` files appear in logs/screenshots/
✅ User can see numbered candidates with colored borders
✅ User can understand why agent picked specific option

---

## Testing

```bash
# Run educational Excel test
python test_educational_excel.py

# Check latest log directory
ls -lt logs/ | head -1

# Check for verification screenshots
ls logs/<latest>/screenshots/verify_*.png

# Open composite to inspect
start logs/<latest>/screenshots/verify_01_composite_numbered.png
```

**Expected:** See numbered crops showing multiple candidates for "Blank workbook" or other elements.

---

**Fix complete. Visual verification debug screenshots now saving correctly.**
