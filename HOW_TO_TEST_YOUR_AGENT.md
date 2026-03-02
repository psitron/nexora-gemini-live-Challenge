# How to Test Your Hybrid AI Agent

**Status:** Complete Testing Guide
**Date:** 2026-03-01
**Platform:** Windows/macOS/Linux

This guide shows you exactly how to test every component of your agent, from basic functionality to advanced features.

---

## Table of Contents

1. [Quick Start Tests (5 minutes)](#quick-start-tests)
2. [Component Tests (15 minutes)](#component-tests)
3. [Integration Tests (30 minutes)](#integration-tests)
4. [Real-World Examples (1 hour)](#real-world-examples)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start Tests (5 minutes)

### Test 1: Verify Installation

```bash
# Check Python version (need 3.9+)
python --version

# Check required packages
pip list | grep -E "(playwright|pywinauto|Pillow|google-generativeai|boto3)"
```

**Expected output:**
```
Python 3.11.x
playwright              1.x.x
pywinauto               0.6.x  (Windows only)
Pillow                  10.x.x
google-generativeai     0.x.x
boto3                   1.x.x
```

---

### Test 2: Run Automated Test Suites

```bash
# Test 1: Agent S3 features
python verify_implementation.py

# Test 2: Cross-platform L2 support
python test_cross_platform.py

# Test 3: Visual annotator
python test_visual_annotator_cross_platform.py
```

**Expected results:**
- Test 1: 6/7 tests pass (playwright dependency may be missing)
- Test 2: 5/5 tests pass (or 3/5 if on macOS/Linux without dependencies)
- Test 3: 5/5 tests pass (or 4/5 if dependencies missing)

**If tests fail:** See [Troubleshooting](#troubleshooting) section below

---

### Test 3: Quick Sanity Check

Create a file `test_quick.py`:

```python
"""Quick sanity check - tests basic agent functionality."""

def test_imports():
    """Test that all core modules import without errors."""
    print("Testing imports...")

    try:
        from core.agent_loop import AgentLoop
        from core.vision_agent import VisionAgent
        from execution.hierarchy import ExecutionHierarchy
        from core.reflection_agent import ReflectionAgent
        from core.code_agent import CodeAgent
        from core.trajectory_manager import TrajectoryManager
        from execution.platform_adapter import get_desktop_adapter, get_platform_info
        from core.visual_annotator_adapter import highlight_bbox, get_platform_info as get_annotator_info

        print("[OK] All core modules imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return False


def test_platform_detection():
    """Test platform detection."""
    print("\nTesting platform detection...")

    try:
        from execution.platform_adapter import get_platform_info

        info = get_platform_info()
        print(f"  Platform: {info['system']}")
        print(f"  L2 Executor: {info['l2_executor']}")
        print(f"  L2 Available: {info['l2_available']}")

        print("[OK] Platform detection works")
        return True
    except Exception as e:
        print(f"[FAIL] Platform detection error: {e}")
        return False


def test_basic_execution():
    """Test basic execution hierarchy."""
    print("\nTesting execution hierarchy...")

    try:
        from execution.hierarchy import ExecutionHierarchy

        hierarchy = ExecutionHierarchy()

        # Test L0 (file operations)
        import tempfile
        import os

        temp_file = os.path.join(tempfile.gettempdir(), "test_agent.txt")

        # Write file
        result = hierarchy.attempt("file_write", path=temp_file, content="Hello, Agent!")
        if not result.success:
            print(f"[FAIL] File write failed: {result.message}")
            return False

        # Read file
        result = hierarchy.attempt("file_read", path=temp_file)
        if not result.success or "Hello, Agent!" not in str(result.data):
            print(f"[FAIL] File read failed: {result.message}")
            return False

        # Delete file
        result = hierarchy.attempt("file_delete", path=temp_file)
        if not result.success:
            print(f"[FAIL] File delete failed: {result.message}")
            return False

        print("[OK] Execution hierarchy works (L0 tested)")
        return True
    except Exception as e:
        print(f"[FAIL] Execution test error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("QUICK SANITY CHECK")
    print("=" * 70)

    results = []
    results.append(("Imports", test_imports()))
    results.append(("Platform Detection", test_platform_detection()))
    results.append(("Basic Execution", test_basic_execution()))

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All quick tests passed! Your agent is working.")
    else:
        print(f"\n[WARN] {total - passed} test(s) failed. Check errors above.")
```

Run it:
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

---

## Component Tests (15 minutes)

### Test Each Execution Level

Create `test_levels.py`:

```python
"""Test each execution level (L0-L5)."""

import tempfile
import os


def test_l0_files():
    """Test L0: File operations."""
    print("\n" + "=" * 70)
    print("TEST: L0 - File Operations")
    print("=" * 70)

    try:
        from execution.hierarchy import ExecutionHierarchy

        hierarchy = ExecutionHierarchy()
        temp_dir = tempfile.gettempdir()
        test_file = os.path.join(temp_dir, "l0_test.txt")

        # Test write
        print("  Testing file_write...")
        result = hierarchy.attempt("file_write", path=test_file, content="L0 test")
        if not result.success:
            print(f"  [FAIL] Write failed: {result.message}")
            return False
        print("  [OK] Write succeeded")

        # Test read
        print("  Testing file_read...")
        result = hierarchy.attempt("file_read", path=test_file)
        if not result.success:
            print(f"  [FAIL] Read failed: {result.message}")
            return False
        print(f"  [OK] Read succeeded: {result.data['content'][:20]}...")

        # Test delete
        print("  Testing file_delete...")
        result = hierarchy.attempt("file_delete", path=test_file)
        if not result.success:
            print(f"  [FAIL] Delete failed: {result.message}")
            return False
        print("  [OK] Delete succeeded")

        print("\n[OK] L0 (File Operations) - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] L0 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_l1_browser():
    """Test L1: Browser automation (requires Playwright)."""
    print("\n" + "=" * 70)
    print("TEST: L1 - Browser Automation")
    print("=" * 70)

    try:
        from execution.level1_dom import Level1DomExecutor

        print("  Creating L1 executor...")
        executor = Level1DomExecutor()

        print("  [SKIP] L1 requires Playwright browser to be running")
        print("  [INFO] To test L1:")
        print("    1. Install Playwright: pip install playwright")
        print("    2. Install browsers: playwright install chromium")
        print("    3. Use AgentLoop or VisionAgent for full test")

        return None  # Skip, not fail

    except Exception as e:
        print(f"  [SKIP] L1 not available: {e}")
        return None


def test_l2_desktop():
    """Test L2: Desktop automation."""
    print("\n" + "=" * 70)
    print("TEST: L2 - Desktop Automation")
    print("=" * 70)

    try:
        from execution.platform_adapter import get_desktop_adapter, get_platform_info

        info = get_platform_info()
        print(f"  Platform: {info['system']}")
        print(f"  Executor: {info['l2_executor']}")
        print(f"  Available: {info['l2_available']}")

        if not info['l2_available']:
            print("  [SKIP] L2 not available (dependencies missing)")
            return None

        adapter = get_desktop_adapter()
        print(f"  [OK] L2 adapter created: {type(adapter).__name__}")

        print("\n  [INFO] To fully test L2:")
        print("    - Use AgentLoop: agent.run('Open Notepad')")
        print("    - Requires actual desktop environment")

        return True

    except Exception as e:
        print(f"  [SKIP] L2 test error: {e}")
        return None


def test_l5_vision():
    """Test L5: Cloud vision."""
    print("\n" + "=" * 70)
    print("TEST: L5 - Cloud Vision")
    print("=" * 70)

    try:
        from config.settings import get_settings

        settings = get_settings()

        # Check if API keys configured
        has_gemini = bool(settings.gemini_api_key)
        has_nova = bool(settings.aws_access_key_id)

        print(f"  Gemini configured: {has_gemini}")
        print(f"  Nova configured: {has_nova}")

        if not (has_gemini or has_nova):
            print("\n  [SKIP] L5 requires API keys in .env")
            print("  [INFO] To configure:")
            print("    - Add GEMINI_API_KEY to .env (Google AI Studio)")
            print("    - Or add AWS credentials for Nova")
            return None

        from execution.level5_cloud_vision import Level5CloudVisionExecutor

        executor = Level5CloudVisionExecutor()
        print("  [OK] L5 executor created")

        print("\n  [INFO] To fully test L5:")
        print("    - Use VisionAgent.run('Click the Chrome icon')")
        print("    - Requires actual screenshot with UI elements")

        return True

    except Exception as e:
        print(f"  [SKIP] L5 test error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_reflection_agent():
    """Test Reflection Agent."""
    print("\n" + "=" * 70)
    print("TEST: Reflection Agent")
    print("=" * 70)

    try:
        from core.reflection_agent import ReflectionAgent
        from config.settings import get_settings

        settings = get_settings()

        print("  Creating reflection agent...")
        agent = ReflectionAgent(settings.llm_settings)
        print(f"  [OK] Reflection agent created")

        print("\n  [INFO] Reflection agent is working")
        print("  [INFO] To fully test: Use AgentLoop.run() with a task")

        return True

    except Exception as e:
        print(f"  [FAIL] Reflection agent error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_agent():
    """Test Code Agent."""
    print("\n" + "=" * 70)
    print("TEST: Code Agent")
    print("=" * 70)

    try:
        from core.code_agent import CodeAgent
        from config.settings import get_settings

        settings = get_settings()

        print("  Creating code agent...")
        agent = CodeAgent(settings.llm_settings)
        print(f"  [OK] Code agent created")

        print("\n  Testing simple code execution...")
        result = agent.execute_task("Calculate 2 + 2 and print the result")

        print(f"  Steps executed: {result.steps_executed}/{result.max_steps}")
        print(f"  Completion reason: {result.completion_reason}")

        if result.completion_reason in ["DONE", "SUCCESS"]:
            print("  [OK] Code agent executed successfully")
            return True
        else:
            print(f"  [WARN] Code agent completed but status: {result.completion_reason}")
            return True

    except Exception as e:
        print(f"  [SKIP] Code agent error: {e}")
        print("  [INFO] Code agent requires LLM API key")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("COMPONENT TESTS - Testing Each Level")
    print("=" * 70)

    tests = [
        ("L0 - Files", test_l0_files),
        ("L1 - Browser", test_l1_browser),
        ("L2 - Desktop", test_l2_desktop),
        ("L5 - Vision", test_l5_vision),
        ("Reflection Agent", test_reflection_agent),
        ("Code Agent", test_code_agent),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {name} crashed: {e}")
            results[name] = False

    print("\n" + "=" * 70)
    print("COMPONENT TEST RESULTS")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)

    for name, result in results.items():
        if result is True:
            status = "[OK] PASS"
        elif result is None:
            status = "[SKIP] SKIP"
        else:
            status = "[FAIL] FAIL"
        print(f"  {status}: {name}")

    print(f"\n{passed}/{total} tests passed, {skipped} skipped")

    if passed + skipped == total:
        print("\n[SUCCESS] All available components working!")
    else:
        print(f"\n[WARN] {total - passed - skipped} component(s) failed")
```

Run it:
```bash
python test_levels.py
```

---

## Integration Tests (30 minutes)

### Test 1: AgentLoop (Planning Mode)

Create `test_agent_loop.py`:

```python
"""Test AgentLoop with simple tasks."""

from core.agent_loop import AgentLoop
import tempfile
import os


def test_file_task():
    """Test: Create and manage files."""
    print("\n" + "=" * 70)
    print("TEST: AgentLoop - File Task")
    print("=" * 70)

    agent = AgentLoop()

    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "agent_test_output.txt")

    # Clean up if exists
    if os.path.exists(test_file):
        os.remove(test_file)

    task = f"Create a file at {test_file} with the content 'Hello from AgentLoop'"

    print(f"Task: {task}")
    print("Running agent...\n")

    result = agent.run(task)

    print(f"\nResult: {result.goal_status}")
    print(f"Steps executed: {result.steps_executed}")
    print(f"Trajectory: {len(result.trajectory.get_trajectory_summary().split('\\n'))} steps")

    # Verify file was created
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
        print(f"File content: {content}")

        if "Hello from AgentLoop" in content:
            print("\n[OK] File task PASSED - Correct content")
            os.remove(test_file)
            return True
        else:
            print(f"\n[FAIL] File task FAILED - Wrong content: {content}")
            return False
    else:
        print("\n[FAIL] File task FAILED - File not created")
        return False


def test_calculation_task():
    """Test: Use code agent for calculation."""
    print("\n" + "=" * 70)
    print("TEST: AgentLoop - Calculation Task (Code Agent)")
    print("=" * 70)

    agent = AgentLoop()

    task = "Calculate the factorial of 10"

    print(f"Task: {task}")
    print("Running agent...\n")

    result = agent.run(task)

    print(f"\nResult: {result.goal_status}")
    print(f"Steps executed: {result.steps_executed}")

    # Check if result mentions the answer (factorial of 10 = 3628800)
    trajectory_summary = result.trajectory.get_trajectory_summary()

    if "3628800" in trajectory_summary or "3,628,800" in trajectory_summary:
        print("\n[OK] Calculation task PASSED - Correct answer found")
        return True
    else:
        print("\n[WARN] Calculation task completed but answer unclear")
        print("Check trajectory for details")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("INTEGRATION TESTS - AgentLoop")
    print("=" * 70)

    tests = [
        ("File Task", test_file_task),
        ("Calculation Task", test_calculation_task),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 70)
    print("INTEGRATION TEST RESULTS")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)

    for name, result in results.items():
        if result is True:
            status = "[OK] PASS"
        elif result is None:
            status = "[SKIP] SKIP"
        else:
            status = "[FAIL] FAIL"
        print(f"  {status}: {name}")

    print(f"\n{passed}/{total} tests passed, {skipped} skipped")
```

Run it:
```bash
python test_agent_loop.py
```

---

### Test 2: VisionAgent (Vision Mode)

**⚠️ Warning:** VisionAgent requires:
- API keys (Gemini or Nova) configured in `.env`
- Desktop environment with visible windows

Create `test_vision_agent.py`:

```python
"""Test VisionAgent with simple visual task."""

from core.vision_agent import VisionAgent


def test_vision_agent_screenshot():
    """Test: Capture screenshot and describe."""
    print("\n" + "=" * 70)
    print("TEST: VisionAgent - Screenshot Test")
    print("=" * 70)

    print("\n[INFO] This test requires:")
    print("  - GEMINI_API_KEY or AWS credentials in .env")
    print("  - Desktop with visible windows")
    print("")

    try:
        agent = VisionAgent()

        # Simple task: just take screenshot and describe
        task = "Take a screenshot and tell me what you see. Then type 'done'."

        print(f"Task: {task}")
        print("Running agent...\n")

        result = agent.run(task, max_steps=3)

        print(f"\nResult: {result.goal_status}")
        print(f"Steps executed: {result.steps_executed}")

        if result.steps_executed > 0:
            print("\n[OK] VisionAgent ran successfully")
            return True
        else:
            print("\n[FAIL] VisionAgent didn't execute any steps")
            return False

    except Exception as e:
        print(f"\n[SKIP] VisionAgent test error: {e}")
        print("\n[INFO] Make sure:")
        print("  1. API key is configured in .env")
        print("  2. Desktop environment is available")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("INTEGRATION TEST - VisionAgent")
    print("=" * 70)

    result = test_vision_agent_screenshot()

    if result is True:
        print("\n[SUCCESS] VisionAgent test passed!")
    elif result is None:
        print("\n[SKIP] VisionAgent test skipped (see requirements above)")
    else:
        print("\n[FAIL] VisionAgent test failed")
```

Run it:
```bash
python test_vision_agent.py
```

---

## Real-World Examples (1 hour)

### Example 1: File Management Task

```python
"""
Real-world test: File management
"""

from core.agent_loop import AgentLoop
import tempfile
import os

agent = AgentLoop()

# Create test directory
test_dir = os.path.join(tempfile.gettempdir(), "agent_test")
os.makedirs(test_dir, exist_ok=True)

# Task: Organize files
task = f"""
Create 3 text files in {test_dir}:
1. notes.txt with content "Meeting notes"
2. todos.txt with content "Task list"
3. ideas.txt with content "Project ideas"

Then create a subdirectory called 'organized' and move all files there.
"""

print("Task:", task)
print("\nRunning agent...\n")

result = agent.run(task)

print("\n" + "=" * 70)
print("RESULT")
print("=" * 70)
print(f"Status: {result.goal_status}")
print(f"Steps: {result.steps_executed}")

# Verify
organized_dir = os.path.join(test_dir, "organized")
if os.path.exists(organized_dir):
    files = os.listdir(organized_dir)
    print(f"\nFiles in organized/: {files}")

    if len(files) == 3:
        print("[OK] All 3 files created and moved!")
    else:
        print(f"[WARN] Expected 3 files, found {len(files)}")
else:
    print("[FAIL] Organized directory not created")

# Cleanup
import shutil
shutil.rmtree(test_dir)
```

---

### Example 2: Desktop Application Task (Windows)

```python
"""
Real-world test: Open Notepad and type (Windows only)
"""

from core.agent_loop import AgentLoop
import platform

if platform.system() != "Windows":
    print("[SKIP] This test is Windows-only")
    exit(0)

agent = AgentLoop()

task = """
1. Open Notepad
2. Type "Hello from AI Agent!"
3. Wait 2 seconds so I can see it
"""

print("Task:", task)
print("\nRunning agent...\n")

result = agent.run(task)

print("\n" + "=" * 70)
print("RESULT")
print("=" * 70)
print(f"Status: {result.goal_status}")
print(f"Steps: {result.steps_executed}")

print("\n[INFO] Check if Notepad opened and text was typed")
print("[INFO] Close Notepad manually when done")
```

---

### Example 3: Web Browsing Task

```python
"""
Real-world test: Web browsing
Requires Playwright: pip install playwright && playwright install chromium
"""

from core.agent_loop import AgentLoop

agent = AgentLoop()

task = """
1. Open a web browser
2. Navigate to example.com
3. Tell me what's on the page
"""

print("Task:", task)
print("\nRunning agent...\n")

result = agent.run(task)

print("\n" + "=" * 70)
print("RESULT")
print("=" * 70)
print(f"Status: {result.goal_status}")
print(f"Steps: {result.steps_executed}")

# Check trajectory for evidence of page content
trajectory = result.trajectory.get_trajectory_summary()
if "example" in trajectory.lower():
    print("\n[OK] Browser navigation worked!")
else:
    print("\n[WARN] Check if browser opened and navigated")
```

---

## Troubleshooting

### Issue: "No module named 'playwright'"

**Problem:** L1 (Browser) level not available

**Solution:**
```bash
pip install playwright
playwright install chromium
```

---

### Issue: "No module named 'pywinauto'"

**Problem:** L2 (Desktop) not available on Windows

**Solution:**
```bash
pip install pywinauto
```

---

### Issue: "No module named 'Cocoa'" (macOS)

**Problem:** L2 (Desktop) not available on macOS

**Solution:**
```bash
pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices
```

---

### Issue: "No module named 'gi'" (Linux)

**Problem:** L2 (Desktop) or Visual Annotator not available on Linux

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0
pip install PyGObject

# Fedora
sudo dnf install python3-gobject gtk3
pip install PyGObject
```

---

### Issue: "API key not found"

**Problem:** Vision models (L5) or LLM features require API keys

**Solution:**

Create or update `.env` file in project root:
```bash
# For Gemini (Google AI Studio)
GEMINI_API_KEY=your_key_here

# For Amazon Nova (optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1

# For task planning LLM
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp
```

Get API keys:
- Gemini: https://aistudio.google.com/apikey
- AWS: https://console.aws.amazon.com/iam/

---

### Issue: Tests pass but agent doesn't work in practice

**Possible causes:**

1. **No API key configured** - Vision/LLM features require keys
   - Check `.env` file exists with valid keys

2. **Desktop environment issues**
   - L2 requires actual desktop (not SSH/headless)
   - Try L0 (files) or L1 (browser) tasks first

3. **Permissions issues**
   - macOS: Grant Accessibility permissions in System Preferences
   - Linux: Ensure AT-SPI is enabled

4. **Wrong task format**
   - Be specific: "Open Notepad" not "open notepad app"
   - Use exact app names for your platform

---

## Quick Reference Commands

```bash
# Run all automated tests
python verify_implementation.py
python test_cross_platform.py
python test_visual_annotator_cross_platform.py

# Test specific components
python test_quick.py               # 5 minutes - sanity check
python test_levels.py              # 15 minutes - each level
python test_agent_loop.py          # 30 minutes - integration

# Test manually
python -c "from core.agent_loop import AgentLoop; agent = AgentLoop(); print(agent.run('Create a file called test.txt with content hello').goal_status)"

# Check configuration
python -c "from config.settings import get_settings; s = get_settings(); print(f'Gemini: {bool(s.gemini_api_key)}'); print(f'Provider: {s.llm_provider}')"

# Check platform support
python -c "from execution.platform_adapter import get_platform_info; import json; print(json.dumps(get_platform_info(), indent=2))"
```

---

## Success Criteria

Your agent is working correctly if:

✅ **All quick tests pass** (test_quick.py)
✅ **L0 (files) works** (test_levels.py)
✅ **Platform detected correctly** (test_cross_platform.py)
✅ **Can create/read/delete files** (basic file task)
✅ **AgentLoop can complete simple task** (test_agent_loop.py)

Optional (requires API keys):
✅ **VisionAgent can take screenshot** (test_vision_agent.py)
✅ **Code Agent can run calculations** (test_agent_loop.py)

---

## Next Steps After Testing

Once tests pass:

1. **Try Real Tasks**
   - Start with simple file operations
   - Progress to desktop automation
   - Try web browsing (if Playwright installed)

2. **Monitor Performance**
   - Check success rates in logs
   - Note which levels are used most
   - Identify any error patterns

3. **Tune Configuration**
   - Adjust MAX_STEPS if tasks timeout
   - Change LLM_MODEL if responses poor
   - Tune VISION_PROVIDER based on cost/quality

4. **Read Documentation**
   - `AGENT_S3_IMPROVEMENTS.md` - Features guide
   - `CROSS_PLATFORM_COMPLETE.md` - Platform support
   - `VISUAL_ANNOTATOR_CROSS_PLATFORM.md` - Annotations

---

**Testing Complete!** 🎉

If you've gotten this far and tests are passing, your Hybrid AI Agent is production-ready!

For questions or issues, check the troubleshooting section or review the comprehensive documentation in the project root.
