#!/usr/bin/env python
"""
Simple Agent - Direct Actions with Visual Annotations

Directly executes common Windows tasks with visual teaching mode.
Uses the Level2 executor (UI Tree) for reliable, fast execution.

Usage:
    python simple_agent.py "open Chrome"
    python simple_agent.py "open Control Panel"
    python simple_agent.py  (interactive mode)

All actions include:
- Red box annotations around UI elements
- Smooth cursor movement
- OCR-based result finding
- Multi-monitor support (set PRIMARY_MONITOR in .env)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from execution.level2_ui_tree import Level2UiTreeExecutor


def print_banner():
    print("=" * 70)
    print("SIMPLE AI AGENT - Direct Actions with Visual Annotations")
    print("=" * 70)
    print()
    print("Open any application with visual teaching mode:")
    print("  - Red boxes highlight search box and results")
    print("  - Smooth cursor movement")
    print("  - OCR finds exact results")
    print("  - Works on your PRIMARY_MONITOR (set in .env)")
    print()
    print("=" * 70)
    print()


def parse_open_command(command: str) -> str | None:
    """Extract app name from 'open X' commands."""
    command_lower = command.lower().strip()
    
    # Match patterns like "open X", "launch X", "start X"
    for prefix in ["open ", "launch ", "start ", "run "]:
        if command_lower.startswith(prefix):
            app_name = command[len(prefix):].strip()
            # Remove common suffixes
            for suffix in [" browser", " app", " application"]:
                if app_name.lower().endswith(suffix):
                    app_name = app_name[:-len(suffix)].strip()
            return app_name
    
    # If no prefix, assume it's just the app name
    return command.strip()


def execute_command(command: str, executor: Level2UiTreeExecutor):
    """Execute a single command."""
    app_name = parse_open_command(command)
    
    if not app_name:
        print(f"Could not understand command: {command}")
        print("Try: 'open Chrome', 'launch Control Panel', etc.")
        return
    
    print(f"Opening: {app_name}")
    print("-" * 70)
    print()
    
    result = executor.desktop_click(app_name)
    
    print()
    print("-" * 70)
    if result.success:
        print(f"[SUCCESS] Opened '{app_name}'")
    else:
        print(f"[FAILED] Could not open '{app_name}'")
        print(f"   Reason: {result.message}")
    print()


def interactive_mode():
    """Run in continuous interactive mode."""
    print_banner()
    print("Interactive Mode - Type your commands below")
    print("(Type 'exit', 'quit', or press Ctrl+C to stop)")
    print()
    
    executor = Level2UiTreeExecutor()
    
    while True:
        try:
            command = input("\nWhat should I open? > ").strip()
            
            if not command:
                continue
                
            if command.lower() in ('exit', 'quit', 'q', 'stop'):
                print("Goodbye!")
                break
            
            print()
            execute_command(command, executor)
            
        except KeyboardInterrupt:
            print("\n\nStopped by user. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            print("\nContinuing in interactive mode...")


def single_command_mode(command: str):
    """Run with a single command."""
    print_banner()
    executor = Level2UiTreeExecutor()
    execute_command(command, executor)


def main():
    if len(sys.argv) > 1:
        # Single command mode
        command = " ".join(sys.argv[1:])
        single_command_mode(command)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
