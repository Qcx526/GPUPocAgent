"""Test simple agent creation and structure"""

import pytest
from unittest.mock import Mock, MagicMock

from src.agent.simple_agent import (
    create_simple_agent,
    save_experiment_results,
)
from src.config import Settings


def test_create_simple_agent():
    """Test that agent can be created with proper configuration"""
    mock_llm = Mock()
    settings = Settings(llm_api_key="test_key")

    agent = create_simple_agent(mock_llm, settings, verbose=False)

    assert agent is not None
    assert hasattr(agent, 'invoke')


def test_save_experiment_results(tmp_path):
    """Test saving experiment results"""
    task = "Test CUDA environment"
    results = {
        "output": "Environment detected successfully",
        "intermediate_steps": [
            (
                MagicMock(tool="detect_cuda_environment", tool_input={}),
                "CUDA 13.4 detected"
            )
        ]
    }

    output_path = save_experiment_results(task, results, tmp_path)

    assert output_path.exists()
    assert output_path.suffix == ".json"

    import json
    data = json.loads(output_path.read_text())

    assert data["task"] == task
    assert data["output"] == results["output"]
    assert len(data["intermediate_steps"]) == 1


@pytest.mark.skip(reason="Requires real API key and LLM - integration test")
def test_run_simple_experiment_integration():
    """Integration test with real LLM (skip by default)"""
    from src.config import get_settings
    from src.llm.client import create_llm_client
    from src.agent.simple_agent import run_simple_experiment

    settings = get_settings()
    llm = create_llm_client(settings)

    task = "Detect CUDA environment"

    results = run_simple_experiment(task, llm, settings, verbose=True)

    assert "output" in results
    assert "intermediate_steps" in results
    assert "results_saved_to" in results
