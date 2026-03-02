"""
Master Test Runner - Runs all test suites in sequence

This script runs all available test suites and provides a comprehensive
report of your agent's functionality.

Usage:
    python test_all.py
"""

import sys
import subprocess


def run_test_script(script_name, description):
    """Run a test script and return success status."""
    print("\n" + "=" * 70)
    print(f"RUNNING: {description}")
    print("=" * 70)
    print(f"Script: {script_name}\n")

    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True
        )

        success = result.returncode == 0

        if success:
            print(f"\n[OK] {description} - PASSED")
        else:
            print(f"\n[WARN] {description} - COMPLETED WITH WARNINGS")

        return success

    except Exception as e:
        print(f"\n[FAIL] {description} - CRASHED: {e}")
        return False


def main():
    """Run all test suites."""
    print("""
    ======================================================================

                        HYBRID AI AGENT - MASTER TEST SUITE

                    Testing all components and integrations...

    ======================================================================
    """)

    # Define all test suites
    test_suites = [
        ("test_quick.py", "Quick Sanity Check (5 min)"),
        ("verify_implementation.py", "Agent S3 Features (10 min)"),
        ("test_cross_platform.py", "Cross-Platform L2 (5 min)"),
        ("test_visual_annotator_cross_platform.py", "Visual Annotator (5 min)"),
        ("test_levels.py", "Component Tests (15 min)"),
        ("test_agent_loop.py", "Integration Tests (30 min)"),
    ]

    results = {}

    # Run each test suite
    for script, description in test_suites:
        try:
            # Check if script exists
            import os
            if not os.path.exists(script):
                print(f"\n[SKIP] {description} - Script not found: {script}")
                results[description] = None
                continue

            # Run the test
            success = run_test_script(script, description)
            results[description] = success

        except KeyboardInterrupt:
            print("\n\n[ABORT] Testing interrupted by user")
            break
        except Exception as e:
            print(f"\n[FAIL] {description} - Error: {e}")
            results[description] = False

    # Print final summary
    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    failed = sum(1 for r in results.values() if r is False)
    total = len(results)

    for description, result in results.items():
        if result is True:
            status = "[OK] PASS"
        elif result is None:
            status = "[SKIP] SKIP"
        else:
            status = "[FAIL] FAIL"
        print(f"  {status}: {description}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped (out of {total})")
    print("=" * 70)

    if failed == 0:
        print("\n[SUCCESS] All tests passed or skipped!")
        print("\nYour Hybrid AI Agent is working correctly.")
        print("\nNext steps:")
        print("  1. Configure API keys in .env for full functionality")
        print("  2. Try real-world examples (see HOW_TO_TEST_YOUR_AGENT.md)")
        print("  3. Read documentation for advanced features")
        return 0
    else:
        print(f"\n[WARN] {failed} test suite(s) failed")
        print("\nTroubleshooting:")
        print("  1. Check error messages above")
        print("  2. Install missing dependencies (see test output)")
        print("  3. Review HOW_TO_TEST_YOUR_AGENT.md")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
