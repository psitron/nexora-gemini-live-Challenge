"""
Hybrid AI Agent – latency benchmark (L0 actions).

Run from project root: python scripts/latency_benchmark.py
Prints average ms per tool from LatencyProfiler after N iterations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

# Run from repo root so imports work
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution.hierarchy import ExecutionHierarchy


def main() -> None:
    n = 5
    h = ExecutionHierarchy()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        sub = tmp_path / "bench_sub"
        sub.mkdir()
        file_a = sub / "a.txt"
        file_a.write_text("hello")

        for _ in range(n):
            h.attempt("list_directory", path=str(sub))
        for _ in range(n):
            h.attempt("mkdir", path=str(tmp_path / "dummy"))
        for _ in range(n):
            h.attempt("file_write", path=str(sub / "b.txt"), content="world")

    samples = h._profiler.recent_samples
    by_level: dict[str, list[str]] = {}
    for _key, s in samples.items():
        level = s.level
        by_level.setdefault(level, []).append(f"  {s.tool_name}: {s.elapsed_ms} ms (success={s.success})")

    print("Latency benchmark (last run samples):")
    for level in sorted(by_level):
        print(level)
        for line in list(by_level[level])[-5:]:
            print(line)
    policy = h._profiler.policy
    if policy.stats:
        print("\nPolicy stats (avg ms):")
        for level, stat in sorted(policy.stats.items()):
            print(f"  {level}: calls={stat.calls}, avg_ms={stat.avg_ms:.1f}, successes={stat.successes}")


if __name__ == "__main__":
    main()
