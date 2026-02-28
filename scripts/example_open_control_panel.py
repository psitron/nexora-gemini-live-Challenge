r"""
End-to-end example: Open Control Panel using the agent.

Demonstrates the full agent loop:
1. Goal: "Open Control Panel"
2. Planner breaks it into steps (using LLM or fallback)
3. ActionMapper maps to desktop_click(name="Control Panel") (using LLM or heuristic)
4. ExecutionHierarchy tries L2 (UI tree), L3 (pattern), L4/L5 (vision)
5. Verifier checks if Control Panel window opened
6. Result reported

Run from project root (with venv active):
  python scripts/example_open_control_panel.py

Requirements: pywinauto (for L2 desktop automation)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent_loop import AgentLoop


def main() -> None:
    goal = "Open Control Panel"
    
    print("=" * 60)
    print("Hybrid AI Agent - End-to-End Example")
    print("=" * 60)
    print(f"\nGoal: {goal}")
    print("\nThis demonstrates:")
    print("  1. LLM-based planning (or fallback)")
    print("  2. LLM-based action mapping (or heuristic)")
    print("  3. Multi-level execution (L2 UI tree → L3 pattern → L4/L5 vision)")
    print("  4. Verification")
    print("\n" + "-" * 60)
    
    loop = AgentLoop()
    result = loop.run(goal)
    
    print("\n" + "=" * 60)
    print("Result:")
    print("=" * 60)
    print(f"Status:    {result.goal_status}")
    print(f"Steps:     {result.steps_executed}")
    print(f"Final node: {result.final_node_id}")
    print(f"Outcomes:  {len(result.outcomes)}")
    
    if result.outcomes:
        print("\nStep outcomes:")
        for i, outcome in enumerate(result.outcomes, 1):
            print(f"  {i}. {outcome.classification}")
    
    if result.goal_status == "FAILED":
        print("\nNote: Goal validation may have failed, or no Control Panel found.")
        print("      This is expected if Control Panel isn't easily accessible via UI tree.")
        print("      Vision fallback (L4/L5) would handle this if wired to a real VLM.")
    else:
        print("\nSuccess! Check if Control Panel window opened.")


if __name__ == "__main__":
    main()
