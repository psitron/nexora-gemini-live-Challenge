from __future__ import annotations

"""
macOS Desktop Automation - Level 2 UI Tree Executor

Uses macOS Accessibility API (AppKit/ApplicationServices) to interact with desktop applications.

Based on Agent S's MacOSACI implementation but adapted for our multi-level architecture.

Key Technologies:
- AppKit: NSWorkspace for app management
- ApplicationServices: AXUIElement for accessibility tree
- pyautogui: Cross-platform mouse/keyboard

Dependencies:
    pip install pyobjc-framework-Cocoa
    pip install pyobjc-framework-Quartz
    pip install pyobjc-framework-ApplicationServices
"""

import platform
import time
from typing import Optional, List, Dict, Tuple

# Only import macOS-specific modules on macOS
if platform.system() == "Darwin":
    try:
        from AppKit import NSWorkspace
        from ApplicationServices import (
            AXUIElementCopyAttributeNames,
            AXUIElementCopyAttributeValue,
            AXUIElementCreateSystemWide,
        )
        MACOS_AVAILABLE = True
    except ImportError:
        MACOS_AVAILABLE = False
        print("[macOS L2] Warning: PyObjC not installed. Install with: pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices")
else:
    MACOS_AVAILABLE = False

from execution.level0_programmatic import ActionResult
from core.state_model import StateModel


class Level2UiTreeExecutorMacOS:
    """
    macOS desktop automation using Accessibility API.

    Strategy:
    1. Get accessibility tree from frontmost application
    2. Find elements by name/text matching
    3. Click element centers
    4. Fall back to Spotlight for app launching
    """

    def __init__(self):
        if not MACOS_AVAILABLE:
            raise RuntimeError(
                "macOS Accessibility API not available. "
                "Install PyObjC: pip install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices"
            )

        self._nodes: List[Dict] = []
        self._exclude_roles = {"AXGroup", "AXLayoutArea", "AXLayoutItem", "AXUnknown", "AXStaticText"}

    def desktop_click(self, target: str, state: StateModel) -> ActionResult:
        """
        Click on a desktop element by name.

        Args:
            target: Name of the element to click (e.g., "Chrome", "Close", "Submit")
            state: Current state model

        Returns:
            ActionResult with success status and message
        """
        print(f"[macOS L2] Looking for '{target}' in accessibility tree...")

        # Strategy 1: Try to find in accessibility tree
        element = self._find_element_in_tree(target)

        if element:
            x, y = self._get_element_center(element)
            print(f"[macOS L2] Found '{target}' at ({x}, {y})")

            # Click using pyautogui
            import pyautogui
            pyautogui.click(x, y)

            return ActionResult(
                success=True,
                message=f"Clicked '{target}' via macOS Accessibility API at ({x}, {y})"
            )

        # Strategy 2: Try Spotlight if it looks like an app name
        if self._looks_like_app_name(target):
            return self._launch_via_spotlight(target)

        return ActionResult(
            success=False,
            message=f"Element '{target}' not found in accessibility tree"
        )

    def _find_element_in_tree(self, target: str) -> Optional[Dict]:
        """Find element by searching accessibility tree."""
        try:
            # Get accessibility tree for frontmost app
            tree = self._get_frontmost_app_tree()

            if not tree:
                return None

            # Extract all visible elements
            self._nodes = self._preserve_nodes(tree)

            # Find matching element
            target_lower = target.lower()
            for node in self._nodes:
                title = node.get('title', '').lower()
                text = node.get('text', '').lower()

                if target_lower in title or target_lower in text:
                    return node

            return None

        except Exception as e:
            print(f"[macOS L2] Error finding element: {e}")
            return None

    def _get_frontmost_app_tree(self) -> Optional[UIElement]:
        """Get accessibility tree for frontmost application."""
        try:
            # Get system-wide accessibility element
            system_wide_ref = AXUIElementCreateSystemWide()
            system_elem = UIElement(system_wide_ref)

            # Get focused application
            focused_app_ref = system_elem.attribute("AXFocusedApplication")
            if not focused_app_ref:
                return None

            return UIElement(focused_app_ref)

        except Exception as e:
            print(f"[macOS L2] Error getting accessibility tree: {e}")
            return None

    def _preserve_nodes(self, tree: UIElement) -> List[Dict]:
        """
        Extract all visible, interactive elements from accessibility tree.

        Args:
            tree: Root UIElement to traverse

        Returns:
            List of element dictionaries with position, size, title, text, role
        """
        preserved_nodes = []

        def traverse(element):
            try:
                role = element.attribute("AXRole")

                # Skip excluded roles (layout containers, etc.)
                if role in self._exclude_roles:
                    pass  # Still traverse children
                else:
                    # Get position and size
                    position = element.attribute("AXPosition")
                    size = element.attribute("AXSize")

                    if position and size:
                        # Parse position (format: "x:123 y:456")
                        x, y = self._parse_position(position)

                        # Parse size (format: "w:100 h:50")
                        w, h = self._parse_size(size)

                        # Only keep elements with valid coordinates
                        if x >= 0 and y >= 0 and w > 0 and h > 0:
                            preserved_nodes.append({
                                "position": (x, y),
                                "size": (w, h),
                                "title": str(element.attribute("AXTitle") or ""),
                                "text": str(element.attribute("AXDescription") or element.attribute("AXValue") or ""),
                                "role": str(role),
                            })

                # Traverse children
                children = element.attribute("AXChildren")
                if children:
                    for child_ref in children:
                        child_element = UIElement(child_ref)
                        traverse(child_element)

            except Exception as e:
                # Silently skip problematic elements
                pass

        traverse(tree)
        return preserved_nodes

    def _parse_position(self, position) -> Tuple[float, float]:
        """Parse AXPosition attribute to (x, y) tuple."""
        try:
            pos_str = str(position.__repr__())
            parts = pos_str.split()

            x = next((float(p.split(":")[1]) for p in parts if p.startswith("x:")), -1)
            y = next((float(p.split(":")[1]) for p in parts if p.startswith("y:")), -1)

            return (x, y)
        except:
            return (-1, -1)

    def _parse_size(self, size) -> Tuple[float, float]:
        """Parse AXSize attribute to (w, h) tuple."""
        try:
            size_str = str(size.__repr__())
            parts = size_str.split()

            w = next((float(p.split(":")[1]) for p in parts if p.startswith("w:")), 0)
            h = next((float(p.split(":")[1]) for p in parts if p.startswith("h:")), 0)

            return (w, h)
        except:
            return (0, 0)

    def _get_element_center(self, element: Dict) -> Tuple[int, int]:
        """Calculate center coordinates of element."""
        x = element["position"][0] + element["size"][0] // 2
        y = element["position"][1] + element["size"][1] // 2
        return (int(x), int(y))

    def _looks_like_app_name(self, target: str) -> bool:
        """Heuristic to detect if target is likely an app name."""
        # Common app indicators
        app_indicators = [
            'safari', 'chrome', 'firefox', 'textedit', 'finder',
            'terminal', 'mail', 'notes', 'calculator', 'calendar',
            'preview', 'messages', 'facetime', 'photos', 'music'
        ]

        target_lower = target.lower()
        return any(indicator in target_lower for indicator in app_indicators)

    def _launch_via_spotlight(self, app_name: str) -> ActionResult:
        """
        Launch application using Spotlight (Command+Space).

        Args:
            app_name: Name of application to launch

        Returns:
            ActionResult with success status
        """
        print(f"[macOS L2] Launching '{app_name}' via Spotlight...")

        try:
            import pyautogui

            # Open Spotlight
            pyautogui.hotkey('command', 'space')
            time.sleep(0.5)

            # Type app name
            pyautogui.typewrite(app_name, interval=0.05)
            time.sleep(0.3)

            # Press Enter
            pyautogui.press('enter')
            time.sleep(1.5)  # Wait for app to launch

            return ActionResult(
                success=True,
                message=f"Launched '{app_name}' via Spotlight"
            )

        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to launch via Spotlight: {e}"
            )


class UIElement:
    """
    Wrapper for macOS AXUIElement.

    Provides convenient access to accessibility attributes.
    """

    def __init__(self, ref):
        """
        Initialize with AXUIElementRef.

        Args:
            ref: CoreFoundation reference to AXUIElement
        """
        self.ref = ref

    def attribute(self, key: str):
        """
        Get attribute value from element.

        Args:
            key: Attribute name (e.g., "AXRole", "AXTitle", "AXChildren")

        Returns:
            Attribute value or None if not available
        """
        try:
            error, value = AXUIElementCopyAttributeValue(self.ref, key, None)
            return value
        except Exception:
            return None

    def __repr__(self):
        return f"UIElement({self.ref})"
