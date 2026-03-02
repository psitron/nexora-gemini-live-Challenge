# 🔧 Install OCR - Fix Wrong Clicks

## Root Cause Found

```
[OCR not available: screen-ocr not installed]
```

**The agent is clicking in wrong places because OCR is not working!**

When OCR fails:
- Agent falls back to AI's "hint" coordinates
- AI's spatial understanding is poor (off by 200-400 pixels)
- Clicks miss the target

When OCR works:
- Finds exact text position on screen
- Clicks precisely on target
- **Success rate dramatically improves**

---

## Installation Steps

### Step 1: Install Python Packages ✅ DONE

```bash
pip install screen-ocr pytesseract pillow
```

**Status**: ✅ Installed

---

### Step 2: Install Tesseract OCR Binary

**Download from**:
https://github.com/UB-Mannheim/tesseract/wiki

**Recommended installer**:
`tesseract-ocr-w64-setup-5.3.3.20231005.exe` (64-bit Windows)

**Installation**:
1. Download installer
2. Run installer
3. **IMPORTANT**: Note the installation path (default: `C:\Program Files\Tesseract-OCR`)
4. Add to PATH or configure path in code

---

### Step 3: Configure Tesseract Path

**Option A: Add to PATH (Recommended)**

1. Open Windows Settings → System → About → Advanced system settings
2. Click "Environment Variables"
3. Under "System variables", find "Path"
4. Click "Edit"
5. Click "New"
6. Add: `C:\Program Files\Tesseract-OCR`
7. Click OK
8. **Restart terminal/IDE**

**Option B: Configure in Code**

Edit `core/ocr_finder.py`:
```python
import pytesseract

# Add this line at the top:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

---

### Step 4: Verify Installation

```bash
# Test if tesseract is accessible:
tesseract --version

# Should output:
# tesseract 5.3.3
#  leptonica-1.83.1
#  ...
```

---

### Step 5: Test OCR on Your Screenshot

```bash
python tools/test_ocr_on_screenshot.py logs/20260302_145003/screenshots/step_8_before.png "Blank workbook"
```

**Expected output**:
```
Testing OCR on: logs/20260302_145003/screenshots/step_8_before.png
Searching for: 'Blank workbook'
------------------------------------------------------------
Image size: 1920 x 1080

Searching for 'Blank workbook'...
✅ OCR found 1 match(es):
  Match 1: bbox=(47, 40, 43, 40)
           center=(68, 60)
           This is where the agent SHOULD click
```

**If it still fails**, check:
1. Is Tesseract installed?
2. Is it in PATH?
3. Restart terminal after PATH changes

---

## After OCR is Working

### Test the Agent Again

```bash
python test_educational_excel.py
```

**You should see**:
- OCR finds "Blank workbook" at correct position
- Agent clicks at (~65, ~70) instead of (249, 468)
- "Blank workbook" opens successfully
- Task completes!

---

## Alternative: Use Coordinate Validator Tool

If Tesseract installation is problematic, use the manual validator:

```bash
# Open in browser:
start tools/coordinate_validator.html
```

**Then**:
1. Upload screenshot
2. Mark where "Blank workbook" really is
3. Use those coordinates to fix the AI's grounding

But **OCR is the proper fix** - it automates this for every element.

---

## Quick Install Script (PowerShell)

```powershell
# Download Tesseract installer
Invoke-WebRequest -Uri "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe" -OutFile "$env:TEMP\tesseract-installer.exe"

# Run installer
Start-Process -FilePath "$env:TEMP\tesseract-installer.exe" -Wait

# Add to PATH
$tesseractPath = "C:\Program Files\Tesseract-OCR"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$tesseractPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$tesseractPath", "Machine")
    Write-Host "✅ Added Tesseract to PATH"
} else {
    Write-Host "✅ Tesseract already in PATH"
}

Write-Host "⚠️  Please restart your terminal for PATH changes to take effect"
```

---

## Why This Fixes Everything

### Before (OCR not working):
```
AI: "Blank workbook is at (133, 250)"  ← WRONG
    ↓ scale 1.875x
Agent clicks: (249, 468)  ← WRONG
Actual position: (65, 70)  ← Should be here
Result: MISS by 400 pixels ❌
```

### After (OCR working):
```
AI: "Blank workbook is at (133, 250)"  ← Still wrong, but...
OCR: "I found 'Blank workbook' at (65, 70)"  ← CORRECT!
Agent uses OCR coordinates: (65, 70)  ← CORRECT!
Result: HIT ✅
```

---

## Summary

1. ✅ Python packages installed (`pip install`)
2. ⏳ Tesseract binary needed (download + install)
3. ⏳ Add to PATH or configure path
4. ⏳ Test with `test_ocr_on_screenshot.py`
5. ⏳ Run agent test again

**Once OCR works, the agent will click accurately!**
