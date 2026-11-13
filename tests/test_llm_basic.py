"""Basic LLM connectivity tests"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage

from src.llm.client import create_llm_client, verify_llm_connection
from src.config import Settings


def test_create_llm_client_with_settings():
    """Test LLM client creation with custom settings"""
    settings = Settings(llm_api_key="test_key_123")

    client = create_llm_client(settings)

    assert client is not None
    assert client.model_name == settings.llm_model


def test_llm_connection_mock():
    """Test LLM connection with mocked response"""
    mock_client = Mock()
    mock_client.invoke.return_value = AIMessage(content="OK")

    success, message = verify_llm_connection(mock_client)

    assert success is True
    assert "successful" in message.lower()
    mock_client.invoke.assert_called_once()


@pytest.mark.skip(reason="Requires real API key - run manually")
def test_real_llm_connection():
    """Test real LLM connection - requires .env configuration"""
    from src.config import get_settings

    settings = get_settings()
    client = create_llm_client(settings)

    success, message = verify_llm_connection(client)

    print(f"\nConnection test: {message}")
    assert success is True
