from __future__ import annotations

"""
Hybrid AI Agent – ShellAdapter.

Simple synchronous shell command execution adapter.
"""

from dataclasses import dataclass
from subprocess import CompletedProcess, run
from typing import List


@dataclass
class ShellResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str


class ShellAdapter:
    """
    Minimal shell adapter for running commands.

    NOTE: This bypasses TransactionManager and should be restricted to
    read-only or low-risk commands in early versions.
    """

    def run(self, args: List[str], cwd: str | None = None, timeout: int | None = None) -> ShellResult:
        proc: CompletedProcess[bytes] = run(
            args,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
        )
        return ShellResult(
            success=proc.returncode == 0,
            returncode=proc.returncode,
            stdout=proc.stdout.decode("utf-8", errors="replace"),
            stderr=proc.stderr.decode("utf-8", errors="replace"),
        )

