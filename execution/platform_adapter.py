from __future__ import annotations

"""
Platform Abstraction Layer - Auto-detects and provides platform-specific L2 executor.

This module provides a factory function that returns the appropriate desktop automation
executor based on the current platform:
- Windows: pywinauto-based executor
- macOS: AppKit/Accessibility API executor
- Linux: AT-SPI-based executor

Usage:
    from execution.platform_adapter import get_desktop_adapter

    adapter = get_desktop_adapter()  # Auto-detects platform
    result = adapter.desktop_click("Chrome", state)
"""

import platform
from typing import Protocol, Optional, Dict

from execution.level0_programmatic import ActionResult
from core.state_model import StateModel


class DesktopAutomationAdapter(Protocol):
    """
    Protocol defining the interface for platform-specific desktop automation.

    All platform-specific executors must implement these methods.
    """

    def desktop_click(self, target: str, state: StateModel) -> ActionResult:
        """
        Click on a desktop element by name.

        Args:
            target: Name/text of element to click
            state: Current state model

        Returns:
            ActionResult with success status and message
        """
        ...


def get_desktop_adapter() -> DesktopAutomationAdapter:
    """
    Factory function to get platform-specific L2 desktop automation executor.

    Returns appropriate executor based on platform.system():
    - Windows: Level2UiTreeExecutor (pywinauto)
    - macOS (Darwin): Level2UiTreeExecutorMacOS (AppKit/Accessibility)
    - Linux: Level2UiTreeExecutorLinux (AT-SPI)

    Returns:
        Platform-specific executor implementing DesktopAutomationAdapter protocol

    Raises:
        RuntimeError: If platform not supported or dependencies not installed

    Example:
        >>> adapter = get_desktop_adapter()
        >>> result = adapter.desktop_click("Chrome", state)
        >>> print(result.message)
        'Clicked Chrome via Windows UI Automation'
    """
    system = platform.system()

    if system == "Windows":
        try:
            from execution.level2_ui_tree import Level2UiTreeExecutor
            print("[Platform Adapter] Using Windows executor (pywinauto)")
            return Level2UiTreeExecutor()
        except ImportError as e:
            raise RuntimeError(
                f"Windows desktop automation not available: {e}. "
                "Install pywinauto: pip install pywinauto"
            )

    elif system == "Darwin":  # macOS
        try:
            from execution.level2_ui_tree_macos import Level2UiTreeExecutorMacOS
            print("[Platform Adapter] Using macOS executor (Accessibility API)")
            return Level2UiTreeExecutorMacOS()
        except ImportError as e:
            raise RuntimeError(
                f"macOS desktop automation not available: {e}. "
                "Install PyObjC: pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices"
            )
        except RuntimeError as e:
            # Re-raise errors from executor __init__
            raise e

    elif system == "Linux":
        try:
            from execution.level2_ui_tree_linux import Level2UiTreeExecutorLinux
            print("[Platform Adapter] Using Linux executor (AT-SPI)")
            return Level2UiTreeExecutorLinux()
        except ImportError as e:
            raise RuntimeError(
                f"Linux desktop automation not available: {e}. "
                "Install AT-SPI: sudo apt-get install python3-pyatspi (Ubuntu/Debian) "
                "or: sudo dnf install python3-pyatspi (Fedora)"
            )
        except RuntimeError as e:
            # Re-raise errors from executor __init__
            raise e

    else:
        raise RuntimeError(
            f"Unsupported platform: {system}. "
            "Desktop automation (L2) only supports Windows, macOS, and Linux."
        )


def get_platform_info() -> Dict[str, str]:
    """
    Get information about current platform and available executors.

    Returns:
        Dictionary with platform details:
        - system: Platform name (Windows/Darwin/Linux)
        - l2_executor: Name of L2 executor
        - l2_available: Whether L2 is available
        - l2_technology: Underlying technology used

    Example:
        >>> info = get_platform_info()
        >>> print(info)
        {
            'system': 'Darwin',
            'l2_executor': 'Level2UiTreeExecutorMacOS',
            'l2_available': True,
            'l2_technology': 'AppKit/Accessibility API'
        }
    """
    system = platform.system()

    platform_map = {
        "Windows": {
            "l2_executor": "Level2UiTreeExecutor",
            "l2_technology": "pywinauto (UIAutomation)",
        },
        "Darwin": {
            "l2_executor": "Level2UiTreeExecutorMacOS",
            "l2_technology": "AppKit/Accessibility API",
        },
        "Linux": {
            "l2_executor": "Level2UiTreeExecutorLinux",
            "l2_technology": "AT-SPI (pyatspi)",
        },
    }

    info = {
        "system": system,
        "l2_executor": "Unknown",
        "l2_available": False,
        "l2_technology": "Not supported",
    }

    if system in platform_map:
        info.update(platform_map[system])

        # Check if actually available
        try:
            get_desktop_adapter()
            info["l2_available"] = True
        except RuntimeError:
            info["l2_available"] = False

    return info


if __name__ == "__main__":
    """Test platform adapter."""
    print("=" * 60)
    print("Platform Adapter Test")
    print("=" * 60)

    # Print platform info
    info = get_platform_info()
    print(f"\nPlatform: {info['system']}")
    print(f"L2 Executor: {info['l2_executor']}")
    print(f"Technology: {info['l2_technology']}")
    print(f"Available: {info['l2_available']}")

    # Try to get adapter
    print("\nAttempting to load adapter...")
    try:
        adapter = get_desktop_adapter()
        print(f"✓ Success: {type(adapter).__name__}")
    except RuntimeError as e:
        print(f"✗ Failed: {e}")

    print("=" * 60)
