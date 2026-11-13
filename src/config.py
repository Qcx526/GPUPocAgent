"""
Project-wide path and configuration management.
All paths must be absolute and resolved from project root.
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class WorkspaceConfig(BaseSettings):
    """Unified workspace and path configuration."""

    # API Configuration
    llm_api_key: str
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-flash"
    tavily_api_key: Optional[str] = None

    # Execution settings
    execution_timeout: int = 300
    max_retry_attempts: int = 3
    debug: bool = False

    # Paths (derived from project root)
    # src/config.py -> src (parent) -> GPUPocAgent (parent.parent)
    project_root: Path = Path(__file__).parent.parent
    workspace_root: Optional[Path] = None

    @field_validator("workspace_root", mode="before")
    @classmethod
    def set_workspace_root(cls, v):
        if v is None:
            return Path(__file__).parent.parent / "workspace"
        return Path(v)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_run_directory(self, task_id: str, run_id: str) -> Path:
        """Get absolute path for a specific run."""
        run_dir = self.workspace_root / "runs" / task_id / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def get_state_directory(self) -> Path:
        """Get absolute path for state storage."""
        state_dir = self.workspace_root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    def get_checkpoint_db_path(self) -> Path:
        """Get absolute path for checkpoint database."""
        return self.get_state_directory() / "checkpoints.db"

    def get_artifact_index_path(self) -> Path:
        """Get absolute path for artifact index."""
        return self.get_state_directory() / "artifacts.db"


# Singleton instance
_config: Optional[WorkspaceConfig] = None


def get_config() -> WorkspaceConfig:
    """Load or retrieve cached configuration."""
    global _config
    if _config is None:
        _config = WorkspaceConfig()
    return _config


def reset_config():
    """Reset cached configuration (mainly for testing)."""
    global _config
    _config = None


# Convenience exports
def project_root() -> Path:
    return get_config().project_root


def workspace_root() -> Path:
    return get_config().workspace_root


def run_directory(task_id: str, run_id: str) -> Path:
    return get_config().get_run_directory(task_id, run_id)


def checkpoint_db_path() -> Path:
    return get_config().get_checkpoint_db_path()


def artifact_index_path() -> Path:
    return get_config().get_artifact_index_path()


def generate_run_id() -> str:
    """Generate a deterministic but unique run ID for a research task.

    Returns:
        A 12-character hex string (first 12 chars of UUID4).
    """
    return str(uuid.uuid4())[:12]


# Backward compatibility aliases
Settings = WorkspaceConfig  # Old name → new name
get_settings = get_config   # Old function → new function
