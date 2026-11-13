"""Test LLM Tool Calling capabilities"""

import pytest
from unittest.mock import Mock
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


@tool
def get_gpu_info(query: str) -> str:
    """Get GPU information based on query.

    Args:
        query: What GPU information to retrieve

    Returns:
        GPU information string
    """
    return f"GPU info for: {query}"


@tool
def compile_cuda_code(source_code: str, output_name: str = "output") -> dict:
    """Compile CUDA source code.

    Args:
        source_code: CUDA C/C++ source code
        output_name: Name for output executable

    Returns:
        Compilation result with success status and output
    """
    return {
        "success": True,
        "output": output_name,
        "message": "Compilation successful (mock)"
    }


def test_tool_definition():
    """Test that tools are properly defined"""
    assert get_gpu_info.name == "get_gpu_info"
    assert compile_cuda_code.name == "compile_cuda_code"

    # Test tool invocation
    result = get_gpu_info.invoke({"query": "GTX 1660"})
    assert "GTX 1660" in result


@pytest.mark.skip(reason="Requires real API key - run manually")
def test_llm_tool_calling_real():
    """Test real LLM tool calling with Qwen API"""
    from src.llm.client import create_llm_client
    from src.config import get_settings

    settings = get_settings()
    client = create_llm_client(settings)

    # Bind tools to LLM
    llm_with_tools = client.bind_tools([get_gpu_info, compile_cuda_code])

    # Test tool calling
    response = llm_with_tools.invoke([
        HumanMessage(content="What GPU information can you get about NVIDIA GTX 1660?")
    ])

    print(f"\nLLM Response: {response}")
    print(f"Response type: {type(response)}")

    # Check if tool was called
    if hasattr(response, 'tool_calls'):
        print(f"Tool calls: {response.tool_calls}")
        assert len(response.tool_calls) > 0, "Expected tool calls but got none"
    else:
        print("Warning: Response has no tool_calls attribute")
        print(f"Response content: {response.content}")


def test_mock_tool_calling_workflow():
    """Test tool calling workflow with mocked LLM"""
    # This tests the structure without requiring API access

    tools = [get_gpu_info, compile_cuda_code]

    # Simulate tool selection by LLM
    selected_tool = tools[0]
    tool_input = {"query": "GTX 1660 compute capability"}

    # Execute tool
    result = selected_tool.invoke(tool_input)

    assert "GTX 1660" in result
    assert "compute capability" in result


if __name__ == "__main__":
    # Run manual test
    import sys
    sys.path.insert(0, ".")

    print("Testing tool calling with real API...")
    test_llm_tool_calling_real()
