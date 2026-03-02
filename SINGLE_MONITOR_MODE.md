# 🎯 Single Monitor Mode - Simplified Testing

**Date**: 2026-03-02
**Strategy**: Get it working perfectly on ONE monitor first, then add multi-monitor support.

---

## 🔧 Changes Made

### Updated `.env`:
```bash
# OLD: PRIMARY_MONITOR=3  (right monitor, offset +2400)
# NEW: PRIMARY_MONITOR=2  (middle monitor, offset 0)
```

### Why Monitor 2?

**Your Monitor Setup**:
```
Monitor 1 (LEFT):   (-2400, 0) to (0, 1350)    - 2400x1350
Monitor 2 (MIDDLE): (0, 0) to (1920, 1080)      - 1920x1080  ← SELECTED
Monitor 3 (RIGHT):  (2400, 0) to (4320, 1080)   - 1920x1080
```

**Monitor 2 Benefits**:
- ✅ Starts at **(0, 0)** - NO offset needed
- ✅ Standard **1920x1080** resolution
- ✅ Simple coordinate math: `screen_x = hint_x × 1.875`
- ✅ Eliminates multi-monitor complexity

---

## 📊 Coordinate Math (Single Monitor)

### With Monitor 2 (No Offset):

```
1. Screenshot captured: 1920 x 1080 pixels
2. Resized for AI: 1024 x 576 pixels
3. Scale factor: 1920 / 1024 = 1.8750x
4. Monitor offset: (0, 0) ← NO OFFSET!

Example transformation:
  AI returns: hint_x=512, hint_y=400 (in 1024x576 space)

  Scaling:
    screen_x = (512 × 1.8750) + 0 = 960
    screen_y = (400 × 1.8750) + 0 = 750

  Result: (960, 750) on monitor 2 ✓

  Validation:
    Is 960 in range [0, 1920]? YES ✓
    Is 750 in range [0, 1080]? YES ✓
```

**Much simpler than monitor 3!**

---

## 🧪 Testing Steps

### Step 1: Run Simple Test

```bash
python test_single_monitor.py
```

**What it does**:
- Performs ONE simple action (click search icon)
- Shows detailed coordinate logging
- Verifies coordinates are in correct range

**Watch for**:
1. **Screenshot dimensions**: Should show 1920x1080 → 1024x576
2. **Scale factor**: Should be 1.8750x
3. **Monitor offset**: Should be (0, 0)
4. **Coordinates**: Should be in range 0-1920 for x, 0-1080 for y
5. **Annotation**: Should appear in correct position on monitor 2
6. **Click**: Should happen at correct position on monitor 2

---

### Step 2: Check the Logs

After running the test, check:
```bash
logs/[latest]/execution_log.json
```

**Verify coordinates**:
```json
{
  "hint_x": [some value],  ← Should be 0-1920
  "hint_y": [some value]   ← Should be 0-1080
}
```

If coordinates are in this range → coordinate scaling is working! ✅

---

### Step 3: Run Full Excel Test

Once simple test works, try the full Excel test:
```bash
python test_educational_excel.py
```

**On monitor 2**, you should see:
- All annotations in correct positions
- All clicks working correctly
- Task completing successfully

---

## ✅ Expected Results

### Coordinate Ranges:

| Coordinate | Monitor 2 Range | Monitor 3 Range (old) |
|------------|----------------|----------------------|
| hint_x | **0 to 1920** | 2400 to 4320 |
| hint_y | **0 to 1080** | 0 to 1080 |

**Much easier to verify on monitor 2!**

---

## 🔍 Debugging Made Easy

### If something goes wrong on monitor 2:

**Problem 1: Coordinates still outside range (e.g., x=2500)**
- Issue: Still trying to use old monitor offset
- Fix: Restart Python (reload .env changes)

**Problem 2: Y coordinates > 1080 (e.g., y=1985)**
- Issue: AI returning coordinates from full 1080px image, not resized 576px
- Fix: Check resize logic in `_resize_screenshot()`

**Problem 3: Annotations still in wrong place**
- Issue: Visual annotator has separate DPI scaling bug
- Fix: Fix `core/visual_annotator.py`

---

## 🎯 Why Single Monitor First?

### Complexity Removed:

**Multi-Monitor Issues**:
- ❌ Need to calculate offsets (-2400, 0, +2400, etc.)
- ❌ Different monitor sizes (2400x1350 vs 1920x1080)
- ❌ Negative coordinates (monitor 1 is at -2400)
- ❌ Hard to tell if coordinates are right (is 2866 correct?)

**Single Monitor (Monitor 2)**:
- ✅ No offset (always starts at 0,0)
- ✅ Simple coordinate range (0-1920, 0-1080)
- ✅ Easy to verify (is 960 in range? YES!)
- ✅ Can isolate coordinate scaling vs annotation bugs

---

## 🚀 Next Steps

### Option A: If Single Monitor Works ✅

Then multi-monitor is just adding the offset back:
```python
screen_x = (hint_x × scale) + monitor_offset_x
screen_y = (hint_y × scale) + monitor_offset_y
```

**This already works in the code!** Just change back to `PRIMARY_MONITOR=3`.

---

### Option B: If Single Monitor Fails ❌

Then we know the issue is NOT multi-monitor offset, but something else:
- Resize logic wrong
- AI returning wrong coordinates
- Visual annotator DPI scaling
- OCR coordinate finding

**Much easier to debug on single monitor!**

---

## 📝 Quick Reference

### Current Settings:
```bash
PRIMARY_MONITOR=2        # Middle monitor (0,0 to 1920,1080)
EDUCATIONAL_MODE=true    # Visible mouse movements
DEBUG_MODE=true          # Save debug screenshots
```

### Test Commands:
```bash
# Simple test (one action)
python test_single_monitor.py

# Math verification
python test_coordinate_scaling.py

# Full Excel test
python test_educational_excel.py
```

### Check Logs:
```bash
# View latest log
cat logs/$(ls -t logs/ | head -1)/execution_log.json

# Check coordinates are in range
grep "hint_x" logs/$(ls -t logs/ | head -1)/execution_log.json
```

---

## 🎉 Goal

**Get 100% working on monitor 2, THEN add multi-monitor support back.**

**Benefits**:
1. Easier to debug
2. Faster to verify
3. Clear success criteria
4. Foundation for multi-monitor

---

**Status**: Ready to test on single monitor (monitor 2)
**Next**: Run `python test_single_monitor.py`
