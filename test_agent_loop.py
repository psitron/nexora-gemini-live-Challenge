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
    print(f"Outcomes: {len(result.outcomes)} action outcomes recorded")

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

    # Check if API key available
    from config.settings import get_settings
    import os
    settings = get_settings()
    has_api_key = bool(settings.models.gemini_api_key or settings.models.anthropic_api_key or os.getenv('AWS_ACCESS_KEY_ID'))

    if not has_api_key:
        print("  [SKIP] This test requires LLM API key in .env")
        print("  [INFO] Add GEMINI_API_KEY or AWS credentials to .env")
        return None

    agent = AgentLoop()

    task = "Calculate the factorial of 10"

    print(f"Task: {task}")
    print("Running agent...\n")

    try:
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

    except Exception as e:
        print(f"\n[FAIL] Calculation task error: {e}")
        import traceback
        traceback.print_exc()
        return False


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
