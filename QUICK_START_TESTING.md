# Quick Start: Testing Your Agent

**Goal:** Get your agent tested in under 10 minutes

---

## Step 1: Run Quick Sanity Check (2 minutes)

This verifies basic functionality without requiring API keys:

```bash
python test_quick.py
```

**Expected output:**
```
======================================================================
QUICK SANITY CHECK
======================================================================
Testing imports...
[OK] All core modules imported successfully

Testing platform detection...
  Platform: Windows
  L2 Executor: Level2UiTreeExecutor
  L2 Available: True
[OK] Platform detection works

Testing execution hierarchy...
  Testing file_write...
  Testing file_read...
  Testing file_delete...
[OK] Execution hierarchy works (L0 tested)

======================================================================
RESULTS
======================================================================
  [OK] PASS: Imports
  [OK] PASS: Platform Detection
  [OK] PASS: Basic Execution

3/3 tests passed

[SUCCESS] All quick tests passed! Your agent is working.
```

✅ **If this passes, your core agent is working!**

---

## Step 2: Run All Automated Tests (10 minutes)

Run the master test suite:

```bash
python test_all.py
```

This runs all test suites in sequence:
- Quick sanity check
- Agent S3 features
- Cross-platform support
- Visual annotator
- Component tests
- Integration tests

**Some tests may be skipped if:**
- API keys not configured (VisionAgent, Code Agent)
- Dependencies not installed (Playwright, pywinauto, etc.)
- Desktop environment not available

**This is normal!** Skipped tests don't mean failure.

---

## Step 3: Test a Real Task (2 minutes)

Try a simple file task:

```bash
python -c "from core.agent_loop import AgentLoop; import tempfile, os; path = os.path.join(tempfile.gettempdir(), 'test.txt'); result = AgentLoop().run(f'Create a file at {path} with content: Hello World'); print(f'Status: {result.goal_status}'); print(f'Steps: {result.steps_executed}')"
```

**Expected output:**
```
[Planning task...]
[Executing actions...]
Status: SUCCESS
Steps: 3
```

✅ **If this works, your agent can complete real tasks!**

---

## Step 4: Check What's Available (1 minute)

See what features are enabled:

```bash
python -c "from execution.platform_adapter import get_platform_info; from config.settings import get_settings; info = get_platform_info(); s = get_settings(); print(f'\nPlatform: {info[\"system\"]}'); print(f'L2 Available: {info[\"l2_available\"]}'); print(f'Gemini Key: {bool(s.gemini_api_key)}'); print(f'AWS Key: {bool(s.aws_access_key_id)}'); print(f'\nYour agent has:'); print(f'  - File operations (L0): Always available'); print(f'  - Desktop automation (L2): {info[\"l2_available\"]}'); print(f'  - Vision/LLM features: {bool(s.gemini_api_key or s.aws_access_key_id)}')"
```

**Example output:**
```
Platform: Windows
L2 Available: True
Gemini Key: True
AWS Key: False

Your agent has:
  - File operations (L0): Always available
  - Desktop automation (L2): True
  - Vision/LLM features: True
```

---

## What If Tests Fail?

### "Import Error" or "Module Not Found"

**Install missing dependencies:**

```bash
# Core dependencies (always needed)
pip install Pillow pyautogui mss

# Windows desktop automation
pip install pywinauto

# Browser automation (optional)
pip install playwright
playwright install chromium

# macOS desktop automation (macOS only)
pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices

# Linux desktop automation (Linux only)
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0
pip install PyGObject
```

---

### "API Key Not Found" or Vision/LLM Features Don't Work

**Add API keys to `.env` file:**

Create `.env` in project root:
```bash
# For Gemini (recommended - free tier available)
GEMINI_API_KEY=your_key_here

# For Amazon Nova (optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1

# LLM Configuration
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp
VISION_PROVIDER=gemini
```

**Get API keys:**
- Gemini: https://aistudio.google.com/apikey (free tier: 15 requests/min)
- AWS: https://console.aws.amazon.com/iam/

---

### Tests Pass But Agent Doesn't Work

**Common issues:**

1. **No API key configured** - Vision/LLM features require keys
   ```bash
   # Check if configured
   python -c "from config.settings import get_settings; s = get_settings(); print(f'Gemini: {bool(s.gemini_api_key)}'); print(f'AWS: {bool(s.aws_access_key_id)}')"
   ```

2. **Wrong platform** - L2 desktop automation requires actual desktop (not SSH/headless)
   ```bash
   # Check L2 availability
   python -c "from execution.platform_adapter import get_platform_info; print(get_platform_info())"
   ```

3. **Task format** - Be specific in task descriptions
   ```
   Good: "Create a file at /tmp/test.txt with content: Hello"
   Bad: "make a file"
   ```

---

## What Works Without API Keys?

✅ **File operations (L0)** - Always works
```bash
python -c "from core.agent_loop import AgentLoop; import tempfile, os; result = AgentLoop().run(f'Create a file at {os.path.join(tempfile.gettempdir(), \"test.txt\")} with content: Test'); print(result.goal_status)"
```

✅ **Desktop automation (L2)** - Works if dependencies installed
```bash
# Windows
python -c "from core.agent_loop import AgentLoop; AgentLoop().run('Open Notepad')"

# macOS
python -c "from core.agent_loop import AgentLoop; AgentLoop().run('Open TextEdit')"

# Linux
python -c "from core.agent_loop import AgentLoop; AgentLoop().run('Open gedit')"
```

❌ **Vision features** - Requires API key
❌ **Task planning with LLM** - Requires API key
❌ **Code Agent** - Requires API key

---

## Next Steps After Testing

**If tests passed:**

1. ✅ Read full testing guide: `HOW_TO_TEST_YOUR_AGENT.md`
2. ✅ Try real-world examples (see guide)
3. ✅ Configure API keys for full functionality
4. ✅ Read feature documentation:
   - `AGENT_S3_IMPROVEMENTS.md` - Reflection, Memory, Code Agent
   - `CROSS_PLATFORM_COMPLETE.md` - Windows/macOS/Linux support
   - `VISUAL_ANNOTATOR_CROSS_PLATFORM.md` - Visual annotations

**If tests failed:**

1. ❌ Check error messages
2. ❌ Install missing dependencies (see above)
3. ❌ Review `HOW_TO_TEST_YOUR_AGENT.md` troubleshooting section
4. ❌ Make sure you're on Windows/macOS/Linux (not other OS)

---

## Summary: Testing Checklist

Run these commands in order:

```bash
# 1. Quick sanity check (2 min)
python test_quick.py

# 2. All automated tests (10 min)
python test_all.py

# 3. Simple file task (30 sec)
python -c "from core.agent_loop import AgentLoop; import tempfile, os; result = AgentLoop().run(f'Create file at {os.path.join(tempfile.gettempdir(), \"test.txt\")}: Hello'); print(result.goal_status)"

# 4. Check configuration (30 sec)
python -c "from execution.platform_adapter import get_platform_info; from config.settings import get_settings; info = get_platform_info(); s = get_settings(); print(f'Platform: {info[\"system\"]}'); print(f'L2: {info[\"l2_available\"]}'); print(f'API Keys: {bool(s.gemini_api_key or s.aws_access_key_id)}')"
```

**Total time: ~15 minutes**

✅ **If all pass, your agent is production-ready!**

---

## Quick Reference

| Test Command | What It Tests | Time | API Key Required? |
|-------------|---------------|------|------------------|
| `python test_quick.py` | Core functionality | 2 min | No |
| `python test_all.py` | Everything | 10 min | No (but some skip) |
| `python test_levels.py` | Each level (L0-L5) | 5 min | No (but L5 skips) |
| `python test_agent_loop.py` | Integration | 5 min | No (file task works) |
| `python verify_implementation.py` | Agent S3 features | 5 min | No |
| `python test_cross_platform.py` | Platform support | 5 min | No |
| `python test_visual_annotator_cross_platform.py` | Annotations | 2 min | No |

---

**Ready to start? Run:**

```bash
python test_quick.py
```

If that passes, you're good to go! 🚀
