# Detailed Logging Verification Guide

**How to verify your agent is logging everything properly**

---

## 🎯 Quick Test (2 minutes)

```bash
# Run the quick logging test
python test_logging_quick.py
```

**Expected Output:**
```
[PASS] Logs directory exists: E:\ui-agent\logs\20260301_HHMMSS
[PASS] execution_report.html       (10,565 bytes)
[PASS] execution_log.txt           (4,949 bytes)
[PASS] execution_log.json          (4,440 bytes)
[PASS] Screenshots directory exists (6 images)

SUCCESS - ALL LOGS CREATED!

Open this file in your browser:
  E:\ui-agent\logs\20260301_HHMMSS\execution_report.html
```

---

## 📊 What Gets Logged

### Directory Structure:
```
logs/
└── 20260301_185030/           ← Timestamp folder
    ├── execution_report.html  ← Open this in browser!
    ├── execution_log.txt      ← Human-readable text
    ├── execution_log.json     ← Machine-readable JSON
    └── screenshots/           ← All images
        ├── step_1_before.png
        ├── step_1_after.png
        ├── step_2_before.png
        ├── step_2_after.png
        └── ...
```

### HTML Report Contains:
- **Dashboard**: Summary stats (total steps, success rate, duration)
- **Every Step**: Detailed breakdown with:
  - Action name and description
  - Exact timestamp
  - Duration in milliseconds
  - Success/failure status
  - Parameters used
  - Result data
  - Screenshot BEFORE action
  - Screenshot AFTER action
  - AI reflection analysis (if available)
  - LLM prompts and responses

---

## 🔍 Two Types of Agents with Logging

### 1. **VisionAgentLogged** (Vision-based)
**File**: `core/vision_agent_logged.py`

**Use for**: Tasks that need vision AI to understand screens

```python
from core.vision_agent_logged import VisionAgentLogged

agent = VisionAgentLogged()
result = agent.run("Open Excel and create a budget")
```

**What it logs:**
- Every vision AI analysis
- Every screenshot sent to AI
- Every action decision
- Every coordinate click
- Before/after screenshots
- AI responses

**Used in:**
- `test_educational_excel.py`
- `test_logging_quick.py`

---

### 2. **AgentLoopLogged** (Planning-based)
**File**: `core/agent_loop_logged.py`

**Use for**: Tasks that need upfront planning and structured execution

```python
from core.agent_loop_logged import AgentLoopLogged

agent = AgentLoopLogged()
result = agent.run("Create a Python project with tests")
```

**What it logs:**
- Planning phase (LLM breaks down goal into steps)
- Action mapping (steps → tool calls)
- Every tool execution
- Before/after screenshots
- Reflection agent analysis
- Outcome classification
- Knowledge gained

**Used in:**
- `test_complex_examples.py`

---

## ✅ Verification Checklist

### Step 1: Run a Test
```bash
# Quick test (1-2 minutes)
python test_logging_quick.py

# OR Educational Excel test (3-5 minutes)
python test_educational_excel.py

# OR Complex example (5-10 minutes)
python test_complex_examples.py
```

### Step 2: Check Console Output
You should see:
```
[DetailedLogger] Logging enabled!
[DetailedLogger] Logs will be saved to: E:\ui-agent\logs\20260301_185030

... (execution) ...

======================================================================
DETAILED LOGS AVAILABLE:
======================================================================
Open this file in your browser to see everything:
  E:\ui-agent\logs\20260301_185030\execution_report.html
======================================================================
```

**If you DON'T see this**, logging is NOT enabled!

### Step 3: Check Files Exist
```bash
# List recent logs
ls -la E:/ui-agent/logs/

# Check contents of most recent log
ls -la E:/ui-agent/logs/20260301_HHMMSS/
```

**Expected files:**
- `execution_report.html` (10-50 KB)
- `execution_log.txt` (5-20 KB)
- `execution_log.json` (5-20 KB)
- `screenshots/` directory with PNG files

**If files are MISSING**, check:
1. Is the agent using `*Logged` version?
2. Are there any errors in console?
3. Does `core/detailed_logger.py` exist?

### Step 4: Open HTML Report
```bash
# Open in default browser (Windows)
start E:\ui-agent\logs\20260301_HHMMSS\execution_report.html

# Or navigate manually:
# File Explorer → E:\ui-agent\logs\20260301_HHMMSS\execution_report.html
# Right-click → Open with → Chrome/Firefox/Edge
```

**What you should see:**
- Beautiful gradient header
- Dashboard with stats
- List of all steps
- Click any step to see:
  - Full details
  - Before/after screenshots
  - LLM interactions

---

## 🐛 Troubleshooting

### Problem 1: "Logs directory is empty"

**Cause**: Script is using regular agent, not logged version

**Fix**:
```python
# WRONG - No logging
from core.vision_agent import VisionAgent
agent = VisionAgent()

# CORRECT - With logging
from core.vision_agent_logged import VisionAgentLogged
agent = VisionAgentLogged()
```

**OR**:
```python
# WRONG - No logging
from core.agent_loop import AgentLoop
agent = AgentLoop()

# CORRECT - With logging
from core.agent_loop_logged import AgentLoopLogged
agent = AgentLoopLogged()
```

---

### Problem 2: "execution_report.html is empty or tiny"

**Cause**: Agent crashed before finalizing logs

**Fix**: Check for exceptions in console output

**Verify**:
```bash
# Check if JSON has content
cat E:/ui-agent/logs/20260301_HHMMSS/execution_log.json
```

If JSON is empty: Agent didn't complete any steps

---

### Problem 3: "No screenshots in screenshots/ directory"

**Cause**: Screenshot capture is failing

**Check**:
1. Is screen-ocr installed? `pip install screen-ocr`
2. Is mss installed? `pip install mss`
3. Are there permission errors?

**Test screenshot capture**:
```python
from perception.visual.screenshot import capture_selected_monitor
img = capture_selected_monitor()
print(f"Captured: {img.size}")
```

---

### Problem 4: "HTML report shows no steps"

**Cause**: Logger wasn't initialized or no actions were logged

**Fix**: Make sure you're calling `agent.run()`, not custom code

**Verify logger initialization**:
```python
agent = VisionAgentLogged()
print(f"Logger: {agent.logger}")  # Should NOT be None after run()
result = agent.run("test")
print(f"Logger: {agent.logger}")  # Should be DetailedLogger instance
```

---

## 📝 Manual Verification Steps

### 1. Check Logger Exists
```bash
ls -la E:/ui-agent/core/detailed_logger.py
ls -la E:/ui-agent/core/vision_agent_logged.py
ls -la E:/ui-agent/core/agent_loop_logged.py
```

All three should exist and be non-empty.

### 2. Test Logger Directly
```python
from core.detailed_logger import DetailedLogger

logger = DetailedLogger("Test task", "test_logs")
logger.log_custom(
    phase="test",
    action="test_action",
    details={"test": "data"},
    success=True
)
report_path = logger.finalize()
print(f"Report: {report_path}")
```

Should create `test_logs/execution_report.html`

### 3. Verify Imports Work
```python
# Test VisionAgentLogged import
try:
    from core.vision_agent_logged import VisionAgentLogged
    print("[PASS] VisionAgentLogged imports correctly")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")

# Test AgentLoopLogged import
try:
    from core.agent_loop_logged import AgentLoopLogged
    print("[PASS] AgentLoopLogged imports correctly")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
```

---

## 🎯 Complete Test Sequence

Run these in order to verify everything:

### Test 1: Quick Logging Test
```bash
python test_logging_quick.py
```
**Duration**: 30 seconds
**Verifies**: Basic logging functionality

### Test 2: Educational Excel (with logging)
```bash
python test_educational_excel.py
```
**Duration**: 3-5 minutes
**Verifies**: VisionAgentLogged with real task

### Test 3: Complex Example (with logging)
```bash
python test_complex_examples.py
# Choose option 1 (Project Setup)
```
**Duration**: 5-10 minutes
**Verifies**: AgentLoopLogged with multi-step task

---

## 📊 Expected Log Sizes

**For a typical 10-step task:**

| File | Size | Contains |
|------|------|----------|
| `execution_report.html` | 10-50 KB | Beautiful HTML |
| `execution_log.txt` | 5-20 KB | Human-readable text |
| `execution_log.json` | 5-20 KB | Machine-readable JSON |
| `screenshots/*.png` | ~100 KB each | 20-40 images (before/after) |

**Total**: ~2-5 MB per execution

---

## 🔍 Reading the Logs

### Text Log (execution_log.txt)
```
======================================================================
EXECUTION LOG
======================================================================
Goal: Open Excel and create a budget
Started: 2026-03-01T18:50:30.123456
======================================================================

Step 1 - INITIALIZATION: capture_initial_state
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time: 2026-03-01T18:50:30.123456
Duration: 45.23ms
Status: ✓ SUCCESS
...
```

### JSON Log (execution_log.json)
```json
{
  "goal": "Open Excel and create a budget",
  "start_time": "2026-03-01T18:50:30.123456",
  "steps": [
    {
      "step_number": 1,
      "phase": "initialization",
      "action": "capture_initial_state",
      "timestamp": "2026-03-01T18:50:30.123456",
      "duration_ms": 45.23,
      "success": true,
      ...
    }
  ]
}
```

### HTML Report (execution_report.html)
Open in browser → Interactive report with:
- Click to expand details
- View screenshots inline
- Filter by success/failure
- Search functionality

---

## ✅ Success Criteria

**Your logging is working if:**

✅ Console shows: `[DetailedLogger] Logging enabled!`
✅ `logs/` directory has timestamped folders
✅ Each folder has: HTML, TXT, JSON, screenshots/
✅ HTML report opens in browser and shows all steps
✅ Screenshots show actual desktop images
✅ Every action has before/after images
✅ LLM interactions are visible (if applicable)

---

## 🚀 Next Steps

Once logging is verified working:

1. **Run educational tasks** with `test_educational_excel.py`
2. **Review HTML reports** to understand agent behavior
3. **Debug failures** by looking at screenshots
4. **Optimize performance** using timing data
5. **Share reports** with students/colleagues

---

## 💡 Pro Tips

### Tip 1: Keep Logs Organized
```bash
# Create dated subdirectories
python test_educational_excel.py  # Logs to logs/YYYYMMDD_HHMMSS/

# Archive old logs
mkdir logs/archive
mv logs/2026* logs/archive/
```

### Tip 2: Compare Executions
```bash
# Open multiple reports side-by-side
start logs/20260301_180000/execution_report.html
start logs/20260301_183000/execution_report.html
```

### Tip 3: Extract Data from JSON
```python
import json

with open("logs/20260301_180000/execution_log.json") as f:
    data = json.load(f)

# Analyze timing
for step in data["steps"]:
    print(f"Step {step['step_number']}: {step['duration_ms']:.0f}ms")

# Count successes
successes = sum(1 for s in data["steps"] if s.get("success"))
print(f"Success rate: {successes}/{len(data['steps'])}")
```

---

## 📞 Still Having Issues?

If logging still doesn't work after following this guide:

1. **Check Python version**: `python --version` (needs 3.10+)
2. **Check dependencies**: `pip list | grep -E "Pillow|mss"`
3. **Check file permissions**: Can Python write to `E:\ui-agent\logs\`?
4. **Run with DEBUG_MODE**: Set `DEBUG_MODE=true` in .env
5. **Check for errors**: Look for exceptions in console output

---

**Your detailed logging system is powerful - use it to understand and improve your agent!** 📊
