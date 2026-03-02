from __future__ import annotations

"""
Linux Desktop Automation - Level 2 UI Tree Executor

Uses AT-SPI (Assistive Technology Service Provider Interface) to interact with desktop applications.

Based on Agent S's LinuxACI implementation but adapted for our multi-level architecture.

Key Technologies:
- pyatspi: AT-SPI accessibility API
- wmctrl: Window management
- pyautogui: Cross-platform mouse/keyboard

Dependencies:
    # Ubuntu/Debian
    sudo apt-get install python3-pyatspi wmctrl

    # Fedora
    sudo dnf install python3-pyatspi wmctrl
"""

import platform
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Tuple

# Only import Linux-specific modules on Linux
if platform.system() == "Linux":
    try:
        import pyatspi
        from pyatspi import Accessible, StateType, Component, STATE_SHOWING
        LINUX_AVAILABLE = True
    except ImportError:
        LINUX_AVAILABLE = False
        print("[Linux L2] Warning: pyatspi not installed. Install with: sudo apt-get install python3-pyatspi")
else:
    LINUX_AVAILABLE = False

from execution.level0_programmatic import ActionResult
from core.state_model import StateModel


class Level2UiTreeExecutorLinux:
    """
    Linux desktop automation using AT-SPI.

    Strategy:
    1. Get accessibility tree from active applications
    2. Filter to elements with showing=true
    3. Find elements by name/text matching
    4. Click element centers
    5. Use wmctrl for window management
    """

    def __init__(self):
        if not LINUX_AVAILABLE:
            raise RuntimeError(
                "Linux AT-SPI not available. "
                "Install with: sudo apt-get install python3-pyatspi (Ubuntu/Debian) "
                "or: sudo dnf install python3-pyatspi (Fedora)"
            )

        self._nodes: List[ET.Element] = []
        self.state_ns = "https://accessibility.ubuntu.example.org/ns/state"
        self.component_ns = "https://accessibility.ubuntu.example.org/ns/component"
        self._exclude_tags = {"panel", "window", "filler", "frame", "separator", "scroll-bar"}

    def desktop_click(self, target: str, state: StateModel) -> ActionResult:
        """
        Click on a desktop element by name.

        Args:
            target: Name of the element to click (e.g., "Files", "Close", "Submit")
            state: Current state model

        Returns:
            ActionResult with success status and message
        """
        print(f"[Linux L2] Looking for '{target}' in accessibility tree...")

        # Strategy 1: Try to find in accessibility tree
        element = self._find_element_in_tree(target)

        if element:
            x, y = self._get_element_center(element)
            print(f"[Linux L2] Found '{target}' at ({x}, {y})")

            # Click using pyautogui
            import pyautogui
            pyautogui.click(x, y)

            return ActionResult(
                success=True,
                message=f"Clicked '{target}' via AT-SPI at ({x}, {y})"
            )

        # Strategy 2: Try wmctrl if it looks like an app name
        if self._looks_like_app_name(target):
            return self._launch_via_wmctrl(target)

        return ActionResult(
            success=False,
            message=f"Element '{target}' not found in accessibility tree"
        )

    def _find_element_in_tree(self, target: str) -> Optional[ET.Element]:
        """Find element by searching accessibility tree."""
        try:
            # Get accessibility tree
            tree_xml = self._get_accessibility_tree()
            tree = ET.ElementTree(ET.fromstring(tree_xml))

            # Filter to showing elements
            self._nodes = self._filter_showing_nodes(tree)

            # Find matching element
            target_lower = target.lower()
            for node in self._nodes:
                name = node.get("name", "").lower()
                text = (node.text or "").lower()

                if target_lower in name or target_lower in text:
                    return node

            return None

        except Exception as e:
            print(f"[Linux L2] Error finding element: {e}")
            return None

    def _get_accessibility_tree(self) -> str:
        """
        Get accessibility tree from AT-SPI as XML string.

        Returns:
            XML representation of accessibility tree
        """
        try:
            desktop = pyatspi.Registry.getDesktop(0)

            # Build XML tree
            root = ET.Element("desktop")

            for app in desktop:
                app_elem = self._create_atspi_node(app)
                if app_elem is not None:
                    root.append(app_elem)

            return ET.tostring(root, encoding="unicode")

        except Exception as e:
            print(f"[Linux L2] Error getting accessibility tree: {e}")
            return "<desktop/>"

    def _create_atspi_node(self, node: Accessible, depth: int = 0) -> Optional[ET.Element]:
        """
        Convert AT-SPI node to XML Element.

        Args:
            node: AT-SPI Accessible node
            depth: Current tree depth (for limiting recursion)

        Returns:
            XML Element or None if node should be skipped
        """
        if depth > 20:  # Limit recursion depth
            return None

        try:
            node_name = node.name
            role = node.getRoleName().replace(" ", "-")

            attribs = {"name": node_name or ""}

            # Get states
            states = node.getState().get_states()
            for st in states:
                try:
                    state_name = StateType._enum_lookup[st].split("_", 1)[1].lower()
                    if state_name:
                        attribs[f"{{{self.state_ns}}}{state_name}"] = "true"
                except:
                    pass

            # Get component (coordinates) only for showing elements
            if attribs.get(f"{{{self.state_ns}}}showing") == "true":
                try:
                    component = node.queryComponent()
                    bbox = component.getExtents(pyatspi.XY_SCREEN)
                    attribs[f"{{{self.component_ns}}}screencoord"] = str(tuple(bbox[0:2]))
                    attribs[f"{{{self.component_ns}}}size"] = str(tuple(bbox[2:]))
                except NotImplementedError:
                    pass

            # Get text
            text = ""
            try:
                text_obj = node.queryText()
                text = text_obj.getText(0, text_obj.characterCount)
                # Clean up special Unicode characters
                text = text.replace("\ufffc", "").replace("\ufffd", "")
            except NotImplementedError:
                pass

            # Create XML element
            xml_node = ET.Element(role, attrib=attribs)
            if text:
                xml_node.text = text

            # Traverse children (with depth limit)
            try:
                for child in node:
                    child_elem = self._create_atspi_node(child, depth + 1)
                    if child_elem is not None:
                        xml_node.append(child_elem)
            except:
                pass  # Skip problematic children

            return xml_node

        except Exception as e:
            return None

    def _filter_showing_nodes(self, tree: ET.ElementTree) -> List[ET.Element]:
        """
        Filter accessibility tree to only showing elements with valid coordinates.

        Args:
            tree: XML ElementTree

        Returns:
            List of visible, positioned elements
        """
        preserved_nodes = []

        for node in tree.iter():
            # Skip excluded tags
            if node.tag in self._exclude_tags:
                continue

            # Must be showing
            if node.attrib.get(f"{{{self.state_ns}}}showing") != "true":
                continue

            # Must have valid coordinates
            coords_str = node.get(f"{{{self.component_ns}}}screencoord", "(-1, -1)")
            try:
                coords = eval(coords_str)
                if coords[0] >= 0 and coords[1] >= 0:
                    preserved_nodes.append(node)
            except:
                pass

        return preserved_nodes

    def _get_element_center(self, element: ET.Element) -> Tuple[int, int]:
        """
        Calculate center coordinates of element.

        Args:
            element: XML Element with screencoord and size attributes

        Returns:
            (x, y) tuple of center point
        """
        try:
            coords_str = element.get(f"{{{self.component_ns}}}screencoord", "(0, 0)")
            sizes_str = element.get(f"{{{self.component_ns}}}size", "(0, 0)")

            coords = eval(coords_str)
            sizes = eval(sizes_str)

            x = coords[0] + sizes[0] // 2
            y = coords[1] + sizes[1] // 2

            return (int(x), int(y))

        except:
            return (0, 0)

    def _looks_like_app_name(self, target: str) -> bool:
        """Heuristic to detect if target is likely an app name."""
        app_indicators = [
            'firefox', 'chrome', 'chromium', 'gedit', 'nautilus', 'files',
            'terminal', 'konsole', 'kate', 'gimp', 'inkscape', 'libreoffice',
            'thunderbird', 'evolution', 'calculator', 'vlc'
        ]

        target_lower = target.lower()
        return any(indicator in target_lower for indicator in app_indicators)

    def _launch_via_wmctrl(self, app_name: str) -> ActionResult:
        """
        Launch or switch to application using wmctrl.

        Args:
            app_name: Name of application

        Returns:
            ActionResult with success status
        """
        print(f"[Linux L2] Attempting to switch to '{app_name}' via wmctrl...")

        try:
            # Get list of windows
            output = subprocess.check_output(['wmctrl', '-lx'], text=True)
            lines = output.splitlines()

            # Find matching window
            target_lower = app_name.lower()
            for line in lines:
                if target_lower in line.lower():
                    # Extract window ID (first column)
                    window_id = line.split()[0]

                    # Activate window
                    subprocess.run(['wmctrl', '-ia', window_id])

                    # Maximize window
                    subprocess.run(['wmctrl', '-ir', window_id, '-b', 'add,maximized_vert,maximized_horz'])

                    return ActionResult(
                        success=True,
                        message=f"Switched to '{app_name}' via wmctrl"
                    )

            # If not found, try to launch
            return self._launch_app(app_name)

        except FileNotFoundError:
            return ActionResult(
                success=False,
                message="wmctrl not found. Install with: sudo apt-get install wmctrl"
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to switch via wmctrl: {e}"
            )

    def _launch_app(self, app_name: str) -> ActionResult:
        """
        Launch application directly.

        Args:
            app_name: Application name or command

        Returns:
            ActionResult with success status
        """
        try:
            # Common app name to command mappings
            app_commands = {
                'files': 'nautilus',
                'file manager': 'nautilus',
                'text editor': 'gedit',
                'editor': 'gedit',
                'browser': 'firefox',
            }

            command = app_commands.get(app_name.lower(), app_name.lower())

            # Launch in background
            subprocess.Popen([command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)  # Wait for app to start

            return ActionResult(
                success=True,
                message=f"Launched '{app_name}'"
            )

        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to launch '{app_name}': {e}"
            )
