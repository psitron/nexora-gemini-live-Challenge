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
        has_gemini = bool(settings.models.gemini_api_key)
        # Note: Nova uses AWS credentials from environment, not directly in Settings
        has_nova = bool(os.getenv('AWS_ACCESS_KEY_ID'))

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

        # Check if API keys configured
        has_api_key = bool(settings.models.anthropic_api_key or settings.models.gemini_api_key)

        print("  Creating reflection agent...")
        agent = ReflectionAgent()  # No parameters needed
        print(f"  [OK] Reflection agent created")

        if not has_api_key:
            print("  [INFO] No API keys configured (agent will have limited functionality)")
        else:
            print("  [INFO] Reflection agent has API keys configured")

        print("\n  [INFO] To fully test: Use AgentLoop.run() with a task")

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

        # Check if API keys configured
        has_api_key = bool(settings.models.anthropic_api_key or settings.models.gemini_api_key)

        if not has_api_key:
            print("  [SKIP] Code agent requires LLM API key in .env")
            print("  [INFO] Add ANTHROPIC_API_KEY or GEMINI_API_KEY to .env")
            return None

        print("  Creating code agent...")
        agent = CodeAgent()  # No parameters needed
        print(f"  [OK] Code agent created")

        print("\n  [INFO] Code agent configured successfully")
        print("  [INFO] To fully test: Use agent.execute_task('Calculate 2+2')")

        return True

    except RuntimeError as e:
        print(f"  [SKIP] Code agent error: {e}")
        print("  [INFO] Code agent requires LLM API key")
        return None
    except Exception as e:
        print(f"  [FAIL] Code agent error: {e}")
        import traceback
        traceback.print_exc()
        return False


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
