#!/usr/bin/env python
"""
M2 Real Mid-Task Interruption and Resume Test - Process 2

This process:
1. Starts as NEW Python process
2. Loads checkpoint from Process 1
3. Creates NEW agent instance
4. Resumes from where Process 1 stopped
5. Completes execution and verification
6. Verifies no duplicate operations
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.gpu_research_agent import create_gpu_research_agent


def main():
    print("=" * 60)
    print("M2 Mid-Task Resume - PROCESS 2")
    print("=" * 60)

    # Load Process 1 metadata
    metadata_file = Path("interrupt_process1_metadata.json")
    if not metadata_file.exists():
        print("\nERROR: interrupt_process1_metadata.json not found")
        print("Run interrupt_process1.py first")
        return 1

    metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
    print(f"\nLoaded metadata from Process 1:")
    print(f"  Task ID: {metadata['task_id']}")
    print(f"  Thread ID: {metadata['thread_id']}")
    print(f"  Status: {metadata['status']}")
    print(f"  Tools called: {len(metadata['tools_called'])}")
    print(f"  Next step: {metadata['next_step']}")

    # Verify checkpoint DB
    checkpoint_db = Path(metadata['checkpoint_db'])
    if not checkpoint_db.exists():
        print(f"\nERROR: Checkpoint DB not found: {checkpoint_db}")
        return 1

    print(f"\nCheckpoint DB found: {checkpoint_db}")
    print(f"  Size: {checkpoint_db.stat().st_size} bytes")

    # Setup NEW agent (simulating process restart)
    print("\n" + "=" * 60)
    print("Creating NEW agent instance (simulating restart)...")
    print("=" * 60)

    settings = get_settings()
    llm = create_llm_client(settings)

    agent = create_gpu_research_agent(
        settings=settings,
        llm=llm,
        checkpoint_db=str(checkpoint_db)
    )

    try:
        # Load state
        print(f"\nLoading state for thread: {metadata['thread_id']}")
        state = agent.get_task_state(metadata['thread_id'])

        if 'error' in state:
            print(f"\nERROR: {state['error']}")
            return 1

        print(f"\nState loaded successfully:")
        print(f"  Thread ID: {state['thread_id']}")

        messages_before = state.get('values', {}).get('messages', [])
        print(f"  Messages from Process 1: {len(messages_before)}")

        # Resume task
        print("\n" + "=" * 60)
        print("Resuming task to complete execution...")
        print("=" * 60)

        resume_instruction = """
Continue from where you left off.
The compilation should be complete.
Now execute the compiled CUDA program and verify the results.
"""

        result = agent.resume_task(
            thread_id=metadata['thread_id'],
            additional_instruction=resume_instruction
        )

        print("\nTask resumed and continued")

        # Get final state
        final_state = agent.get_task_state(metadata['thread_id'])
        messages_after = final_state.get('values', {}).get('messages', [])

        print(f"\nFinal state:")
        print(f"  Total messages: {len(messages_after)}")
        print(f"  New messages: {len(messages_after) - len(messages_before)}")

        # Check for execution
        tools_called_after = []
        for msg in messages_after[len(messages_before):]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tools_called_after.append(tc.get('name'))

        print(f"\nTools called in Process 2: {len(tools_called_after)}")
        for tool in set(tools_called_after):
            print(f"  - {tool}: {tools_called_after.count(tool)}x")

        # Verification
        print("\n" + "=" * 60)
        print("Verifying resume correctness...")
        print("=" * 60)

        issues = []

        # Check if execution tool was called
        if 'execute_cuda_program' not in tools_called_after:
            issues.append("execute_cuda_program was not called in Process 2")

        # Check for duplicate compilation
        process1_tools = metadata['tools_called']
        if 'compile_cuda_code' in process1_tools and 'compile_cuda_code' in tools_called_after:
            issues.append("WARNING: compile_cuda_code called again (possible duplicate)")

        # Check for duplicate detection
        if 'detect_cuda_environment' in process1_tools and 'detect_cuda_environment' in tools_called_after:
            issues.append("WARNING: detect_cuda_environment called again (possible duplicate)")

        if issues:
            print("\nIssues found:")
            for issue in issues:
                print(f"  - {issue}")
            print("\n" + "=" * 60)
            print("RESULT: M2 RESUME TEST HAD ISSUES")
            print("=" * 60)
            return 1
        else:
            print("\nNo issues found:")
            print("  - Execution tool called in Process 2")
            print("  - No duplicate operations detected")

            print("\n" + "=" * 60)
            print("RESULT: M2 MID-TASK RESUME TEST PASSED")
            print("=" * 60)
            print("Task successfully resumed and completed across process boundary")
            return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return 1
    finally:
        agent.close()


if __name__ == "__main__":
    sys.exit(main())
