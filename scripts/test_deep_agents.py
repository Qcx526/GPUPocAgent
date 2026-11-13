#!/usr/bin/env python
"""
Real Deep Agents Test with Qwen API
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deepagents import create_deep_agent
from langchain_core.tools import tool
from src.config import get_settings
from src.llm.client import create_llm_client


@tool
def test_cuda_detection() -> str:
    """Detect CUDA environment on the system."""
    import shutil
    nvcc_path = shutil.which("nvcc")
    if nvcc_path:
        return f"CUDA found at {nvcc_path}"
    return "CUDA not found"


def main():
    print("=" * 60)
    print("Deep Agents Real Test with Qwen API")
    print("=" * 60)

    # Load config
    settings = get_settings()
    print(f"\n1. Model: {settings.llm_model}")
    print(f"   Base URL: {settings.llm_base_url}")

    # Create LLM client
    llm = create_llm_client(settings)
    print("\n2. LLM client created")

    # Create Deep Agent
    print("\n3. Creating Deep Agent with tools...")

    try:
        agent = create_deep_agent(
            model=llm,
            tools=[test_cuda_detection],
        )
        print("   Deep Agent created successfully")
    except Exception as e:
        print(f"   ERROR creating agent: {e}")
        import traceback
        print(traceback.format_exc())
        return 1

    # Test tool calling
    print("\n4. Testing tool calling...")
    try:
        response = agent.invoke({
            "messages": [("user", "Detect if CUDA is available using the test_cuda_detection tool")]
        })

        print("\n5. Response received:")
        if "messages" in response:
            final_msg = response["messages"][-1]
            print(f"   Type: {type(final_msg).__name__}")
            if hasattr(final_msg, 'content'):
                print(f"   Content: {final_msg.content}")

            # Check for tool calls
            tool_calls_found = False
            for msg in response["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    print(f"\n   Tool calls detected: {len(msg.tool_calls)}")
                    for tc in msg.tool_calls:
                        print(f"     - {tc.get('name', 'unknown')}")
                    tool_calls_found = True

            if not tool_calls_found:
                print("\n   WARNING: No tool calls detected")

        print("\n" + "=" * 60)
        print("Deep Agents Test COMPLETED")
        print("Agent can be instantiated and invoked with Qwen API")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n   ERROR during invocation: {e}")
        import traceback
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
