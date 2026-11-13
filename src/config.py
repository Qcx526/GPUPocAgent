"""Configuration management for GPUVulnAgent"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    llm_api_key: str
    llm_base_url: str = "https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1"
    llm_model: str = "deepseek-v4.1-flash-1017"
    llm_temperature: float = 0.0
    llm_max_tokens: Optional[int] = None

    # Optional APIs
    tavily_api_key: Optional[str] = None

    # Execution Configuration
    execution_timeout: int = 300
    max_retry_attempts: int = 3

    # Project Paths
    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def research_tasks_dir(self) -> Path:
        return self.data_dir / "research_tasks"

    @property
    def poc_artifacts_dir(self) -> Path:
        return self.data_dir / "poc_artifacts"

    @property
    def execution_logs_dir(self) -> Path:
        return self.data_dir / "execution_logs"

    def validate_api_key(self) -> None:
        """Validate that required API keys are configured"""
        if not self.llm_api_key or self.llm_api_key == "your_api_key_here":
            raise ValueError(
                "LLM_API_KEY not configured. Please set it in .env file. "
                "Copy .env.example to .env and add your actual API key."
            )


def load_settings() -> Settings:
    """Load and validate settings"""
    settings = Settings()
    settings.validate_api_key()
    return settings


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
