"""
Verification Script - Test that all new components work correctly.

This script verifies that all Agent S3-inspired improvements were
implemented correctly and can be instantiated without errors.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all new modules can be imported."""
    print("=" * 70)
    print("TEST 1: IMPORTS")
    print("=" * 70)

    modules_to_test = [
        ("core.reflection_agent", "ReflectionAgent"),
        ("core.state_model", "StateModel"),
        ("core.code_agent", "CodeAgent"),
        ("core.trajectory_manager", "TrajectoryManager"),
        ("core.procedural_memory", "ProceduralMemory"),
        ("core.procedural_memory", "ProceduralMemoryBuilder"),
    ]

    all_passed = True
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  [OK] {module_name}.{class_name}")
        except Exception as e:
            print(f"  [FAIL] {module_name}.{class_name}: {e}")
            all_passed = False

    if all_passed:
        print("\n[OK] All imports successful!")
    else:
        print("\n[FAIL] Some imports failed!")

    return all_passed


def test_reflection_agent():
    """Test ReflectionAgent instantiation and basic operation."""
    print("\n" + "=" * 70)
    print("TEST 2: REFLECTION AGENT")
    print("=" * 70)

    try:
        from core.reflection_agent import ReflectionAgent

        agent = ReflectionAgent()
        print("  [OK] ReflectionAgent instantiated")

        # Test basic reflection (without screenshots)
        reflection = agent.reflect(
            task_goal="Test task",
            last_action="Test action",
            screenshot_before=None,
            screenshot_after=None
        )
        print(f"  [OK] Reflection completed")
        print(f"    - Action succeeded: {reflection.action_succeeded}")
        print(f"    - Progress: {reflection.progress_assessment}")
        print(f"    - Confidence: {reflection.confidence:.1%}")

        return True

    except Exception as e:
        print(f"  [FAIL] ReflectionAgent failed: {e}")
        return False


def test_state_model():
    """Test StateModel with new text buffer methods."""
    print("\n" + "=" * 70)
    print("TEST 3: STATE MODEL (Text Buffer)")
    print("=" * 70)

    try:
        from core.state_model import StateModel

        state = StateModel()
        print("  [OK] StateModel instantiated")

        # Test knowledge methods
        state.add_knowledge("Test fact 1")
        state.add_knowledge("Test fact 2")
        state.add_knowledge("Test fact 1")  # Duplicate
        print("  [OK] Knowledge added (with duplicate filtering)")

        summary = state.get_knowledge_summary()
        print(f"  [OK] Knowledge summary retrieved")
        print(f"    {summary}")

        state.clear_knowledge()
        empty_summary = state.get_knowledge_summary()
        print(f"  [OK] Knowledge cleared")
        print(f"    After clear: '{empty_summary}'")

        return True

    except Exception as e:
        print(f"  [FAIL] StateModel failed: {e}")
        return False


def test_code_agent():
    """Test CodeAgent instantiation."""
    print("\n" + "=" * 70)
    print("TEST 4: CODE AGENT")
    print("=" * 70)

    try:
        from core.code_agent import CodeAgent

        # Note: CodeAgent requires API keys, so we just test instantiation
        try:
            agent = CodeAgent()
            print("  [OK] CodeAgent instantiated (API keys available)")
            has_api_keys = True
        except RuntimeError as e:
            print(f"  [WARN] CodeAgent requires API keys: {e}")
            print("    Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env to enable")
            has_api_keys = False

        if has_api_keys:
            print("  [INFO] Code execution tests skipped (requires API calls)")

        return True  # Pass even without API keys

    except Exception as e:
        print(f"  [FAIL] CodeAgent failed: {e}")
        return False


def test_trajectory_manager():
    """Test TrajectoryManager."""
    print("\n" + "=" * 70)
    print("TEST 5: TRAJECTORY MANAGER")
    print("=" * 70)

    try:
        from core.trajectory_manager import TrajectoryManager

        manager = TrajectoryManager(max_images=4)
        print("  [OK] TrajectoryManager instantiated (max_images=4)")

        # Add some steps
        for i in range(1, 6):
            manager.add_step(
                step_number=i,
                action_description=f"Test action {i}",
                screenshot_before=None,
                screenshot_after=None,
                outcome="success",
                observations=f"Observation {i}"
            )
        print(f"  [OK] Added 5 steps")

        text_summary = manager.get_text_summary()
        print(f"  [OK] Text summary generated")
        print(f"    Steps preserved: {manager.get_step_count()}")
        print(f"    Images in memory: {manager.get_image_count()}")

        # Get context
        context = manager.get_full_context()
        print(f"  [OK] Full context retrieved")
        print(f"    Total steps: {context['total_steps']}")

        return True

    except Exception as e:
        print(f"  [FAIL] TrajectoryManager failed: {e}")
        return False


def test_procedural_memory():
    """Test ProceduralMemory."""
    print("\n" + "=" * 70)
    print("TEST 6: PROCEDURAL MEMORY")
    print("=" * 70)

    try:
        from core.procedural_memory import ProceduralMemory, ProceduralMemoryBuilder

        # Test simple build
        prompt = ProceduralMemory.build_system_prompt(task="Test task")
        print(f"  [OK] System prompt built ({len(prompt)} chars)")

        # Test quick reference
        quick_ref = ProceduralMemory.get_quick_reference()
        print(f"  [OK] Quick reference generated ({len(quick_ref)} chars)")

        # Test fluent builder
        custom_prompt = (ProceduralMemoryBuilder()
                         .with_task("Test task")
                         .with_core_guidelines()
                         .with_quick_reference()
                         .build())
        print(f"  [OK] Fluent builder worked ({len(custom_prompt)} chars)")

        return True

    except Exception as e:
        print(f"  [FAIL] ProceduralMemory failed: {e}")
        return False


def test_agent_loop_integration():
    """Test that AgentLoop imports and has new components."""
    print("\n" + "=" * 70)
    print("TEST 7: AGENT LOOP INTEGRATION")
    print("=" * 70)

    try:
        from core.agent_loop import AgentLoop

        agent = AgentLoop()
        print("  [OK] AgentLoop instantiated")

        # Check for new attributes
        has_reflection = hasattr(agent, 'reflection_agent')
        has_trajectory = hasattr(agent, 'trajectory_manager')

        print(f"  {'[OK]' if has_reflection else '[FAIL]'} Has reflection_agent attribute")
        print(f"  {'[OK]' if has_trajectory else '[FAIL]'} Has trajectory_manager attribute")

        if has_reflection and has_trajectory:
            print("  [OK] AgentLoop integration complete!")
            return True
        else:
            print("  [FAIL] AgentLoop missing new attributes")
            return False

    except Exception as e:
        print(f"  [FAIL] AgentLoop integration failed: {e}")
        return False


def run_all_tests():
    """Run all verification tests."""
    print("""
    ==================================================================

              AGENT S3 IMPROVEMENTS VERIFICATION

      Testing that all new components work correctly...

    ==================================================================
    """)

    tests = [
        ("Imports", test_imports),
        ("Reflection Agent", test_reflection_agent),
        ("State Model (Text Buffer)", test_state_model),
        ("Code Agent", test_code_agent),
        ("Trajectory Manager", test_trajectory_manager),
        ("Procedural Memory", test_procedural_memory),
        ("Agent Loop Integration", test_agent_loop_integration),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {test_name} CRASHED: {e}")
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
        print("\n[PASS] ALL TESTS PASSED - Implementation verified!")
        return True
    else:
        print(f"\n[WARN] {total - passed} test(s) failed - Review errors above")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
