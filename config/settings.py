from __future__ import annotations

"""
Hybrid AI Agent – configuration loader (settings.py).

Responsibilities:
- Load configuration from environment variables (optionally via .env)
- Provide a typed Settings object the rest of the agent can import
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import os

from dotenv import load_dotenv


@dataclass
class ModelSettings:
    # Vision model configuration
    vision_provider: str  # "gemini" or "nova"
    
    # Gemini settings
    gemini_api_key: Optional[str]
    gemini_vision_model: str
    
    # Nova (Bedrock) settings
    nova_region: str
    nova_model_id: str
    
    # Other models (legacy)
    anthropic_api_key: Optional[str]
    anthropic_task_model: str
    anthropic_execution_model: str
    qwen_endpoint: Optional[str]
    qwen_api_key: Optional[str]
    qwen_model: str


@dataclass
class PathSettings:
    root_dir: Path
    trajectory_db_path: Path
    action_log_db_path: Path
    template_dir: Path
    agent_trash_dir: Path
    agent_backup_dir: Path
    agent_reg_backup_dir: Path


@dataclass
class RuntimeSettings:
    environment: str
    log_level: str
    action_timeout_seconds: int
    max_steps_per_run: int
    max_seconds_per_run: int
    max_llm_tokens_per_run: int
    sandbox_mode: bool
    enable_latency_debug: bool
    enable_trajectory_debug: bool


@dataclass
class Settings:
    models: ModelSettings
    paths: PathSettings
    runtime: RuntimeSettings


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_settings(dotenv: bool = True) -> Settings:
    """
    Load Settings from the current process environment.
    If dotenv=True, a .env file in the project root is loaded first.
    """
    if dotenv:
        # Load .env from the project root (one level above this file)
        root = Path(__file__).resolve().parent.parent
        env_file = root / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    root_dir = Path(os.getenv("HYBRID_AGENT_ROOT", Path(__file__).resolve().parent.parent))

    models = ModelSettings(
        # Vision model provider selection
        vision_provider=os.getenv("VISION_PROVIDER", "gemini").lower(),
        
        # Gemini configuration (model name only defaulted here)
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_vision_model=os.getenv("GEMINI_VISION_MODEL", "gemini-3-flash-preview"),
        
        # Nova (Bedrock) configuration (region and model ID only defaulted here)
        nova_region=os.getenv("NOVA_REGION", "us-east-1"),
        nova_model_id=os.getenv("NOVA_MODEL_ID", "us.amazon.nova-lite-v1:0"),
        
        # Other models (legacy)
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_task_model=os.getenv("ANTHROPIC_TASK_MODEL", "claude-3-5-sonnet-20241022"),
        anthropic_execution_model=os.getenv("ANTHROPIC_EXECUTION_MODEL", "claude-3-haiku-20240307"),
        qwen_endpoint=os.getenv("QWEN_VL_ENDPOINT"),
        qwen_api_key=os.getenv("QWEN_VL_API_KEY"),
        qwen_model=os.getenv("QWEN_VL_MODEL", "qwen2-vl-72b-instruct"),
    )

    paths = PathSettings(
        root_dir=root_dir,
        trajectory_db_path=Path(os.getenv("TRAJECTORY_DB_PATH", root_dir / "storage" / "trajectory.db")),
        action_log_db_path=Path(os.getenv("ACTION_LOG_DB_PATH", root_dir / "storage" / "actions.db")),
        template_dir=Path(os.getenv("TEMPLATE_DIR", root_dir / "templates")),
        agent_trash_dir=Path(os.getenv("AGENT_TRASH_DIR", "C:/.agent_trash")),
        agent_backup_dir=Path(os.getenv("AGENT_BACKUP_DIR", "C:/.agent_backups")),
        agent_reg_backup_dir=Path(os.getenv("AGENT_REG_BACKUP_DIR", "C:/.agent_reg_backups")),
    )

    runtime = RuntimeSettings(
        environment=os.getenv("AGENT_ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        action_timeout_seconds=_get_int("ACTION_TIMEOUT_SECONDS", 60),
        max_steps_per_run=_get_int("MAX_STEPS_PER_RUN", 200),
        max_seconds_per_run=_get_int("MAX_SECONDS_PER_RUN", 1800),
        max_llm_tokens_per_run=_get_int("MAX_LLM_TOKENS_PER_RUN", 200000),
        sandbox_mode=_get_bool("SANDBOX_MODE", True),
        enable_latency_debug=_get_bool("ENABLE_LATENCY_DEBUG", False),
        enable_trajectory_debug=_get_bool("ENABLE_TRAJECTORY_DEBUG", False),
    )

    return Settings(models=models, paths=paths, runtime=runtime)


# Convenience singleton-style accessor if modules want to import settings directly.
_CACHED_SETTINGS: Optional[Settings] = None


def get_settings() -> Settings:
    global _CACHED_SETTINGS
    if _CACHED_SETTINGS is None:
        _CACHED_SETTINGS = load_settings()
    return _CACHED_SETTINGS

