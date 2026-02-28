from __future__ import annotations

"""
Hybrid AI Agent – ActionMapper with LLM.

Maps high-level planned steps into concrete tool invocations using:
1. LLM (Claude/Gemini) for dynamic, general-purpose mapping
2. Fallback heuristics for simple patterns when LLM unavailable
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.planner_task import PlannedStep


@dataclass
class ActionSpec:
    tool_name: str
    kwargs: Dict[str, Any]


class ActionMapper:
    """
    Maps PlannedStep + goal → list[ActionSpec] using LLM when available.
    Falls back to heuristics for simple cases.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Deduplication tracking
        self._navigated_urls: set[str] = set()
        self._listed_paths: set[str] = set()
        self._created_dirs: set[str] = set()
        self._read_files: set[str] = set()
        self._copied_pairs: set[tuple[str, str]] = set()

    def map_step(self, step: PlannedStep, goal: str) -> List[ActionSpec]:
        """Map a planned step to concrete tool actions using LLM or heuristics."""
        # Try LLM first
        actions = self._try_llm_mapping(step, goal)
        if actions:
            return actions
        # Fallback to heuristics
        actions = self._heuristic_mapping(step, goal)
        if actions:
            return actions
        print(f"  [ActionMapper] No mapping found for: {step.description}")
        return []

    def _try_llm_mapping(self, step: PlannedStep, goal: str) -> List[ActionSpec]:
        """Use Claude or Gemini to map step → tools."""
        # Try Claude first
        actions = self._call_claude_for_mapping(step, goal)
        if actions:
            return actions
        # Try Gemini
        actions = self._call_gemini_for_mapping(step, goal)
        if actions:
            return actions
        return []

    def _call_claude_for_mapping(self, step: PlannedStep, goal: str) -> List[ActionSpec]:
        """Ask Claude to map step to tool calls."""
        api_key = self._settings.models.anthropic_api_key
        if not api_key:
            return []
        try:
            import anthropic
        except Exception:
            return []

        client = anthropic.Anthropic(api_key=api_key)
        model = self._settings.models.anthropic_task_model

        prompt = self._build_mapping_prompt(step, goal)
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    text += block.text
            return self._parse_llm_response(text.strip())
        except Exception:
            return []

    def _call_gemini_for_mapping(self, step: PlannedStep, goal: str) -> List[ActionSpec]:
        """Ask Gemini to map step to tool calls."""
        api_key = self._settings.models.gemini_api_key
        if not api_key:
            return []
        try:
            import google.generativeai as genai
        except Exception:
            return []

        genai.configure(api_key=api_key)
        model_name = self._settings.models.gemini_vision_model
        model = genai.GenerativeModel(model_name)

        prompt = self._build_mapping_prompt(step, goal)
        try:
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            actions = self._parse_llm_response(text)
            if not actions:
                print(f"  [ActionMapper] Gemini response couldn't be parsed: {text[:200]}")
            return actions
        except Exception as e:
            print(f"  [ActionMapper] Gemini call failed: {e}")
            return []

    def _build_mapping_prompt(self, step: PlannedStep, goal: str) -> str:
        """Build prompt for LLM to map step to tool calls."""
        return f"""You are an action mapper for a Windows automation agent.

**Overall Goal:** {goal}

**Current Step:** {step.description}

**Available Tools:**
- browser_navigate(url: str) - Open URL in browser
- browser_click(selector: str) - Click element in browser
- browser_type(selector: str, text: str) - Type in browser input
- desktop_click(name: str) - Click Windows UI element by name (e.g. "Control Panel", "Chrome", "PowerPoint")
- desktop_type(name: str, text: str) - Type in Windows UI element
- keyboard_shortcut(name: str) - Execute keyboard shortcut (e.g. "new_slide", "save", "copy", "paste", "new", "volume_up")
- keyboard_press(keys: list) - Press specific keys (e.g. ["ctrl", "m"] for Ctrl+M)
- keyboard_type(text: str) - Type text
- file_read(path: str) - Read file
- file_write(path: str, content: str) - Write file
- file_delete(path: str) - Delete file
- file_copy(src: str, dst: str) - Copy file
- mkdir(path: str) - Create directory
- list_directory(path: str) - List directory contents
- pattern_click(label: str, app_name: str) - Click by visual pattern

**Keyboard Shortcuts Available:**
- new_slide (Ctrl+M) - Add new slide in PowerPoint
- new (Ctrl+N) - New document/file
- save (Ctrl+S) - Save
- copy (Ctrl+C) - Copy
- paste (Ctrl+V) - Paste
- undo (Ctrl+Z) - Undo
- volume_up - Increase volume
- volume_down - Decrease volume

**Your Task:**
Map the current step to one or more tool calls. Return ONLY a JSON array of tool calls in this exact format:
[
  {{"tool": "tool_name", "kwargs": {{"param": "value"}}}}
]

Examples:
- "Open PowerPoint" → [{{"tool": "desktop_click", "kwargs": {{"name": "PowerPoint"}}}}]
- "Add a new slide" → [{{"tool": "keyboard_shortcut", "kwargs": {{"name": "new_slide"}}}}]
- "Open PowerPoint and add a new slide" → [
    {{"tool": "desktop_click", "kwargs": {{"name": "PowerPoint"}}}},
    {{"tool": "keyboard_shortcut", "kwargs": {{"name": "new_slide"}}}}
  ]
- "Copy text and paste it" → [
    {{"tool": "keyboard_shortcut", "kwargs": {{"name": "copy"}}}},
    {{"tool": "keyboard_shortcut", "kwargs": {{"name": "paste"}}}}
  ]
- "Increase volume" → [{{"tool": "keyboard_shortcut", "kwargs": {{"name": "volume_up"}}}}]
- "Create folder reports in C:/Data" → [{{"tool": "mkdir", "kwargs": {{"path": "C:/Data/reports"}}}}]

Return ONLY the JSON array, no other text."""

    def _parse_llm_response(self, text: str) -> List[ActionSpec]:
        """Parse LLM response into ActionSpec list."""
        try:
            # Extract JSON array from response
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if not match:
                return []
            actions_data = json.loads(match.group(0))
            if not isinstance(actions_data, list):
                return []
            
            specs = []
            for item in actions_data:
                if not isinstance(item, dict) or "tool" not in item:
                    continue
                tool_name = item["tool"]
                kwargs = item.get("kwargs", {})
                specs.append(ActionSpec(tool_name=tool_name, kwargs=kwargs))
            return specs
        except Exception:
            return []

    def _heuristic_mapping(self, step: PlannedStep, goal: str) -> List[ActionSpec]:
        """Fallback heuristic mapping for when LLM unavailable."""
        text = (step.description + " " + goal).strip()
        text_lower = text.lower()
        actions: List[ActionSpec] = []
        root_dir = Path(self._settings.paths.root_dir)

        # URL extraction
        url = self._extract_url(text)
        if url and url not in self._navigated_urls:
            actions.append(ActionSpec(tool_name="browser_navigate", kwargs={"url": url}))
            self._navigated_urls.add(url)

        # Path operations
        paths = self._extract_path_candidates(text, root_dir)
        for path in paths:
            path_str = str(path)
            if "list" in text_lower or "contents" in text_lower:
                if path_str not in self._listed_paths:
                    actions.append(ActionSpec(tool_name="list_directory", kwargs={"path": path_str}))
                    self._listed_paths.add(path_str)
                    break
            if "create" in text_lower or "mkdir" in text_lower:
                if path_str not in self._created_dirs:
                    actions.append(ActionSpec(tool_name="mkdir", kwargs={"path": path_str}))
                    self._created_dirs.add(path_str)
                    break

        # Keyboard shortcut patterns
        if any(p in text_lower for p in ["new slide", "add slide", "insert slide"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "new_slide"}))
        elif any(p in text_lower for p in ["new document", "new file", "blank presentation", "new presentation"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "new"}))
        elif any(p in text_lower for p in ["save file", "save document", "save the"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "save"}))
        elif any(p in text_lower for p in ["copy text", "copy the", "copy selection"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "copy"}))
        elif any(p in text_lower for p in ["paste text", "paste the", "paste it"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "paste"}))
        elif any(p in text_lower for p in ["undo", "undo the"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "undo"}))
        elif any(p in text_lower for p in ["increase volume", "volume up", "turn up volume"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "volume_up"}))
        elif any(p in text_lower for p in ["decrease volume", "volume down", "turn down volume", "lower volume"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "volume_down"}))
        elif any(p in text_lower for p in ["mute volume", "mute sound", "mute"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "volume_mute"}))
        elif any(p in text_lower for p in ["take screenshot", "screenshot", "screen capture"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "screenshot"}))
        elif any(p in text_lower for p in ["open settings", "windows settings"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "settings"}))
        elif any(p in text_lower for p in ["open file explorer", "open explorer"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "file_explorer"}))
        elif any(p in text_lower for p in ["select all", "select everything"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "select_all"}))
        elif any(p in text_lower for p in ["find text", "search text", "find in"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "find"}))
        elif any(p in text_lower for p in ["print document", "print the", "print page"]):
            actions.append(ActionSpec(tool_name="keyboard_shortcut", kwargs={"name": "print"}))

        # Desktop UI patterns - open/launch/click applications
        if not actions:
            app_name = self._extract_app_name(text_lower)
            if app_name:
                actions.append(ActionSpec(tool_name="desktop_click", kwargs={"name": app_name}))

        return actions

    def _extract_app_name(self, text_lower: str) -> str | None:
        """Extract application name from text."""
        known_apps = {
            "control panel": "Control Panel",
            "chrome": "Chrome",
            "google chrome": "Google Chrome",
            "firefox": "Firefox",
            "edge": "Microsoft Edge",
            "notepad": "Notepad",
            "calculator": "Calculator",
            "paint": "Paint",
            "word": "Word",
            "excel": "Excel",
            "powerpoint": "PowerPoint",
            "outlook": "Outlook",
            "teams": "Teams",
            "task manager": "Task Manager",
            "command prompt": "Command Prompt",
            "cmd": "Command Prompt",
            "powershell": "PowerShell",
            "terminal": "Terminal",
            "file explorer": "File Explorer",
            "explorer": "File Explorer",
            "settings": "Settings",
            "recycle bin": "Recycle Bin",
            "microsoft defender": "Microsoft Defender",
            "defender": "Windows Security",
            "snipping tool": "Snipping Tool",
        }
        for key, name in known_apps.items():
            if key in text_lower:
                return name
        
        # Try to extract app name from "open X" / "launch X" / "start X" patterns
        import re
        for pattern in [r"open\s+(.+?)(?:\s+and\s+|\s*$)", r"launch\s+(.+?)(?:\s+and\s+|\s*$)", r"start\s+(.+?)(?:\s+and\s+|\s*$)"]:
            m = re.search(pattern, text_lower)
            if m:
                candidate = m.group(1).strip()
                # Clean up
                for suffix in [" application", " app", " browser", " program"]:
                    if candidate.endswith(suffix):
                        candidate = candidate[:-len(suffix)].strip()
                if candidate and len(candidate) < 40:
                    return candidate.title()
        
        return None

    def _extract_url(self, text: str) -> Optional[str]:
        """Return first http(s) URL found in text, or None."""
        m = re.search(r"https?://[^\s\]\)\"']+", text, re.IGNORECASE)
        return m.group(0) if m else None

    def _extract_path_candidates(self, text: str, root: Path) -> List[Path]:
        """Heuristic: find path-like strings."""
        out: List[Path] = []
        for m in re.finditer(r"[A-Za-z]:[/\\][^\s\]\)\"']+", text):
            p = Path(m.group(0).replace("/", "\\"))
            if p.is_absolute():
                out.append(p)
        return out

