"""Quick sanity check - tests basic agent functionality."""

def test_imports():
    """Test that core modules can be imported."""
    print("Testing imports...")

    errors = []

    # Test essential imports (should always work)
    try:
        from core.reflection_agent import ReflectionAgent
        from core.code_agent import CodeAgent
        from core.trajectory_manager import TrajectoryManager
        from execution.platform_adapter import get_desktop_adapter, get_platform_info
        from core.visual_annotator_adapter import highlight_bbox, get_platform_info as get_annotator_info
        from execution.level0_programmatic import Level0ProgrammaticExecutor
        print("  [OK] Essential modules imported")
    except Exception as e:
        errors.append(f"Essential imports: {e}")

    # Test agent imports (may fail if optional deps missing)
    try:
        from core.agent_loop import AgentLoop
        print("  [OK] AgentLoop imported")
    except Exception as e:
        print(f"  [SKIP] AgentLoop import failed (missing dependencies): {e}")

    try:
        from core.vision_agent import VisionAgent
        print("  [OK] VisionAgent imported")
    except Exception as e:
        print(f"  [SKIP] VisionAgent import failed (missing dependencies): {e}")

    if errors:
        print(f"[FAIL] Essential imports failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("[OK] Core modules imported successfully (some optional modules skipped)")
        return True


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
        import traceback
        traceback.print_exc()
        return False


def test_basic_execution():
    """Test basic execution (L0 file operations)."""
    print("\nTesting basic execution (L0 file operations)...")

    try:
        from execution.level0_programmatic import Level0ProgrammaticExecutor
        from pathlib import Path
        import tempfile
        import os

        executor = Level0ProgrammaticExecutor()
        temp_file = Path(tempfile.gettempdir()) / "test_agent.txt"

        # Write file
        print("  Testing file_write...")
        result = executor.file_write(temp_file, "Hello, Agent!")
        if not result.success:
            print(f"  [FAIL] File write failed: {result.message}")
            return False
        print(f"  [OK] Write succeeded")

        # Read file
        print("  Testing file_read...")
        result = executor.file_read(temp_file)
        if not result.success or "Hello, Agent!" not in str(result.data):
            print(f"  [FAIL] File read failed: {result.message}")
            return False
        print(f"  [OK] Read succeeded: {result.data['content'][:20]}...")

        # Delete file
        print("  Testing file_delete...")
        result = executor.file_delete(temp_file)
        if not result.success:
            print(f"  [FAIL] File delete failed: {result.message}")
            return False
        print(f"  [OK] Delete succeeded")

        print("[OK] L0 file operations work correctly")
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
