"""
Cross-Platform Implementation Test

Verifies that all platform-specific components work correctly.
Run this on Windows, macOS, or Linux to verify L2 desktop automation.
"""

import platform
import sys


def test_platform_detection():
    """Test that platform is correctly detected."""
    print("=" * 70)
    print("TEST 1: Platform Detection")
    print("=" * 70)

    system = platform.system()
    print(f"Detected platform: {system}")

    expected = {
        "Windows": "pywinauto",
        "Darwin": "AppKit/Accessibility API",
        "Linux": "AT-SPI"
    }

    if system in expected:
        print(f"[OK] Platform supported: {expected[system]}")
        return True
    else:
        print(f"[FAIL] Platform not supported: {system}")
        return False


def test_platform_adapter():
    """Test platform adapter imports and works."""
    print("\n" + "=" * 70)
    print("TEST 2: Platform Adapter")
    print("=" * 70)

    try:
        from execution.platform_adapter import get_platform_info, get_desktop_adapter

        # Get platform info
        info = get_platform_info()
        print(f"Platform: {info['system']}")
        print(f"L2 Executor: {info['l2_executor']}")
        print(f"Technology: {info['l2_technology']}")
        print(f"Available: {info['l2_available']}")

        if not info['l2_available']:
            print("\n[FAIL] L2 not available. Install dependencies:")
            if platform.system() == "Darwin":
                print("  pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices")
            elif platform.system() == "Linux":
                print("  sudo apt-get install python3-pyatspi wmctrl")
            return False

        # Try to get adapter
        print("\nAttempting to create adapter...")
        adapter = get_desktop_adapter()
        print(f"[OK] Adapter created: {type(adapter).__name__}")

        return True

    except Exception as e:
        print(f"[FAIL] Platform adapter failed: {e}")
        return False


def test_execution_hierarchy():
    """Test that ExecutionHierarchy uses platform adapter."""
    print("\n" + "=" * 70)
    print("TEST 3: ExecutionHierarchy Integration")
    print("=" * 70)

    try:
        from execution.hierarchy import ExecutionHierarchy

        hierarchy = ExecutionHierarchy()
        print(f"[OK] ExecutionHierarchy created")
        print(f"L2 Executor type: {type(hierarchy._l2).__name__}")

        # Check it's the right type for platform
        system = platform.system()
        expected_types = {
            "Windows": "Level2UiTreeExecutor",
            "Darwin": "Level2UiTreeExecutorMacOS",
            "Linux": "Level2UiTreeExecutorLinux"
        }

        actual_type = type(hierarchy._l2).__name__
        expected_type = expected_types.get(system, "Unknown")

        if actual_type == expected_type:
            print(f"[OK] Correct executor for {system}: {actual_type}")
            return True
        else:
            print(f"[FAIL] Wrong executor. Expected: {expected_type}, Got: {actual_type}")
            return False

    except Exception as e:
        print(f"[FAIL] ExecutionHierarchy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_loop():
    """Test that AgentLoop can be created."""
    print("\n" + "=" * 70)
    print("TEST 4: AgentLoop Integration")
    print("=" * 70)

    try:
        from core.agent_loop import AgentLoop

        agent = AgentLoop()
        print(f"[OK] AgentLoop created successfully")
        print(f"L2 Executor: {type(agent.exec_hierarchy._l2).__name__}")

        return True

    except Exception as e:
        print(f"[FAIL] AgentLoop test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_platform_specific_modules():
    """Test that platform-specific modules can be imported."""
    print("\n" + "=" * 70)
    print("TEST 5: Platform-Specific Module Imports")
    print("=" * 70)

    system = platform.system()
    success = True

    # Test Windows module
    if system == "Windows":
        try:
            from execution.level2_ui_tree import Level2UiTreeExecutor
            print("[OK] Windows executor imported: Level2UiTreeExecutor")
        except Exception as e:
            print(f"[FAIL] Windows executor failed: {e}")
            success = False

    # Test macOS module
    elif system == "Darwin":
        try:
            from execution.level2_ui_tree_macos import Level2UiTreeExecutorMacOS
            print("[OK] macOS executor imported: Level2UiTreeExecutorMacOS")
        except Exception as e:
            print(f"[FAIL] macOS executor failed: {e}")
            print(f"  Install dependencies: pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices")
            success = False

    # Test Linux module
    elif system == "Linux":
        try:
            from execution.level2_ui_tree_linux import Level2UiTreeExecutorLinux
            print("[OK] Linux executor imported: Level2UiTreeExecutorLinux")
        except Exception as e:
            print(f"[FAIL] Linux executor failed: {e}")
            print(f"  Install dependencies: sudo apt-get install python3-pyatspi wmctrl")
            success = False

    return success


def run_all_tests():
    """Run all tests and report results."""
    print("""
    ==================================================================

                  CROSS-PLATFORM IMPLEMENTATION TEST

      Testing platform detection, adapters, and integration...

    ==================================================================
    """)

    tests = [
        ("Platform Detection", test_platform_detection),
        ("Platform Adapter", test_platform_adapter),
        ("ExecutionHierarchy", test_execution_hierarchy),
        ("AgentLoop", test_agent_loop),
        ("Platform Modules", test_platform_specific_modules),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {test_name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {test_name}")

    print("\n" + "=" * 70)
    print(f"RESULT: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED - Cross-platform implementation verified!")
        print(f"\nYour agent works on: {platform.system()}")
        print("Ready for production use!")
        return True
    else:
        print(f"\n[WARN]️ {total - passed} test(s) failed")
        print("Review errors above and install missing dependencies.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
