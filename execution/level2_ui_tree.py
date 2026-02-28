from __future__ import annotations

"""
Hybrid AI Agent – Level 2 UI tree execution.

Desktop automation using:
1. Vision-based desktop search (Gemini looks at desktop)
2. Start menu search fallback
3. Shell commands as last resort

All actions human-like with visible cursor movement.
"""

import subprocess
from typing import Optional

from pywinauto import Desktop
from pywinauto.base_wrapper import BaseWrapper

from execution.level0_programmatic import ActionResult
from execution.level5_cloud_vision import Level5CloudVisionExecutor
from execution.start_menu_helper import StartMenuSearchHelper
from perception.schemas import NormalisedEnvironment, NormalisedElement
from datetime import datetime
from core.human_timing import HumanTiming


class Level2UiTreeExecutor:
    """
    Desktop executor with human-like visual automation.
    
    Strategy for desktop_click:
    1. Try vision on desktop (Gemini finds icon)
    2. Try Start menu search (Win+S → type → click)
    3. Try shell command (invisible fallback)
    """

    def __init__(self, backend: str = "uia") -> None:
        self._backend = backend
        self._vision = Level5CloudVisionExecutor()
        self._start_menu = StartMenuSearchHelper()
        self._timing = HumanTiming()

    def _active_window(self) -> Optional[BaseWrapper]:
        try:
            desktop = Desktop(backend=self._backend)
            return desktop.active()
        except Exception:
            return None

    def desktop_click(self, name: str) -> ActionResult:
        """
        Click/open a Windows item by name using human-like visual automation.
        
        Tries in order:
        1. Vision on desktop (looks for icon, moves cursor, clicks)
        2. Start menu search (Win+S, type, find result, click)
        3. Shell command (invisible fallback)
        """
        print(f"\n=== Opening '{name}' ===")
        
        # Strategy 1: Try finding on desktop with vision
        print(f"Strategy 1: Looking for '{name}' on desktop...")
        desktop_result = self._try_desktop_vision(name)
        if desktop_result.success:
            print(f"  [OK] Opened via desktop vision")
            return desktop_result
        print(f"  [X] Not found on desktop: {desktop_result.message}")
        
        # Strategy 2: Try Start menu search
        print(f"Strategy 2: Searching in Start menu...")
        search_result = self._start_menu.search_and_click(name)
        if search_result.success:
            print(f"  [OK] Opened via Start menu search")
            return search_result
        print(f"  [X] Start menu search failed: {search_result.message}")
        
        # Strategy 3: Try shell command (invisible fallback)
        print(f"Strategy 3: Trying shell command...")
        shell_result = self._try_shell_open(name)
        if shell_result.success:
            print(f"  [OK] Opened via shell (NO CURSOR MOVEMENT)")
            print(f"  WARNING: This was invisible - no human-like automation")
            return shell_result
        
        return ActionResult(False, f"Could not open '{name}' via desktop, Start menu, or shell")

    def _try_desktop_vision(self, name: str) -> ActionResult:
        """Use Gemini vision to find item on desktop and click it."""
        # Create a simple environment representing the desktop
        env = NormalisedEnvironment(
            window_title="Desktop",
            window_type="desktop",
            current_url=None,
            app_name="Desktop",
            elements=[
                NormalisedElement(
                    id="desktop_icon",
                    label=name,
                    element_type="icon",
                    text_content=name,
                    state="enabled",
                    sources=["visual"],
                    dom_locator=None,
                    ui_tree_id=None,
                    bbox=None,
                    confidence=1.0,
                    children=[],
                )
            ],
            interactive=[],
            timestamp=datetime.now(),
            source_hash="",
        )
        
        # Ask vision to find and click it
        return self._vision.execute(
            environment=env,
            action_description="click",
            element_description=f"{name} icon on desktop",
            perform_click=True,  # This will move cursor and click
        )

    def _try_shell_open(self, name: str) -> ActionResult:
        """Try to open via Windows shell commands (invisible fallback)."""
        name_lower = name.lower()
        
        # Map common items to shell commands
        shell_commands = {
            "control panel": "control",
            "recycle bin": "explorer shell:RecycleBinFolder",
            "file explorer": "explorer",
            "this pc": "explorer",
            "computer": "explorer",
            "settings": "ms-settings:",
            "task manager": "taskmgr",
            "notepad": "notepad",
            "calculator": "calc",
            "paint": "mspaint",
            "command prompt": "cmd",
            "powershell": "powershell",
        }
        
        for key, cmd in shell_commands.items():
            if key in name_lower:
                try:
                    subprocess.Popen(cmd, shell=True)
                    self._timing.wait_for_window()
                    return ActionResult(True, f"Opened '{name}' via shell command: {cmd}")
                except Exception as exc:
                    return ActionResult(False, f"Shell command '{cmd}' failed: {exc}")
        
        return ActionResult(False, f"No shell command known for '{name}'")

    def desktop_type(self, name: str, text: str) -> ActionResult:
        """
        Type into a control in the active window by its visible name.
        """
        win = self._active_window()
        if win is None:
            return ActionResult(False, "No active window for desktop_type.")

        try:
            ctrl = win.child_window(title=name)
            ctrl_wrapper = ctrl.wrapper_object()
            ctrl_wrapper.set_focus()
            ctrl_wrapper.type_keys(text, with_spaces=True, set_foreground=True)
            return ActionResult(True, f"Typed into desktop control with name '{name}'.")
        except Exception as exc:
            return ActionResult(False, f"Failed to type into desktop control '{name}': {exc}")
