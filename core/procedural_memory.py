from __future__ import annotations

"""
Procedural Memory - Task guidelines and action documentation.

Provides structured guidelines for the agent on:
- When to use different execution levels (L0-L5)
- How to use the Code Agent
- Action timing and verification best practices
- Available actions and their signatures

This is dynamically included in LLM system prompts to improve decision-making.
"""

import inspect
import platform
from typing import Dict, Any, Callable


class ProceduralMemory:
    """
    Builds comprehensive system prompts with task guidelines and action documentation.

    Inspired by Agent S3's procedural memory system, adapted for the hybrid agent's
    multi-level execution hierarchy.
    """

    CORE_GUIDELINES = """# AGENT GUIDELINES

## Execution Level Selection

Your hybrid agent has multiple execution levels. Choose wisely:

- **L0 (Programmatic)**: Direct file I/O, API calls
  - Speed: <10ms per action
  - Use for: Creating/deleting files, reading/writing content, directory operations
  - Reliability: 95%+
  - ALWAYS try L0 first for file operations

- **L1 (Browser DOM)**: Playwright-based web automation
  - Speed: ~50ms per action
  - Use for: Web forms, clicking links, filling inputs, navigation
  - Reliability: 85%+ for structured web UIs
  - ALWAYS try L1 first for browser tasks

- **L2 (Desktop UI Tree)**: Native UI automation (pywinauto on Windows)
  - Speed: ~100ms per action
  - Use for: Desktop applications, native dialogs, system UI
  - Reliability: 70%+ for standard Windows apps
  - ALWAYS try L2 first for desktop apps

- **L3 (Template Matching)**: OpenCV-based visual pattern matching
  - Speed: ~200ms per action
  - Use for: Finding icons, buttons, UI elements by appearance
  - Reliability: 60%+ (lighting/scaling dependent)
  - Use when L0-L2 fail or for visual-only tasks

- **L4 (Local Vision)**: Qwen2-VL local vision model
  - Speed: ~2s per action (GPU dependent)
  - Use for: Privacy-sensitive tasks requiring vision
  - Reliability: 65%+
  - Currently: STUB (not implemented)

- **L5 (Cloud Vision)**: Gemini/Nova cloud vision models
  - Speed: ~4s per action
  - Use for: Complex visual understanding, OCR, last resort
  - Reliability: 75%+
  - ONLY use when L0-L4 fail or for vision-only tasks

**Strategy**: Always start with the fastest level that can accomplish the task.
The system automatically falls back to slower levels if needed.

## Code Agent Usage

Use the Code Agent for:
- **Spreadsheet calculations**: Formulas, sums, data filling
- **Bulk operations**: Process 100+ files, mass renaming, data transformation
- **Data processing**: Filter, sort, aggregate, calculations
- **Complex file operations**: Multi-step file manipulations

**DO NOT** use Code Agent for:
- Simple file operations (use L0 instead)
- Single clicks or form fills (use L1/L2 instead)
- Tasks better suited for GUI automation

**ALWAYS** verify Code Agent results with GUI actions:
- Open the file to confirm changes
- Check the output visually
- Don't trust code output blindly

## Action Timing

- **After opening apps**: Wait 3-5 seconds for loading
- **After clicking**: Wait 0.5-1 second for UI updates
- **After typing**: Wait 0.3 seconds for input to register
- **After keyboard shortcuts**: Wait 1 second for action to complete
- **App launches**: Wait longer (5+ seconds) for heavy applications

## Verification Best Practices

1. **Always verify action success**: Don't assume actions worked
2. **Check visual feedback**: Look for state changes in screenshots
3. **Use reflection**: Analyze before/after states
4. **Retry on failure**: Try alternative approaches
5. **Detect stuck states**: If repeating the same action 3+ times, try different approach

## Knowledge Accumulation

- **Add facts to knowledge buffer**: When you discover state (e.g., "Chrome is open")
- **Reference knowledge**: Check buffer before redundant actions
- **Keep buffer updated**: Remove obsolete facts

## Error Handling

- **Permission errors**: May need elevated privileges or different path
- **Timeout errors**: App may need more time to load
- **Element not found**: Try vision-based fallback (L5)
- **Stuck in loop**: Use reflection agent to diagnose and change approach
"""

    PLATFORM_NOTES = {
        "Windows": """
## Windows-Specific Notes

- Use forward slashes in file paths (e.g., "E:/data/file.txt")
- L2 (Desktop UI) works best on Windows (pywinauto)
- Some apps may require "Run as Administrator"
- Window management: Foreground window is automatically moved to primary monitor
""",
        "Darwin": """
## macOS-Specific Notes

- L2 (Desktop UI) support is LIMITED (needs AppleScript integration)
- Use L1 (Browser) or L5 (Vision) instead for most UI tasks
- File paths use forward slashes (native)
""",
        "Linux": """
## Linux-Specific Notes

- L2 (Desktop UI) support is LIMITED (needs AT-SPI integration)
- Use L1 (Browser) or L5 (Vision) instead for most UI tasks
- File paths use forward slashes (native)
"""
    }

    RESPONSE_FORMAT = """
## Response Format

When planning actions:
1. **Verify previous action**: Check if it succeeded
2. **Assess current state**: What's visible on screen?
3. **Choose execution level**: Which level is fastest for this task?
4. **Specify action**: Clear, specific action with parameters
5. **Explain reasoning**: Why this approach?

Example:
```
Previous action: ✓ Clicked Chrome icon
Current state: Chrome window is open
Next action: Navigate to google.com using L1 (Browser DOM)
Reasoning: L1 is fastest for web navigation
```
"""

    @staticmethod
    def build_system_prompt(
        task: str,
        available_actions: Dict[str, Callable] = None
    ) -> str:
        """
        Build comprehensive system prompt with guidelines and action documentation.

        Args:
            task: The task description
            available_actions: Optional dict of {action_name: action_function}

        Returns:
            Complete system prompt string
        """
        system_platform = platform.system()
        platform_notes = ProceduralMemory.PLATFORM_NOTES.get(system_platform, "")

        prompt_parts = [
            f"# TASK\n\n{task}\n",
            ProceduralMemory.CORE_GUIDELINES,
            platform_notes,
            ProceduralMemory.RESPONSE_FORMAT
        ]

        # Add available actions if provided
        if available_actions:
            actions_doc = ProceduralMemory._document_actions(available_actions)
            prompt_parts.append(f"\n# AVAILABLE ACTIONS\n\n{actions_doc}")

        return "\n".join(prompt_parts)

    @staticmethod
    def _document_actions(actions: Dict[str, Callable]) -> str:
        """
        Generate documentation for available actions.

        Args:
            actions: Dictionary of {action_name: action_function}

        Returns:
            Formatted action documentation
        """
        lines = []
        for name, func in sorted(actions.items()):
            try:
                sig = inspect.signature(func)
                doc = inspect.getdoc(func) or "No description available."

                lines.append(f"## {name}{sig}")
                lines.append(f"{doc}\n")

            except Exception:
                lines.append(f"## {name}")
                lines.append("Documentation unavailable.\n")

        return "\n".join(lines)

    @staticmethod
    def get_quick_reference() -> str:
        """
        Get a condensed quick reference guide.

        Returns:
            Short reference string for inline inclusion
        """
        return """Quick Reference:
- L0 (Files): <10ms, 95% reliability
- L1 (Browser): ~50ms, 85% reliability
- L2 (Desktop): ~100ms, 70% reliability
- L5 (Vision): ~4s, 75% reliability

Always: L0/L1/L2 first → fallback to L5
Code Agent: Use for bulk operations, verify results
Wait: 3-5s after app launch, 0.5-1s after actions
Verify: Always check action success before proceeding"""


class ProceduralMemoryBuilder:
    """
    Fluent builder for constructing custom procedural memory prompts.

    Usage:
        prompt = (ProceduralMemoryBuilder()
                  .with_task("Open Chrome and search for Python")
                  .with_platform_notes()
                  .with_actions(available_actions)
                  .with_quick_reference()
                  .build())
    """

    def __init__(self):
        self._parts = []

    def with_task(self, task: str) -> ProceduralMemoryBuilder:
        """Add task description."""
        self._parts.append(f"# TASK\n\n{task}\n")
        return self

    def with_core_guidelines(self) -> ProceduralMemoryBuilder:
        """Add core execution guidelines."""
        self._parts.append(ProceduralMemory.CORE_GUIDELINES)
        return self

    def with_platform_notes(self) -> ProceduralMemoryBuilder:
        """Add platform-specific notes."""
        system_platform = platform.system()
        notes = ProceduralMemory.PLATFORM_NOTES.get(system_platform, "")
        if notes:
            self._parts.append(notes)
        return self

    def with_response_format(self) -> ProceduralMemoryBuilder:
        """Add response format guidelines."""
        self._parts.append(ProceduralMemory.RESPONSE_FORMAT)
        return self

    def with_actions(self, actions: Dict[str, Callable]) -> ProceduralMemoryBuilder:
        """Add action documentation."""
        actions_doc = ProceduralMemory._document_actions(actions)
        self._parts.append(f"\n# AVAILABLE ACTIONS\n\n{actions_doc}")
        return self

    def with_quick_reference(self) -> ProceduralMemoryBuilder:
        """Add quick reference guide."""
        self._parts.append(f"\n# QUICK REFERENCE\n\n{ProceduralMemory.get_quick_reference()}")
        return self

    def with_custom_section(self, title: str, content: str) -> ProceduralMemoryBuilder:
        """Add a custom section."""
        self._parts.append(f"\n# {title.upper()}\n\n{content}")
        return self

    def build(self) -> str:
        """Build the final prompt."""
        return "\n".join(self._parts)
