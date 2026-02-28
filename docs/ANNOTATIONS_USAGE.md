# How Annotations Are Used in This Project

## Summary

**Visual annotations** (red boxes, keyboard indicators) were added for an "AI teacher" / training-demo use case: showing students *where* to click when teaching Windows (e.g. "Open Control Panel").

## Where they were used

| Location | Purpose |
|----------|--------|
| **`core/visual_annotator.py`** | Defines `VisualAnnotator`: `highlight_area()`, `show_keyboard_shortcut()`, `show_action_label()`, `clear_annotations()`. Draws on screen via Win32 GDI. |
| **`execution/start_menu_helper.py`** | **Only consumer.** When opening an app via Start menu search (e.g. "Open Control Panel"), it called the annotator to: show "Win+S", draw a red box around the search area, show "Enter", then clear. |
| **`scripts/demo_ai_teacher.py`** | Demo script that runs `Level2UiTreeExecutor.desktop_click("Control Panel")` and prints text about annotations; it does not call the annotator directly. |

## Where they are NOT used

- **`main.py`** – uses `AgentLoop` only; no annotations.
- **Agent loop / execution hierarchy** – no annotation calls.
- **Level 0, 1, 3, 4, 5** – no annotation calls.
- **Level 2** – only uses annotations indirectly when it calls `StartMenuSearchHelper.search_and_click()`.

So in this project, annotations were used **only** when the agent opened something via **Start menu search** (Win+S → type → Enter). All other tasks (filesystem, browser, etc.) never used annotations.

## Current state

Annotations have been **removed** from the Start Menu flow. The annotator module (`core/visual_annotator.py`) remains in the repo but is unused. You can delete it and `docs/ANNOTATIONS_USAGE.md` if you want to clean up fully.
