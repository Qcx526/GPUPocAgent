#!/usr/bin/env python
"""
M2 Real Mid-Task Interruption and Resume Test - Process 1

This process:
1. Starts a CUDA research task
2. Completes detection and code generation
3. Completes compilation
4. STOPS BEFORE execution (controlled interruption)
5. Saves checkpoint to disk
6. Records what was completed
7. Exits completely
"""

import sys
from pathlib import Path
import json
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.gpu_research_agent import create_gpu_research_agent


def main():
    print("=" * 60)
    print("M2 Mid-Task Interruption - PROCESS 1")
    print("=" * 60)

    # Setup
    settings = get_settings()
    llm = create_llm_client(settings)

    task_id = f"interrupt_test_{uuid.uuid4().hex[:8]}"
    thread_id = task_id

    print(f"\nTask ID: {task_id}")
    print(f"Thread ID: {thread_id}")

    checkpoint_db = "interrupt_resume_checkpoints.db"
    print(f"Checkpoint DB: {checkpoint_db}")

    # Create agent
    agent = create_gpu_research_agent(
        settings=settings,
        llm=llm,
        checkpoint_db=checkpoint_db
    )

    # Task: Will be interrupted after compilation
    task_description = """
Your task is to conduct a CUDA vector addition experiment:

1. Detect the CUDA environment
2. Generate a simple CUDA vector addition program
3. Compile the program
4. Execute the compiled program
5. Verify the results

Start working on this step by step.
"""

    print("\n" + "=" * 60)
    print("Starting task (will interrupt before execution)...")
    print("=" * 60)

    try:
        # Start task
        result = agent.start_research_task(
            task_id=task_id,
            task_description=task_description,
            thread_id=thread_id
        )

        print("\nTask started")

        # Get current state
        state = agent.get_task_state(thread_id)

        print(f"\nCurrent state:")
        print(f"  Thread ID: {state['thread_id']}")
        print(f"  Messages: {len(state.get('values', {}).get('messages', []))}")

        # Extract what was completed
        messages = state.get('values', {}).get('messages', [])

        tools_called = []
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tools_called.append(tc.get('name'))

        print(f"\nTools called so far: {len(tools_called)}")
        for tool in set(tools_called):
            print(f"  - {tool}: {tools_called.count(tool)}x")

        # Check for generated artifacts
        artifacts = []
        for msg in messages:
            if hasattr(msg, 'content'):
                content = str(msg.content)
                # Look for file paths
                if '.cu' in content:
                    # Extract potential file paths
                    for line in content.split('\n'):
                        if '.cu' in line and ('data/' in line or 'cuda_' in line):
                            artifacts.append(line.strip())

        # Save metadata
        metadata = {
            "process": 1,
            "task_id": task_id,
            "thread_id": thread_id,
            "checkpoint_db": checkpoint_db,
            "tools_called": tools_called,
            "total_messages": len(messages),
            "status": "INTERRUPTED_BEFORE_EXECUTION",
            "next_step": "execute_cuda_program"
        }

        metadata_file = Path("interrupt_process1_metadata.json")
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

        print(f"\nMetadata saved to: {metadata_file}")
        print(f"Checkpoint DB exists: {Path(checkpoint_db).exists()}")
        if Path(checkpoint_db).exists():
            print(f"Checkpoint DB size: {Path(checkpoint_db).stat().st_size} bytes")

        print("\n" + "=" * 60)
        print("PROCESS 1 COMPLETE")
        print("=" * 60)
        print(f"Task interrupted at: {metadata['status']}")
        print(f"Next step should be: {metadata['next_step']}")
        print("Now run process 2 to resume and complete execution")

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
