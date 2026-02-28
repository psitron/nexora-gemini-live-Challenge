from __future__ import annotations

"""
Hybrid AI Agent – project scaffold script.

Run once from the project root to create the folder structure and all
referenced module files from the PRD as empty stubs, plus package
`__init__.py` files where appropriate.
"""

from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parent


PACKAGE_DIRS: list[str] = [
    "goal_spec",
    "core",
    "verifier",
    "state_graph",
    "transaction",
    "latency_policy",
    "safety",
    "execution",
    "adapters",
    "perception",
    "perception/structured",
    "perception/visual",
    "element_id",
    "trajectory",
    "human_loop",
    "config",
    "templates",
    "memory",
    "tests",
]


MODULE_FILES: list[str] = [
    # v5.0 additions and updates
    "perception/normaliser.py",
    "perception/schemas.py",
    "core/state_model.py",
    "config/tool_contracts.py",
    "config/latency_thresholds.py",
    "execution/level3_pattern.py",
    "execution/level4_local_vision.py",
    "latency_policy/policy.py",
    "safety/classifier.py",
    "config/template_matching.py",
    "perception/visual/vlm_reader.py",
    "verifier/expectation_matcher.py",
    "element_id/resolver.py",
    "core/agent_loop.py",
    # Core architecture (v1–v4 modules)
    "main.py",
    "goal_spec/compiler.py",
    "goal_spec/validator.py",
    "core/planner_task.py",
    "core/planner_execution.py",
    "core/evidence_planner.py",
    "core/goal_tracker.py",
    "core/governance_budget.py",
    "core/deadlock_detector.py",
    "verifier/pre_state.py",
    "verifier/post_state.py",
    "verifier/diff_engine.py",
    "verifier/outcome_classifier.py",
    "state_graph/graph.py",
    "state_graph/node.py",
    "state_graph/edge.py",
    "transaction/manager.py",
    "transaction/compensating.py",
    "transaction/trash.py",
    "latency_policy/profiler.py",
    "safety/simulator.py",
    "safety/confirmation.py",
    "safety/action_logger.py",
    "safety/sandbox.py",
    "execution/hierarchy.py",
    "execution/level0_programmatic.py",
    "execution/level1_dom.py",
    "execution/level2_ui_tree.py",
    "execution/level5_cloud_vision.py",
    "execution/level6_human.py",
    "adapters/browser_adapter.py",
    "adapters/windows_ui_adapter.py",
    "adapters/filesystem_adapter.py",
    "adapters/shell_adapter.py",
    "adapters/api_adapter.py",
    "perception/structured/dom_reader.py",
    "perception/structured/ui_tree_reader.py",
    "perception/structured/screen_hasher.py",
    "perception/visual/screenshot.py",
    "perception/visual/omniparser.py",
    "element_id/element_id.py",
    "trajectory/element_fingerprints.py",
    "trajectory/action_templates.py",
    "trajectory/failure_patterns.py",
    "trajectory/navigation_paths.py",
    "trajectory/db.py",
    "human_loop/interactive.py",
    "human_loop/context_packager.py",
    "human_loop/hint_parser.py",
    "memory/session_memory.py",
    "memory/persistent_memory.py",
    "config/settings.py",
    "config/safety_rules.py",
    # Marker so the .cursorrules file exists in the repo
    ".cursorrules",
]


STUB_HEADER = '"""Stub module generated from Hybrid AI Agent PRD v5.0.\n\nFill this file using the corresponding Cursor prompt from the PRD.\n"""\n'


def ensure_directories(dirs: Iterable[str]) -> None:
    for d in dirs:
        path = BASE_DIR / d
        path.mkdir(parents=True, exist_ok=True)


def ensure_package_inits(dirs: Iterable[str]) -> None:
    for d in dirs:
        pkg_init = BASE_DIR / d / "__init__.py"
        if not pkg_init.exists():
            pkg_init.write_text(
                '"""Package initialiser for Hybrid AI Agent component."""\n',
                encoding="utf-8",
            )


def ensure_module_files(files: Iterable[str]) -> None:
    for rel in files:
        path = BASE_DIR / rel
        if path.exists():
            continue
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        if path.name == ".cursorrules":
            # Leave .cursorrules empty here; you will paste the v5.0
            # rules from the PRD or let Cursor generate them.
            path.write_text(
                "# Hybrid AI Agent .cursorrules – fill with v5.0 rules from PRD.\n",
                encoding="utf-8",
            )
        elif path.suffix == ".py":
            path.write_text(STUB_HEADER, encoding="utf-8")
        else:
            path.touch()


def main() -> None:
    print(f"Scaffolding Hybrid AI Agent project in {BASE_DIR}")
    ensure_directories(PACKAGE_DIRS)
    ensure_package_inits(PACKAGE_DIRS)
    ensure_module_files(MODULE_FILES)
    print("Scaffold complete.")


if __name__ == "__main__":
    main()

