from __future__ import annotations

"""
Hybrid AI Agent – environment and wiring verifier.

Run this after:
  1) Creating the scaffold (python scaffold.py)
  2) Creating a real .env from .env.template and filling keys

It checks:
  - Python version
  - Core Python dependencies installed
  - Expected folders and key files exist
  - Critical environment variables are set
  - Optionally performs tiny "hello world" calls to Anthropic and/or Gemini
"""

import importlib
import os
import sys
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


REQUIRED_PACKAGES: List[str] = [
    "anthropic",            # Claude planners
    "google.generativeai",  # Gemini Flash vision (deprecated but importable)
    "playwright",           # DOM-level execution
    "pywinauto",            # Windows UI tree
    "mss",                  # Screenshot capture
    "cv2",                  # OpenCV template matching (cv2 module)
    "PIL",                  # Pillow for image handling
    "imagehash",            # Screen hasher
    "deepdiff",             # State diffing
    "gradio",               # Optional UI, but nice to have
]


REQUIRED_ENV_VARS: List[str] = [
    # Core paths / storage
    "TRAJECTORY_DB_PATH",
    "ACTION_LOG_DB_PATH",
    "TEMPLATE_DIR",
    "AGENT_TRASH_DIR",
    "AGENT_BACKUP_DIR",
    "AGENT_REG_BACKUP_DIR",
]

# Optional provider-specific variables (warn if missing, but do not fail)
OPTIONAL_ENV_VARS: List[str] = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_TASK_MODEL",
    "ANTHROPIC_EXECUTION_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_VISION_MODEL",
    "QWEN_VL_ENDPOINT",
    "QWEN_VL_API_KEY",
    "QWEN_VL_MODEL",
]


EXPECTED_DIRS: List[Path] = [
    BASE_DIR / "goal_spec",
    BASE_DIR / "core",
    BASE_DIR / "verifier",
    BASE_DIR / "state_graph",
    BASE_DIR / "transaction",
    BASE_DIR / "latency_policy",
    BASE_DIR / "safety",
    BASE_DIR / "execution",
    BASE_DIR / "adapters",
    BASE_DIR / "perception",
    BASE_DIR / "perception" / "structured",
    BASE_DIR / "perception" / "visual",
    BASE_DIR / "element_id",
    BASE_DIR / "trajectory",
    BASE_DIR / "human_loop",
    BASE_DIR / "config",
    BASE_DIR / "templates",
    BASE_DIR / "memory",
    BASE_DIR / "tests",
]


EXPECTED_FILES: List[Path] = [
    BASE_DIR / "main.py",
    BASE_DIR / ".cursorrules",
    BASE_DIR / "config" / "settings.py",
    BASE_DIR / "core" / "state_model.py",
    BASE_DIR / "core" / "agent_loop.py",
    BASE_DIR / "core" / "planner_task.py",
    BASE_DIR / "core" / "planner_execution.py",
    BASE_DIR / "config" / "tool_contracts.py",
    BASE_DIR / "config" / "latency_thresholds.py",
    BASE_DIR / "latency_policy" / "policy.py",
    BASE_DIR / "safety" / "classifier.py",
]


def check_python_version() -> Tuple[bool, str]:
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        return False, f"Python 3.11+ required, found {major}.{minor}"
    return True, f"Python version OK: {major}.{minor}"


def check_packages() -> Tuple[bool, List[str]]:
    missing: List[str] = []
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
        except Exception:
            missing.append(pkg)
    return not missing, missing


def check_env_vars() -> Tuple[bool, List[str]]:
    missing_required: List[str] = []
    for key in REQUIRED_ENV_VARS:
        if not os.getenv(key):
            missing_required.append(key)
    return not missing_required, missing_required


def check_optional_env_vars() -> List[str]:
    missing_optional: List[str] = []
    for key in OPTIONAL_ENV_VARS:
        if not os.getenv(key):
            missing_optional.append(key)
    return missing_optional


def check_paths() -> Tuple[bool, List[str]]:
    missing: List[str] = []

    for d in EXPECTED_DIRS:
        if not d.exists() or not d.is_dir():
            missing.append(f"Missing directory: {d}")

    for f in EXPECTED_FILES:
        if not f.exists():
            missing.append(f"Missing file: {f}")

    return not missing, missing


def test_claude_hello_world() -> Tuple[bool, str]:
    """
    Perform a single tiny Anthropic call as an end-to-end smoke test.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return True, "ANTHROPIC_API_KEY not set; skipping Claude smoke test (ok)."

    try:
        import anthropic  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure path
        return False, f"anthropic package not importable: {exc}"

    client = anthropic.Anthropic(api_key=api_key)

    model = os.getenv("ANTHROPIC_TASK_MODEL", "claude-3-5-sonnet-20241022")

    try:
        _ = client.messages.create(
            model=model,
            max_tokens=16,
            messages=[
                {"role": "user", "content": "Say 'hello from Hybrid AI Agent skeleton' and nothing else."}
            ],
        )
    except Exception as exc:  # pragma: no cover - network path
        return False, f"Claude API call failed: {exc}"

    return True, "Claude hello-world call succeeded."


def test_gemini_hello_world() -> Tuple[bool, str]:
    """
    Perform a tiny Gemini call as an alternative smoke test.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return True, "GEMINI_API_KEY not set; skipping Gemini smoke test (ok)."

    try:
        import google.generativeai as genai  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure path
        return False, f"google-generativeai package not importable: {exc}"

    genai.configure(api_key=api_key)
    from config.settings import load_settings
    model_name = load_settings().models.gemini_vision_model

    try:
        model = genai.GenerativeModel(model_name)
        _ = model.generate_content("Say 'hello from Hybrid AI Agent skeleton' and nothing else.")
    except Exception as exc:  # pragma: no cover - network path
        return False, f"Gemini API call failed: {exc}"

    return True, "Gemini hello-world call succeeded."


def main() -> None:
    print("Hybrid AI Agent – verify_setup\n")

    # Load environment variables from .env if present so users do not need
    # to export them manually.
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    ok_py, msg_py = check_python_version()
    print(f"[python] {msg_py}")

    ok_pkgs, missing_pkgs = check_packages()
    if ok_pkgs:
        print("[deps] All required Python packages are importable.")
    else:
        print("[deps] Missing packages:")
        for name in missing_pkgs:
            print(f"  - {name}")

    ok_env, missing_env = check_env_vars()
    if ok_env:
        print("[env ] All required environment variables are set.")
    else:
        print("[env ] Missing or empty variables:")
        for name in missing_env:
            print(f"  - {name}")

    missing_optional = check_optional_env_vars()
    if missing_optional:
        print("[env ] Optional provider variables not set (these can be added later):")
        for name in missing_optional:
            print(f"  - {name}")

    ok_paths, missing_paths = check_paths()
    if ok_paths:
        print("[fs  ] All expected folders and key files are present.")
    else:
        print("[fs  ] Missing paths:")
        for desc in missing_paths:
            print(f"  - {desc}")

    ok_claude, msg_claude = test_claude_hello_world()
    print(f"[llm ] {msg_claude}")

    ok_gemini, msg_gemini = test_gemini_hello_world()
    print(f"[llm ] {msg_gemini}")

    # LLM smoke tests are informative; they should not block starting work.
    all_ok = ok_py and ok_pkgs and ok_env and ok_paths
    print("\nSummary:")
    if all_ok:
        print("Environment looks good enough. You can start implementing modules with Cursor.")
        sys.exit(0)
    else:
        print("Some checks failed. Fix the required items above and re-run verify_setup.py.")
        sys.exit(1)


if __name__ == "__main__":
    main()

