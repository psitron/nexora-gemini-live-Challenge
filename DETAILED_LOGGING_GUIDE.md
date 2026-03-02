

# Detailed Logging Guide

**Complete Behind-the-Scenes Logging for Your AI Agent**

This guide shows you how to see EVERYTHING your agent does - every step, every screenshot, every decision.

---

## 🚀 Quick Start

### Run Complex Examples (Easiest Way)

```bash
python test_complex_examples.py
```

**Choose from:**
1. Complete Project Setup (⭐⭐⭐)
2. Data Processing Workflow (⭐⭐⭐⭐)
3. Documentation Generator (⭐⭐⭐)
4. Meeting Management System (⭐⭐⭐⭐)

Each example will create a `logs/` folder with:
- ✅ HTML report (open in browser!)
- ✅ Screenshots of every step
- ✅ Text log (human-readable)
- ✅ JSON log (machine-readable)

---

## 📊 What You Get

### After running an example, you'll find:

```
logs/20260301_143052/
├── execution_report.html      ← Open this in your browser!
├── execution_log.txt           ← Human-readable text
├── execution_log.json          ← Machine-readable JSON
└── screenshots/
    ├── step_1_before.png       ← Screenshot before action
    ├── step_1_after.png        ← Screenshot after action
    ├── step_2_before.png
    ├── step_2_after.png
    └── ... (all screenshots)
```

---

## 🌟 The HTML Report

The HTML report shows **EVERYTHING**:

### 📈 Summary Dashboard
- Total steps executed
- Successful vs failed actions
- Total execution time
- Quick statistics

### 🔍 Step-by-Step Details

For each step:
- ✅ **Timestamp** - Exact time of execution
- ✅ **Action name** - What action was performed
- ✅ **Parameters** - All input parameters
- ✅ **Result** - Success/failure with message
- ✅ **Duration** - How long it took (milliseconds)
- ✅ **Screenshots** - Before and after images
- ✅ **Reflection** - AI analysis of what happened
- ✅ **LLM Prompts** - What was sent to the AI
- ✅ **LLM Responses** - What the AI replied

### Example Screenshot from Report:

```
Step 3 - EXECUTION: file_write
Time: 2026-03-01T14:30:52.123456
Duration: 45.23ms
Status: SUCCESS

Details:
  action: file_write
  parameters: {'path': 'C:\\temp\\project\\README.md', 'content': '# My Project...'}
  result: File written successfully
  success: True

Screenshot Before:
  [Image showing desktop before action]

Screenshot After:
  [Image showing file created]

Reflection:
  Action succeeded: True
  Progress: progressing
  Observations: File was created successfully at the specified path
  Confidence: 95%
```

---

## 💻 Using Detailed Logging in Your Code

### Basic Usage

```python
from core.agent_loop_logged import AgentLoopLogged

# Create agent with logging
agent = AgentLoopLogged()

# Run any task
result = agent.run("Create a file at C:/temp/test.txt with content: Hello World")

# Logs are automatically created!
# Check the console output for the logs directory path
```

### Custom Log Directory

```python
# Specify where to save logs
agent = AgentLoopLogged(log_dir="my_custom_logs")

result = agent.run("Your task here")
```

---

## 📝 Understanding the Logs

### Text Log Format

```
================================================================================
Step 1 - PLANNING: generate_plan
Time: 2026-03-01T14:30:50.000000
Duration: 234.56ms
Status: SUCCESS

Details:
  plan: Plan with 3 steps
  llm_prompt: Plan this task: Create a file...
  llm_response: Generated plan with 3 steps

  LLM Prompt:
  ----------------------------------------------------------------------
  Plan this task: Create a file at C:/temp/test.txt
  [... full prompt ...]

  LLM Response:
  ----------------------------------------------------------------------
  Step 1: Create the file
  Step 2: Write content
  Step 3: Verify creation
================================================================================
```

### JSON Log Format

```json
{
  "task_name": "Create a file...",
  "start_time": "2026-03-01T14:30:50",
  "total_steps": 5,
  "entries": [
    {
      "timestamp": "2026-03-01T14:30:50.123456",
      "step_number": 1,
      "phase": "planning",
      "action": "generate_plan",
      "details": {
        "plan": "...",
        "llm_prompt": "...",
        "llm_response": "..."
      },
      "success": true,
      "duration_ms": 234.56,
      "screenshot_path": null,
      "error": null
    },
    ...
  ]
}
```

---

## 🎯 What Gets Logged

### Planning Phase
- ✅ Task description
- ✅ Generated plan
- ✅ LLM prompt used
- ✅ LLM response
- ✅ Number of steps

### Execution Phase
For each action:
- ✅ Action name (e.g., "file_write", "desktop_click")
- ✅ All parameters passed
- ✅ Result (success/failure)
- ✅ Error message (if failed)
- ✅ Screenshot before action
- ✅ Screenshot after action
- ✅ Execution time

### Reflection Phase
For each action:
- ✅ Did action succeed?
- ✅ Did state change?
- ✅ Progress assessment
- ✅ Observations about what changed
- ✅ Next action guidance
- ✅ Confidence level

### Finalization Phase
- ✅ Overall success/failure
- ✅ Total steps executed
- ✅ Total actions performed
- ✅ Knowledge gained
- ✅ Final state screenshot

---

## 📸 Screenshots

### What Gets Captured:
- Initial desktop state (before starting)
- Before each action
- After each action
- Final desktop state (after completion)

### Screenshot Naming:
- `step_1_before.png` - Before first action
- `step_1_after.png` - After first action
- `step_2_before.png` - Before second action
- `step_2_after.png` - After second action
- etc.

---

## 🔍 Analyzing Logs

### Common Questions You Can Answer:

**"What actions did the agent perform?"**
- Check execution_log.txt or HTML report
- Each action listed with full details

**"Did action X succeed?"**
- Look for the action in the log
- Check the "success" field
- Read the result message

**"What did the screen look like when it failed?"**
- Open HTML report
- Find the failed step
- View the "before" and "after" screenshots

**"What did the AI decide to do and why?"**
- Check the reflection sections
- Read "observations" and "next_action_guidance"
- View LLM prompts/responses

**"How long did each step take?"**
- Every entry has "duration_ms"
- HTML report shows timing for all steps

---

## 🎨 Example Use Cases

### Debugging a Failed Task

```python
agent = AgentLoopLogged(log_dir="debug_session")

result = agent.run("Open Notepad and type Hello")

# If it fails, check:
# 1. HTML report - see exactly what happened
# 2. Screenshots - see desktop state at each step
# 3. Error messages - understand why it failed
# 4. LLM prompts - see what AI was trying to do
```

### Demonstrating Capabilities

```python
# Run complex example
agent = AgentLoopLogged(log_dir="demo_for_client")

result = agent.run("Create complete project structure...")

# Share the HTML report with others
# Shows professional, detailed execution log
```

### Understanding Performance

```python
# Log a task
agent = AgentLoopLogged(log_dir="performance_test")

result = agent.run("Process 10 files...")

# Check JSON log for timing analysis:
# - Which steps were slowest?
# - Where did reflection take time?
# - Total execution time breakdown
```

---

## 🚀 Complex Examples Explained

### Example 1: Project Setup (⭐⭐⭐)

**What it tests:**
- Creating multiple directories
- Writing multiple files
- Different file formats (Python, Markdown, INI)
- Complex multi-step workflow

**Expected logs:**
- 10-15 action steps
- Screenshots showing file explorer
- Reflection confirming each file created

---

### Example 2: Data Processing (⭐⭐⭐⭐)

**What it tests:**
- CSV-style data files
- Processing scripts
- Report generation
- Directory organization

**Expected logs:**
- 15-20 action steps
- Multiple file creations
- Sequential task execution

---

### Example 3: Documentation (⭐⭐⭐)

**What it tests:**
- Markdown formatting
- Structured documentation
- Multiple related files
- Content organization

**Expected logs:**
- 8-12 action steps
- Documentation file creations
- Formatted markdown content

---

### Example 4: Meeting Management (⭐⭐⭐⭐)

**What it tests:**
- Complex file hierarchies
- Template generation
- Task tracking
- Multi-file workflows

**Expected logs:**
- 12-18 action steps
- Directory structure creation
- Multiple markdown files

---

## 💡 Tips for Best Results

### 1. Run Examples First
Start with the provided examples to understand the log format:
```bash
python test_complex_examples.py
```

### 2. Always Check HTML Report
The HTML report is the easiest way to see everything:
- Open execution_report.html in any browser
- Beautiful formatting
- All details in one place

### 3. Use Screenshots for Debugging
If something went wrong:
- Look at the "before" screenshot
- Compare to "after" screenshot
- See exactly what changed (or didn't)

### 4. Read Reflections
The reflection agent analyzes each action:
- Did it succeed?
- What changed?
- Should we continue?

### 5. Check Timing
If tasks are slow:
- Look at duration_ms for each step
- Find bottlenecks
- Optimize slow operations

---

## 📊 Log File Sizes

**Typical sizes for complex tasks:**

| Task Complexity | Text Log | JSON Log | Screenshots | Total |
|----------------|----------|----------|-------------|-------|
| Simple (5 steps) | 10 KB | 15 KB | 5 MB | ~5 MB |
| Medium (15 steps) | 30 KB | 45 KB | 15 MB | ~15 MB |
| Complex (30 steps) | 60 KB | 90 KB | 30 MB | ~30 MB |

**Note:** Screenshots are the largest component (1-2 MB each)

---

## 🎯 Quick Reference

**Start logging:**
```python
from core.agent_loop_logged import AgentLoopLogged
agent = AgentLoopLogged()
result = agent.run("Your task")
```

**Run examples:**
```bash
python test_complex_examples.py
```

**View logs:**
1. Check console for logs directory path
2. Open `execution_report.html` in browser
3. Browse screenshots in `screenshots/` folder

**Analyze:**
- HTML: Visual, complete overview
- Text: Quick grep/search
- JSON: Programmatic analysis
- Screenshots: Visual debugging

---

## 🎉 Summary

With detailed logging, you can:

✅ **See every action** the agent performs
✅ **Understand decisions** via reflection analysis
✅ **Debug failures** with before/after screenshots
✅ **Measure performance** with precise timing
✅ **Demonstrate capabilities** with professional reports
✅ **Learn how it works** by seeing behind the scenes

**Start now:**
```bash
python test_complex_examples.py
```

Choose any example, run it, and open the HTML report in your browser!

---

## 📞 Need Help?

**Check these files:**
- This guide: `DETAILED_LOGGING_GUIDE.md`
- Complex examples: `test_complex_examples.py`
- Logger source: `core/detailed_logger.py`
- Logged agent: `core/agent_loop_logged.py`

**Common issues:**
- "No screenshots captured" → Install `mss` package: `pip install mss`
- "Logs not created" → Check console output for errors
- "HTML report blank" → Check JSON log for raw data

---

**Happy logging!** 🎉

Now you can see exactly what your AI agent is doing at every step!
