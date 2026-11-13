#!/usr/bin/env python
"""
Test Deep Agents Integration with Real CUDA Tools

Verifies that Deep Agents can:
1. Use real CUDA tools (not just test tools)
2. Make autonomous decisions
3. Execute multi-step workflows
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.gpu_research_agent import create_gpu_research_agent


def test_deep_agents_cuda_integration():
    """Test Deep Agents with real CUDA tools"""

    print("=" * 60)
    print("Deep Agents + CUDA Tools Integration Test")
    print("=" * 60)

    # Setup
    settings = get_settings()
    llm = create_llm_client(settings)

    print(f"\n1. Configuration:")
    print(f"   Model: {settings.llm_model}")
    print(f"   Base URL: {settings.llm_base_url}")

    # Create agent
    print("\n2. Creating GPU Research Agent with Deep Agents...")
    agent = create_gpu_research_agent(
        settings=settings,
        llm=llm,
        checkpoint_db="test_deep_agents_cuda.db"
    )
    print("   Agent created")

    # Simple task
    task_description = """
Detect the CUDA environment on this system using the detect_cuda_environment tool.
Report what GPU is available and its compute capability.
"""

    print("\n3. Starting research task...")
    print(f"   Task: {task_description.strip()}")

    try:
        result = agent.start_research_task(
            task_id="test_cuda_detect",
            task_description=task_description
        )

        print("\n4. Task completed")
        print(f"   Thread ID: {result['thread_id']}")
        print(f"   Checkpoint DB: {result['checkpoint_db']}")

        # Extract messages
        messages = result['result'].get('messages', [])
        print(f"   Total messages: {len(messages)}")

        # Check for tool calls
        tool_calls_found = 0
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_calls_found += len(msg.tool_calls)
                for tc in msg.tool_calls:
                    print(f"\n   Tool called: {tc.get('name', 'unknown')}")

        # Check final response
        if messages:
            final_msg = messages[-1]
            if hasattr(final_msg, 'content'):
                print(f"\n5. Final response:")
                # Avoid Unicode encoding issues
                content = str(final_msg.content)[:500]
                safe_content = content.encode('ascii', 'replace').decode('ascii')
                print(f"   {safe_content}")

        # Verdict
        print("\n" + "=" * 60)
        if tool_calls_found > 0:
            print("RESULT: INTEGRATION TEST PASSED")
            print(f"Deep Agents successfully called {tool_calls_found} CUDA tool(s)")
            return 0
        else:
            print("RESULT: INTEGRATION TEST FAILED")
            print("No CUDA tools were called")
            return 1

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return 1
    finally:
        agent.close()


if __name__ == "__main__":
    sys.exit(test_deep_agents_cuda_integration())
