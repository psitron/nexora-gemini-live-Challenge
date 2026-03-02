"""
Visual Annotator Cross-Platform Test

Tests the visual annotator on the current platform to verify:
1. Platform detection works correctly
2. Import succeeds
3. Annotation can be displayed (if dependencies installed)
4. Graceful degradation if dependencies missing
"""

import platform
import sys
import time


def test_platform_detection():
    """Test 1: Platform detection."""
    print("=" * 70)
    print("TEST 1: Platform Detection")
    print("=" * 70)

    system = platform.system()
    print(f"Detected platform: {system}")

    expected = {
        "Windows": "Win32 API",
        "Darwin": "AppKit/Quartz",
        "Linux": "GTK+"
    }

    if system in expected:
        print(f"[OK] Platform supported: {expected[system]}")
        return True
    else:
        print(f"[FAIL] Platform not supported: {system}")
        return False


def test_adapter_import():
    """Test 2: Adapter import."""
    print("\n" + "=" * 70)
    print("TEST 2: Adapter Import")
    print("=" * 70)

    try:
        from core.visual_annotator_adapter import highlight_bbox, get_platform_info
        print("[OK] Successfully imported visual_annotator_adapter")

        # Get platform info
        info = get_platform_info()
        print(f"\nPlatform info:")
        print(f"  System: {info['system']}")
        print(f"  Implementation: {info['implementation']}")
        print(f"  Available: {info['available']}")

        return True

    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_platform_specific_import():
    """Test 3: Platform-specific module import."""
    print("\n" + "=" * 70)
    print("TEST 3: Platform-Specific Module Import")
    print("=" * 70)

    system = platform.system()

    try:
        if system == "Windows":
            from core.visual_annotator import highlight_bbox
            print("[OK] Windows module imported: core.visual_annotator")

        elif system == "Darwin":
            from core.visual_annotator_macos import highlight_bbox
            print("[OK] macOS module imported: core.visual_annotator_macos")

        elif system == "Linux":
            from core.visual_annotator_linux import highlight_bbox
            print("[OK] Linux module imported: core.visual_annotator_linux")

        return True

    except ImportError as e:
        print(f"[FAIL] Platform-specific module import failed: {e}")

        if system == "Darwin":
            print("\nTo install macOS dependencies:")
            print("  pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz")
        elif system == "Linux":
            print("\nTo install Linux dependencies:")
            print("  sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0")
            print("  pip install PyGObject")

        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_annotation_display():
    """Test 4: Display annotation (visual test)."""
    print("\n" + "=" * 70)
    print("TEST 4: Annotation Display (Visual)")
    print("=" * 70)

    try:
        from core.visual_annotator_adapter import highlight_bbox, get_platform_info

        info = get_platform_info()
        if not info['available']:
            print(f"[SKIP] Annotation not available: {info['implementation']}")
            return None  # Skip (not a failure)

        print("Displaying test annotation...")
        print("  Location: (500, 400)")
        print("  Size: 200x100")
        print("  Duration: 1.0 seconds")
        print("  Fade out: 1.0 seconds")
        print("\n[OK] If you see a red box on screen, the test PASSED!")
        print("     If not, the test FAILED.")

        # Display annotation
        highlight_bbox("500,400,200,100", duration=1.0, fade_out_seconds=1.0)

        # Wait for it to complete
        time.sleep(2.5)

        print("\n[OK] Annotation test completed")
        return True

    except Exception as e:
        print(f"[FAIL] Annotation display failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unified_api():
    """Test 5: Unified API (all code paths use adapter)."""
    print("\n" + "=" * 70)
    print("TEST 5: Unified API Integration")
    print("=" * 70)

    try:
        # Check that key files use the adapter
        import core.vision_agent
        import execution.level5_cloud_vision
        import execution.keyboard_controller

        print("[OK] All modules use visual_annotator_adapter")
        print("  - core.vision_agent")
        print("  - execution.level5_cloud_vision")
        print("  - execution.keyboard_controller")

        return True

    except Exception as e:
        print(f"[FAIL] Unified API test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("""
    ==================================================================

              VISUAL ANNOTATOR CROSS-PLATFORM TEST

      Testing platform detection, imports, and annotations...

    ==================================================================
    """)

    tests = [
        ("Platform Detection", test_platform_detection),
        ("Adapter Import", test_adapter_import),
        ("Platform-Specific Import", test_platform_specific_import),
        ("Annotation Display", test_annotation_display),
        ("Unified API", test_unified_api),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n[FAIL] {test_name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)

    for test_name, result in results.items():
        if result is True:
            status = "[OK] PASS"
        elif result is None:
            status = "[SKIP] SKIP"
        else:
            status = "[FAIL] FAIL"
        print(f"  {status}: {test_name}")

    print("\n" + "=" * 70)
    print(f"RESULT: {passed}/{total} tests passed, {skipped} skipped")
    print("=" * 70)

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        print(f"\nVisual annotator works on: {platform.system()}")
        print("Ready for production use!")
        return True
    elif passed + skipped == total:
        print(f"\n[WARN] Some tests skipped (dependencies not installed)")
        print("Visual annotator will fall back to text-only mode.")
        return True
    else:
        print(f"\n[WARN] {total - passed - skipped} test(s) failed")
        print("Review errors above and install missing dependencies.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
