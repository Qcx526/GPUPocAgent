"""Test configuration loading"""

import os
import pytest
from src.config import Settings


def test_settings_from_env(monkeypatch):
    """Test that settings load from environment variables"""
    monkeypatch.setenv("LLM_API_KEY", "test_key_12345")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    settings = Settings()

    assert settings.llm_api_key == "test_key_12345"
    assert settings.llm_model == "test-model"
    assert settings.llm_base_url  # Should have default


def test_settings_validation_fails_without_key(monkeypatch):
    """Test that validation fails without API key"""
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ValueError, match="LLM_API_KEY not configured"):
        settings = Settings(llm_api_key="your_api_key_here")
        settings.validate_api_key()


def test_project_paths():
    """Test that project paths are correctly constructed"""
    settings = Settings(llm_api_key="test_key")

    assert settings.project_root.exists()
    assert settings.data_dir.name == "data"
    assert settings.research_tasks_dir.name == "research_tasks"
