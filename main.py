from __future__ import annotations

"""
Hybrid AI Agent – minimal entry point.

For now this only:
- Loads configuration from config/settings.py
- Instantiates a bare StateModel
- Prints a short bootstrap message

This is the "hello world" for the agent skeleton.
"""

from config.settings import get_settings
from core.agent_loop import AgentLoop
import sys


def main() -> None:
    settings = get_settings()

    print("Hybrid AI Agent bootstrap")
    print(f"- Environment : {settings.runtime.environment}")
    print(f"- Log level   : {settings.runtime.log_level}")
    print(f"- Root dir    : {settings.paths.root_dir}")

    if len(sys.argv) > 1:
        goal_description = " ".join(sys.argv[1:])
    else:
        goal_description = (
            "Start a coding session by opening the Python website in a browser, "
            "then under E:\\ui-agent\\sessions create today’s folder named with "
            "the current date (YYYY-MM-DD), write a plan.md file that lists three "
            "bullet points: Review Python docs, Try new features, Summarize "
            "learnings, and finally list the contents of the new session folder."
        )

    loop = AgentLoop()
    result = loop.run(goal_description)

    print("\nAgent loop result:")
    print(f"- Goal        : {goal_description}")
    print(f"- Status      : {result.goal_status}")
    print(f"- Steps       : {result.steps_executed}")
    print(f"- Final node  : {result.final_node_id}")


if __name__ == "__main__":
    main()

