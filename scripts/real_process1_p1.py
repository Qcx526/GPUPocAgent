#!/usr/bin/env python
"""
M2 Real Cross-Process Resume Test - Process 1

Actual OS-level process:
1. Creates GPUResearchAgent
2. Starts real CUDA research task
3. Completes compilation
4. Records binary SHA256
5. Interrupts BEFORE execution
6. Saves checkpoint
7. Exits completely
"""

import sys
import os
from pathlib import Path
import json
import hashlib

# Must be run as independent process
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.gpu_research_agent import create_gpu_research_agent


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def main():
    print("=" * 70)
    print("M2 REAL CROSS-PROCESS TEST - PROCESS 1")
    print("=" * 70)

    # Record actual OS PID
    pid = os.getpid()
    print(f"\nActual OS Process ID: {pid}")

    # Setup
    settings = get_settings()
    llm = create_llm_client(settings)

    task_id = "real_cross_process_p1"
    thread_id = task_id
    checkpoint_db = "cross_process_checkpoints.db"

    print(f"Task ID: {task_id}")
    print(f"Thread ID: {thread_id}")
    print(f"Checkpoint DB: {checkpoint_db}")

    # Create agent
    print("\nCreating GPUResearchAgent...")
    agent = create_gpu_research_agent(
        settings=settings,
        llm=llm,
        checkpoint_db=checkpoint_db
    )

    # Task: Generate, compile, then interrupt BEFORE execution
    task_description = """
Conduct a CUDA vector addition experiment:
1. Detect CUDA environment
2. Generate vector addition source code
3. Compile to binary
4. STOP - do not execute yet

Only reach steps 1-3. Do not proceed to execution.
"""

    print("\nStarting research task...")
    print("(This should reach compilation but stop before execution)")

    try:
        result = agent.start_research_task(
            task_id=task_id,
            task_description=task_description,
            thread_id=thread_id
        )

        # Get state
        state = agent.get_task_state(thread_id)

        if 'error' in state:
            print(f"\nERROR loading state: {state['error']}")
            return 1

        messages = state.get('values', {}).get('messages', [])
        print(f"\nTask state retrieved. Messages: {len(messages)}")

        # Collect tool calls
        tool_calls = []
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(tc.get('name'))

        print(f"Tools called: {tool_calls}")

        # Check if compilation happened
        if 'compile_cuda_code' not in tool_calls:
            print("\nERROR: compile_cuda_code was not called")
            return 1

        print("[OK] Compilation was attempted")

        # Look for compiled binary
        binaries = []
        for msg in messages:
            if hasattr(msg, 'content'):
                content = str(msg.content).lower()
                if '.exe' in content or 'compilation successful' in content:
                    # Try to find actual binary file
                    pass

        # Search for actual binary files
        data_dir = Path("data/generated_code")
        if data_dir.exists():
            exes = list(data_dir.glob("*.exe"))
            if exes:
                binary_path = exes[-1]  # Get latest
                print(f"\nBinary found: {binary_path}")
                print(f"Binary size: {binary_path.stat().st_size} bytes")

                binary_sha256 = compute_sha256(binary_path)
                print(f"Binary SHA256: {binary_sha256}")
                binaries.append({
                    "path": str(binary_path),
                    "sha256": binary_sha256,
                    "size": binary_path.stat().st_size
                })

        # Check if execution was called
        execution_called = 'execute_cuda_program' in tool_calls
        if execution_called:
            print("\n[FAIL] execute_cuda_program WAS called - interrupt did not work")
            return 1

        print("[OK] execute_cuda_program was NOT called")

        # Save metadata
        metadata = {
            "process": 1,
            "os_pid": pid,
            "task_id": task_id,
            "thread_id": thread_id,
            "checkpoint_db": checkpoint_db,
            "tool_calls": tool_calls,
            "total_messages": len(messages),
            "binaries": binaries,
            "status": "INTERRUPTED_BEFORE_EXECUTION"
        }

        metadata_path = Path("process1_metadata.json")
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

        print(f"\nMetadata saved to: {metadata_path}")

        print("\n" + "=" * 70)
        print("PROCESS 1 COMPLETE")
        print("=" * 70)
        print(f"Status: {metadata['status']}")
        print(f"Next: Run process 2 to resume and execute")

        return 0

    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        import traceback
        print(traceback.format_exc())
        return 1
    finally:
        agent.close()


if __name__ == "__main__":
    sys.exit(main())
