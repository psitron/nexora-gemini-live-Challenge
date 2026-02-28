from __future__ import annotations

"""
Hybrid AI Agent – human_loop.interactive

Interactive human-in-the-loop for terminal usage.

When all automated levels fail, the agent can call into this module to
present context and request a free-form hint from the human operator.
"""

from typing import Optional

from human_loop.context_packager import HumanContext
from human_loop.hint_parser import ParsedHint, parse_hint


class InteractiveHumanLoop:
    """
    Minimal terminal-based human loop.
    """

    def request_hint(self, context: HumanContext) -> ParsedHint:
        """
        Print context to stdout and read a single-line hint from stdin.
        In non-interactive environments this may block; it is intended
        primarily for local development and debugging.
        """
        data = context.to_dict()
        print("\n=== HUMAN LOOP ACTIVATED ===")
        print(f"Goal: {data['goal']}")
        print("Plan steps:")
        for i, step in enumerate(data["plan_steps"], start=1):
            print(f"  {i}. {step}")
        print(f"Last outcome: {data['last_outcome']} - {data['last_reason']}")
        if data.get("notes"):
            print(f"Notes: {data['notes']}")

        try:
            hint_text = input("Enter a hint for the agent (single line): ").strip()
        except EOFError:
            hint_text = ""

        if not hint_text:
            return ParsedHint(action="noop", target=None, extra=None)

        return parse_hint(hint_text)

