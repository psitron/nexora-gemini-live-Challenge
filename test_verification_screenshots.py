"""
Test to verify visual verification debug screenshots are being saved.

This is a minimal test that doesn't require user interaction.
"""

from core.vision_agent_logged import VisionAgentLogged
import os
from pathlib import Path

print("="*70)
print("TESTING: Visual Verification Debug Screenshots")
print("="*70)
print()

# Create agent
agent = VisionAgentLogged()

# Simple task that should trigger visual verification
task = """
Press Windows key
Type 'notepad'
Wait 1 second
Press Escape to close search
"""

print("Running simple task to test screenshot saving...")
print(f"Task: {task}")
print()

result = agent.run(task)

print()
print("="*70)
print("RESULTS")
print("="*70)
print()
print(f"Success: {result.success}")
print(f"Steps executed: {result.steps_executed}")
print(f"Message: {result.message}")
print()

# Check if debug screenshots were saved
if hasattr(agent, 'logger') and agent.logger:
    screenshots_dir = agent.logger.screenshots_dir
    print(f"Screenshots directory: {screenshots_dir}")
    print()

    # List all files
    if screenshots_dir.exists():
        all_files = sorted(screenshots_dir.glob("*"))
        print(f"Total files saved: {len(all_files)}")
        print()

        # Check for specific types
        full_screenshots = list(screenshots_dir.glob("step_*_full.png"))
        resized_screenshots = list(screenshots_dir.glob("step_*_resized.png"))
        verify_crops = list(screenshots_dir.glob("verify_*_crop_*.png"))
        verify_composites = list(screenshots_dir.glob("verify_*_composite_*.png"))

        print("Screenshot types found:")
        print(f"  - Full screenshots (step_XX_full.png): {len(full_screenshots)}")
        print(f"  - Resized screenshots (step_XX_resized.png): {len(resized_screenshots)}")
        print(f"  - Verification crops (verify_XX_crop_Y.png): {len(verify_crops)}")
        print(f"  - Verification composites (verify_XX_composite.png): {len(verify_composites)}")
        print()

        if len(full_screenshots) > 0:
            print("✅ SUCCESS: Full/resized screenshots ARE being saved!")
        else:
            print("❌ FAILED: Full/resized screenshots NOT being saved")

        if len(verify_crops) > 0 or len(verify_composites) > 0:
            print("✅ SUCCESS: Visual verification debug screenshots ARE being saved!")
            print()
            print("Sample verification screenshots:")
            for f in verify_crops[:3]:
                print(f"  - {f.name}")
            for f in verify_composites[:3]:
                print(f"  - {f.name}")
        else:
            print("⚠️  NOTE: No visual verification screenshots (this is OK if no disambiguation was needed)")

        print()
        print("All files in screenshots directory:")
        for f in all_files[:20]:
            print(f"  - {f.name}")
        if len(all_files) > 20:
            print(f"  ... and {len(all_files) - 20} more files")
    else:
        print("❌ FAILED: Screenshots directory doesn't exist!")
else:
    print("❌ FAILED: Logger not initialized!")

print()
print("="*70)
print("Test complete!")
print("="*70)
