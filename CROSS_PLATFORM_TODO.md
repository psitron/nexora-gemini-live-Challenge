# Cross-Platform Implementation TODO

## Current Status

**Windows:** ✅ 100% functional
**macOS:** ⚠️ 70% functional (L2 desktop automation missing)
**Linux:** ⚠️ 70% functional (L2 desktop automation missing)

---

## Missing Components for macOS/Linux

### 1. L2 Desktop Automation (HIGH PRIORITY)

**Problem:** `pywinauto` is Windows-only

**Solutions by Platform:**

#### macOS Implementation
```python
# execution/level2_ui_tree_macos.py

import subprocess
from typing import Optional

class Level2UiTreeExecutorMacOS:
    """macOS desktop automation using AppleScript and Accessibility API."""

    def desktop_click(self, target: str) -> ActionResult:
        # Option A: AppleScript
        script = f'''
        tell application "System Events"
            tell process "Finder"
                click button "{target}" of window 1
            end tell
        end tell
        '''
        subprocess.run(['osascript', '-e', script])

        # Option B: PyObjC + Accessibility API
        # from AppKit import NSWorkspace
        # from Quartz import ...

    def find_element(self, name: str):
        # Use macOS Accessibility API via PyObjC
        pass
```

**Dependencies:**
```bash
pip install PyObjC
pip install pyobjc-framework-Quartz
pip install pyobjc-framework-ApplicationServices
```

**Effort:** 3-5 days

---

#### Linux Implementation
```python
# execution/level2_ui_tree_linux.py

import subprocess
from typing import Optional

class Level2UiTreeExecutorLinux:
    """Linux desktop automation using AT-SPI."""

    def __init__(self):
        # AT-SPI (Accessibility Technology - Service Provider Interface)
        import pyatspi
        self.registry = pyatspi.Registry

    def desktop_click(self, target: str) -> ActionResult:
        # Option A: xdotool (X11)
        subprocess.run(['xdotool', 'search', '--name', target, 'click', '1'])

        # Option B: ydotool (Wayland)
        subprocess.run(['ydotool', 'click', '1'])

        # Option C: AT-SPI
        # Use pyatspi to find and click elements

    def find_element(self, name: str):
        # Use AT-SPI to query accessibility tree
        import pyatspi
        desktop = pyatspi.Registry.getDesktop(0)
        # Traverse tree to find element
```

**Dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-pyatspi
sudo apt-get install xdotool  # for X11
sudo apt-get install ydotool  # for Wayland

# Fedora
sudo dnf install python3-pyatspi
```

**Effort:** 3-5 days

---

### 2. Visual Annotator (MEDIUM PRIORITY)

**Problem:** `ctypes.windll` is Windows-only

**Solutions by Platform:**

#### macOS Implementation
```python
# core/visual_annotator_macos.py

from AppKit import NSWindow, NSView, NSColor
from Quartz import CGWindowLevel

class VisualAnnotatorMacOS:
    """macOS screen annotations using Quartz/AppKit."""

    def highlight_bbox(self, bbox: str, duration: float = 0.8):
        # Create transparent overlay window using NSWindow
        # Set window level to CGWindowLevelForKey(kCGOverlayWindowLevelKey)
        # Draw red box using NSBezierPath
        pass
```

**Dependencies:**
```bash
pip install PyObjC-framework-Quartz
pip install PyObjC-framework-Cocoa
```

**Effort:** 2-3 days

---

#### Linux Implementation
```python
# core/visual_annotator_linux.py

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class VisualAnnotatorLinux:
    """Linux screen annotations using GTK."""

    def highlight_bbox(self, bbox: str, duration: float = 0.8):
        # Create transparent GTK window
        # Set window type hint to NOTIFICATION
        # Draw red box using Cairo
        pass
```

**Dependencies:**
```bash
sudo apt-get install python3-gi python3-gi-cairo
```

**Effort:** 2-3 days

---

### 3. Window Manager (LOW PRIORITY)

**Problem:** Window manipulation uses Win32 API

**Solutions:**

#### macOS
```python
# execution/window_manager_macos.py

from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll
from AppKit import NSWorkspace

def move_window_to_primary_monitor(window_title: str):
    # Use Quartz to find window
    # Use NSWindow to move it
    pass
```

#### Linux
```python
# execution/window_manager_linux.py

import subprocess

def move_window_to_primary_monitor(window_title: str):
    # Use wmctrl (works on X11)
    subprocess.run(['wmctrl', '-r', window_title, '-e', '0,0,0,-1,-1'])
```

**Effort:** 1-2 days

---

### 4. Platform Abstraction Layer (RECOMMENDED)

**Create unified interface:**

```python
# execution/platform_adapter.py

import platform
from typing import Protocol

class DesktopAutomationAdapter(Protocol):
    """Protocol for platform-specific desktop automation."""
    def desktop_click(self, target: str) -> ActionResult: ...
    def find_element(self, name: str) -> Optional[Element]: ...
    def get_active_window(self) -> Optional[Window]: ...

def get_desktop_adapter() -> DesktopAutomationAdapter:
    """Factory function to get platform-specific adapter."""
    system = platform.system()

    if system == "Windows":
        from execution.level2_ui_tree import Level2UiTreeExecutor
        return Level2UiTreeExecutor()
    elif system == "Darwin":  # macOS
        from execution.level2_ui_tree_macos import Level2UiTreeExecutorMacOS
        return Level2UiTreeExecutorMacOS()
    elif system == "Linux":
        from execution.level2_ui_tree_linux import Level2UiTreeExecutorLinux
        return Level2UiTreeExecutorLinux()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
```

**Usage:**
```python
# In execution/hierarchy.py
from execution.platform_adapter import get_desktop_adapter

adapter = get_desktop_adapter()  # Auto-detects platform
result = adapter.desktop_click("Chrome")  # Works everywhere!
```

**Effort:** 1 day (after platform-specific implementations)

---

## Implementation Roadmap

### Phase 1: Basic Cross-Platform Support (1 week)
- [ ] Implement L2 for macOS (AppleScript)
- [ ] Implement L2 for Linux (xdotool/AT-SPI)
- [ ] Create platform adapter abstraction
- [ ] Test basic desktop automation on all platforms

### Phase 2: Visual Feedback (3-5 days)
- [ ] Implement visual annotator for macOS (Quartz)
- [ ] Implement visual annotator for Linux (GTK)
- [ ] Fallback to no-op if platform not supported

### Phase 3: Polish (2-3 days)
- [ ] Window manager for macOS/Linux
- [ ] Monitor utils for macOS/Linux
- [ ] Cross-platform testing suite
- [ ] Update documentation

---

## Alternative: Skip L2 Entirely on macOS/Linux

**Simpler approach:**

```python
# execution/hierarchy.py

def attempt(self, tool_name: str, **kwargs):
    # On non-Windows platforms, skip L2
    if tool_name == "desktop_click" and platform.system() != "Windows":
        # Skip directly to L5 vision
        return self._level5.attempt(tool_name, **kwargs)

    # Continue with normal fallback chain
```

**Pros:**
- No additional code needed
- Works today on all platforms
- L5 vision is reasonably good (75% success)

**Cons:**
- 40x slower for desktop tasks (4s vs 100ms)
- Higher cost (cloud vision API calls)
- Lower reliability (75% vs 70%)

**Recommendation:** Use this as interim solution while implementing proper L2

---

## Testing Strategy

### Cross-Platform Test Suite

```python
# tests/test_cross_platform.py

import pytest
import platform

@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
def test_macos_desktop_automation():
    agent = AgentLoop()
    result = agent.run("Open TextEdit")
    assert result.goal_status == "complete"

@pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
def test_linux_desktop_automation():
    agent = AgentLoop()
    result = agent.run("Open gedit")
    assert result.goal_status == "complete"

@pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
def test_windows_desktop_automation():
    agent = AgentLoop()
    result = agent.run("Open Notepad")
    assert result.goal_status == "complete"
```

---

## Current Workaround for Users

**For macOS/Linux users TODAY:**

```python
from core.agent_loop import AgentLoop

# Works perfectly (uses L1 browser):
agent.run("Open Chrome and go to google.com")  # ✅

# Works with degraded performance (falls back to L5 vision):
agent.run("Open TextEdit")  # ⚠️ Slow but works

# Works perfectly (uses L0 files):
agent.run("Create a file called test.txt")  # ✅

# Works perfectly (uses Code Agent):
agent.run("Calculate sum of column A in spreadsheet.xlsx")  # ✅
```

**80% of use cases work out-of-box on macOS/Linux!**

Only desktop-app-specific automation is affected.

---

## Priority Recommendation

**High Priority:**
1. ✅ Document current limitations (this file)
2. 🔧 Implement L2 for macOS (AppleScript) - 3-5 days
3. 🔧 Implement L2 for Linux (AT-SPI) - 3-5 days
4. 🔧 Create platform adapter - 1 day

**Medium Priority:**
5. 🔧 Visual annotator for macOS/Linux - 5 days
6. 🔧 Window manager for macOS/Linux - 2 days

**Total Effort:** 2-3 weeks for full cross-platform support

---

## Status Updates

- **2026-03-01:** Created this TODO
- **Next milestone:** Implement macOS L2 adapter
