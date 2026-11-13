"""LLM client for GPUVulnAgent using LangChain"""

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from src.config import Settings


def create_llm_client(settings: Optional[Settings] = None) -> BaseChatModel:
    """
    Create LLM client configured for Qwen API gateway with DeepSeek model.

    Args:
        settings: Application settings (defaults to global settings)

    Returns:
        Configured ChatOpenAI instance

    Raises:
        ValueError: If API key is not configured
    """
    if settings is None:
        from src.config import get_settings
        settings = get_settings()

    # Validate API key
    settings.validate_api_key()

    # Create ChatOpenAI with custom base URL
    client = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        # Enable streaming for better responsiveness
        streaming=True,
    )

    return client


def verify_llm_connection(client: BaseChatModel) -> tuple[bool, str]:
    """
    Verify basic LLM connectivity.

    Args:
        client: LLM client to test

    Returns:
        (success, message) tuple
    """
    try:
        response = client.invoke("Hello! Please respond with just 'OK'.")
        return True, f"Connection successful. Response: {response.content[:100]}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"
