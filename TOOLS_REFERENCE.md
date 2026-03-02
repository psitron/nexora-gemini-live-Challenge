# 🛠️ Tools Reference

Quick guide to all diagnostic and testing tools created.

---

## Diagnostic Tools

### 1. `tools/diagnostic_full.py`

**Purpose:** Check what's currently broken

**Usage:**
```bash
python tools/diagnostic_full.py
```

**What it checks:**
- Tesseract OCR installation
- OCR Python integration
- OCR accuracy on actual screenshots
- Loop detection code exists
- Loop detection triggered in last run
- Reflection agent integration

**Output:**
- ✅ or ❌ for each component
- List of issues found
- Suggested next steps

**When to use:**
- Before starting any fixes
- After installing Tesseract
- After making any code changes
- To verify system state

---

### 2. `tools/test_ocr_on_screenshot.py`

**Purpose:** Test if OCR can find specific text in a screenshot

**Usage:**
```bash
python tools/test_ocr_on_screenshot.py <screenshot_path> "<search_text>"
```

**Example:**
```bash
python tools/test_ocr_on_screenshot.py logs/20260302_153038/screenshots/step_8_before.png "Blank workbook"
```

**Output:**
- ✅ Found: Shows coordinates where text was found
- ❌ Not found: Explains why OCR failed

**When to use:**
- After installing Tesseract
- To verify OCR works on specific image
- To get exact coordinates of text
- To debug OCR issues

---

### 3. `tools/coordinate_validator.html`

**Purpose:** Manually mark and extract coordinates from screenshots

**Usage:**
1. Open in browser: `start tools/coordinate_validator.html`
2. Upload screenshot
3. Click where element is located
4. Extract coordinates

**Features:**
- Interactive clicking to mark positions
- Shows grid overlay
- Displays real-time mouse coordinates
- Copy coordinates to clipboard
- Calculate bbox for 40x40 marker box

**When to use:**
- To verify OCR coordinates are correct
- To find exact position of UI elements
- To compare with agent's logged coordinates
- To debug coordinate transformation issues

---

### 4. `tools/test_phase_runner.py`

**Purpose:** Guide through step-by-step testing process

**Usage:**
```bash
python tools/test_phase_runner.py
```

**What it does:**
- Interactive questionnaire
- Guides through each testing phase
- Asks for verification at each step
- Prevents skipping phases

**Phases:**
1. Diagnostics
2. OCR verification
3. Loop detection check
4. Reflection accuracy
5. Integration test

**When to use:**
- After running diagnostics
- When following the testing plan
- To ensure nothing is skipped

---

## Testing Scripts

### 5. `test_educational_excel.py`

**Purpose:** Full integration test (already exists)

**Usage:**
```bash
python test_educational_excel.py
```

**What it does:**
- Runs complete Excel budget task
- Opens Excel, creates spreadsheet
- Tests full agent workflow

**When to use:**
- After all individual components verified
- For end-to-end testing
- To verify task completion

---

## Documentation Files

### 6. `ACTION_PLAN_START_HERE.md`

**What it is:** Step-by-step action plan

**Contents:**
- What to do first (diagnostics)
- How to fix each issue
- Testing procedures
- Communication protocol

**When to read:**
- Before starting any work
- To understand the process
- As reference during fixes

---

### 7. `FIXES_IMPLEMENTED_20260302.md`

**What it is:** Documentation of logging fixes

**Contents:**
- What was fixed (coordinate logging, reflection logging, etc.)
- Before/after log formats
- How to verify fixes

**When to read:**
- To understand what logging improvements were made
- To verify log format is correct

---

### 8. `ROOT_CAUSE_FOUND.md`

**What it is:** Analysis of why clicks are wrong

**Contents:**
- Evidence from logs and screenshots
- Root cause: OCR not working
- Explanation of how agent works
- Fix instructions

**When to read:**
- To understand the core problem
- To see evidence and analysis

---

### 9. `INSTALL_OCR_FIX.md`

**What it is:** Tesseract installation guide

**Contents:**
- Why OCR is needed
- Installation steps
- Configuration instructions
- Verification tests

**When to read:**
- When diagnostic says "Tesseract not installed"
- To fix OCR issues

---

### 10. `COORDINATE_PROBLEM_ANALYSIS.md`

**What it is:** Technical analysis of coordinate issues

**Contents:**
- Evidence from logs
- Coordinate transformation pipeline
- Why AI coordinates are wrong
- Possible fixes

**When to read:**
- To understand coordinate system
- For technical deep dive

---

### 11. `BEFORE_AFTER_COMPARISON.md`

**What it is:** Side-by-side log comparison

**Contents:**
- Log format before fixes
- Log format after fixes
- Verification examples

**When to read:**
- To see what improved logging looks like
- To verify your logs match expected format

---

## Quick Reference Commands

### Check System State
```bash
# Full diagnostic
python tools/diagnostic_full.py

# Check Tesseract
tesseract --version

# Test OCR on screenshot
python tools/test_ocr_on_screenshot.py <path> "text"
```

### Run Tests
```bash
# Phased testing guide
python tools/test_phase_runner.py

# Full integration test
python test_educational_excel.py
```

### Check Logs
```bash
# Find latest log
ls -lt logs/ | head -5

# Check for loops
grep "Blank workbook" logs/<latest>/execution_log.txt

# Check reflection output
grep "REFLECTION" logs/<latest>/execution_log.txt

# Check coordinates
grep "coordinates" logs/<latest>/execution_log.json | head -20
```

---

## Workflow Summary

**1. Start:**
```bash
python tools/diagnostic_full.py
```

**2. If OCR broken:**
- Install Tesseract
- Run: `tesseract --version`
- Test: `python tools/test_ocr_on_screenshot.py ...`

**3. If loop detection broken:**
- Add debug logging
- Run test
- Analyze output
- Fix bug

**4. Verify each fix:**
- Re-run diagnostic
- Should show ✅ for fixed component

**5. Integration test:**
```bash
python test_educational_excel.py
```

**6. Verify results:**
- Check logs/screenshots
- Use coordinate validator if needed

---

## Getting Help

**If diagnostic shows error you don't understand:**
- Share full diagnostic output
- Include any error messages
- Note what you tried

**If test fails:**
- Share test output
- Share relevant log files
- Share screenshots if applicable

**If not sure what to do next:**
- Check ACTION_PLAN_START_HERE.md
- Run test_phase_runner.py
- Ask before making changes
