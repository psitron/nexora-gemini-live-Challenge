#!/usr/bin/env python
"""
AI Agent with Visual Annotations - Vision-Driven

DPI AWARENESS: Set BEFORE any Win32/GUI imports so all coordinate
systems (screen capture, mouse, OCR, overlay windows) are consistent.
Without this, annotations appear at wrong positions on scaled displays.
"""

from __future__ import annotations

import ctypes as _ctypes
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        _ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.vision_agent import VisionAgent


def print_banner():
    print("=" * 70)
    print("VISION AI AGENT - Sees Screen, Decides, Acts")
    print("=" * 70)
    print()
    print("This agent SEES your screen and can handle anything:")
    print("  - Opens apps, handles popups, closes dialogs")
    print("  - Reads screen with OCR, clicks exact targets")
    print("  - Red box annotations show what it's clicking")
    print("  - Works on your PRIMARY_MONITOR (set in .env)")
    print()
    print("=" * 70)
    print()


def interactive_mode():
    print_banner()
    print("Interactive Mode - Type your commands below")
    print("(Type 'exit' or 'quit' to stop)")
    print()

    while True:
        try:
            command = input("\nWhat should I do? > ").strip()

            if not command:
                continue

            if command.lower() in ('exit', 'quit', 'q'):
                print("Goodbye!")
                break

            print()
            agent = VisionAgent()
            result = agent.run(command)

            print()
            print("-" * 70)
            print("RESULT:")
            print(f"  Status: {'SUCCESS' if result.success else 'FAILED'}")
            print(f"  Steps: {result.steps_executed}")
            print(f"  Message: {result.message}")

            if result.success:
                print("  [OK] Done!")
            else:
                print("  [X] Could not complete (see details above)")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            print("Continuing in interactive mode...")


def single_command_mode(command: str):
    print_banner()

    agent = VisionAgent()
    result = agent.run(command)

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Command: {command}")
    print(f"Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Steps: {result.steps_executed}")
    print(f"Message: {result.message}")
    print()

    if result.success:
        print("[OK] Task completed successfully!")
    else:
        print("[X] Task did not complete (see log above)")
    print()


def main():
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        single_command_mode(command)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
