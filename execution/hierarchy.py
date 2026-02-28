from __future__ import annotations

"""
Hybrid AI Agent – ExecutionHierarchy.

Routes high-level tool names to concrete executors across levels
L0–L5, using LatencyPolicy + TOOL_AFFINITY_MAP ordering.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from execution.level0_programmatic import Level0ProgrammaticExecutor, ActionResult
from execution.level1_dom import Level1DomExecutor
from execution.level2_ui_tree import Level2UiTreeExecutor
from execution.level3_pattern import PatternMatchExecutor
from execution.level4_local_vision import Level4LocalVisionExecutor
from execution.level5_cloud_vision import Level5CloudVisionExecutor
from execution.mouse_controller import click_center_of_bbox
from execution.keyboard_controller import execute_shortcut, press_keys, type_text
from latency_policy.profiler import LatencyProfiler

if TYPE_CHECKING:
    from core.state_model import StateModel


class ExecutionHierarchy:
    def __init__(self) -> None:
        self._l0 = Level0ProgrammaticExecutor()
        self._l1 = Level1DomExecutor()
        self._l2 = Level2UiTreeExecutor()
        self._l3 = PatternMatchExecutor()
        self._l4 = Level4LocalVisionExecutor()
        self._l5 = Level5CloudVisionExecutor()
        self._profiler = LatencyProfiler()

    def attempt(
        self,
        tool_name: str,
        *,
        state: StateModel | None = None,
        **kwargs: Any,
    ) -> ActionResult:
        """
        Choose execution levels using TOOL_AFFINITY_MAP, then attempt the tool
        at each level in order until one succeeds. Pass state for L4/L5 vision.
        """
        levels = self._profiler.policy.choose_levels(tool_name)
        last_result: ActionResult | None = None
        for level in levels:
            result = self._attempt_level(level, tool_name, state=state, **kwargs)
            if result is None:
                continue
            last_result = result
            if result.success:
                return result
        if last_result is not None:
            return last_result
        return ActionResult(False, f"Unknown tool: {tool_name}")

    def _attempt_level(
        self,
        level: str,
        tool_name: str,
        *,
        state: StateModel | None = None,
        **kwargs: Any,
    ) -> ActionResult | None:
        # Keyboard tools (works at L0 level - direct system calls)
        if level == "L0_PROGRAMMATIC":
            if tool_name == "keyboard_shortcut":
                kb_result = execute_shortcut(kwargs["name"])
                return ActionResult(kb_result.success, kb_result.message)
            if tool_name == "keyboard_press":
                keys = kwargs.get("keys", [])
                if not isinstance(keys, list):
                    return ActionResult(False, "keyboard_press requires 'keys' as list")
                kb_result = press_keys(*keys, annotation=True)
                return ActionResult(kb_result.success, kb_result.message)
            if tool_name == "keyboard_type":
                kb_result = type_text(kwargs["text"])
                return ActionResult(kb_result.success, kb_result.message)
        
        if level == "L0_PROGRAMMATIC":
            if tool_name == "file_read":
                return self._profiler.time_call(
                    level, tool_name, self._l0.file_read, Path(kwargs["path"])
                )
            if tool_name == "file_write":
                return self._profiler.time_call(
                    level,
                    tool_name,
                    self._l0.file_write,
                    Path(kwargs["path"]),
                    kwargs["content"],
                )
            if tool_name == "file_delete":
                return self._profiler.time_call(
                    level, tool_name, self._l0.file_delete, Path(kwargs["path"])
                )
            if tool_name == "file_copy":
                return self._profiler.time_call(
                    level,
                    tool_name,
                    self._l0.file_copy,
                    Path(kwargs["src"]),
                    Path(kwargs["dst"]),
                )
            if tool_name == "list_directory":
                return self._profiler.time_call(
                    level,
                    tool_name,
                    self._l0.list_directory,
                    Path(kwargs["path"]),
                )
            if tool_name == "mkdir":
                return self._profiler.time_call(
                    level, tool_name, self._l0.mkdir, Path(kwargs["path"])
                )

        if level == "L1_DOM":
            if tool_name == "browser_navigate":
                return self._profiler.time_call(
                    level, tool_name, self._l1.navigate, kwargs["url"]
                )
            if tool_name == "browser_click":
                return self._profiler.time_call(
                    level, tool_name, self._l1.click, kwargs["selector"]
                )
            if tool_name == "browser_type":
                return self._profiler.time_call(
                    level,
                    tool_name,
                    self._l1.type_text,
                    kwargs["selector"],
                    kwargs["text"],
                )

        if level == "L2_UI_TREE":
            if tool_name == "desktop_click":
                return self._profiler.time_call(
                    level, tool_name, self._l2.desktop_click, kwargs["name"]
                )
            if tool_name == "desktop_type":
                return self._profiler.time_call(
                    level,
                    tool_name,
                    self._l2.desktop_type,
                    kwargs["name"],
                    kwargs["text"],
                )

        if level == "L3_PATTERN":
            if tool_name == "pattern_click":
                match_result = self._profiler.time_call(
                    level,
                    tool_name,
                    self._l3.capture_and_match,
                    kwargs["label"],
                    kwargs.get("app_name", "app"),
                )
                if not match_result.success or not match_result.data:
                    return match_result
                match = match_result.data.get("match")
                if match is None or not getattr(match, "bbox", None):
                    return match_result

                mouse_res = click_center_of_bbox(match.bbox)
                combined_message = f"{match_result.message} then {mouse_res.message}"
                return ActionResult(
                    success=mouse_res.success,
                    message=combined_message,
                    data={"bbox": match.bbox, "confidence": getattr(match, "confidence", None)},
                )

        # L4 local VLM / L5 cloud VLM: need state.environment for grounding
        if level in ("L4_LOCAL_VLM", "L5_CLOUD") and state is not None and state.environment is not None:
            env = state.environment
            action_desc = "click"
            element_desc = (
                kwargs.get("element_description")
                or kwargs.get("selector")
                or kwargs.get("name")
                or "clickable element"
            )
            if tool_name in ("browser_click", "desktop_click"):
                executor = self._l4 if level == "L4_LOCAL_VLM" else self._l5
                res = executor.execute(env, action_desc, element_desc)
                if not res.success:
                    return res
                bbox = res.data.get("bbox") if res.data else None
                if bbox:
                    mouse_res = click_center_of_bbox(bbox)
                    return ActionResult(
                        success=mouse_res.success,
                        message=f"{res.message} then {mouse_res.message}",
                        data=res.data,
                    )
                return res

        return None

