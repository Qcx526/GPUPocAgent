#!/usr/bin/env python
"""
M2 Real Cross-Process Resume Test - Process 2

Actual OS-level process (NEW):
1. Loads metadata from Process 1
2. Creates NEW GPUResearchAgent
3. Resumes from same thread_id
4. Completes execution
5. Verifies no duplicate compilation
6. Records results
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
    print("M2 REAL CROSS-PROCESS TEST - PROCESS 2")
    print("=" * 70)

    # Record actual OS PID
    pid = os.getpid()
    print(f"\nActual OS Process ID: {pid}")

    # Load Process 1 metadata
    metadata_path = Path("process1_metadata.json")
    if not metadata_path.exists():
        print(f"\nERROR: {metadata_path} not found")
        print("Run real_process1_p1.py first")
        return 1

    p1_metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    print(f"\nLoaded Process 1 metadata:")
    print(f"  Process 1 PID: {p1_metadata['os_pid']}")
    print(f"  Task ID: {p1_metadata['task_id']}")
    print(f"  Status: {p1_metadata['status']}")
    print(f"  Tools called: {p1_metadata['tool_calls']}")

    # Verify different OS PID
    if pid == p1_metadata['os_pid']:
        print(f"\nERROR: Same OS PID ({pid}) - not a separate process")
        return 1

    print(f"\n[OK] Different OS PID: P1={p1_metadata['os_pid']}, P2={pid}")

    # Verify checkpoint exists
    checkpoint_db = Path(p1_metadata['checkpoint_db'])
    if not checkpoint_db.exists():
        print(f"\nERROR: Checkpoint DB not found: {checkpoint_db}")
        return 1

    print(f"[OK] Checkpoint DB found: {checkpoint_db}")

    # Create NEW agent
    print("\nCreating NEW GPUResearchAgent (simulating fresh process)...")
    settings = get_settings()
    llm = create_llm_client(settings)

    agent = create_gpu_research_agent(
        settings=settings,
        llm=llm,
        checkpoint_db=str(checkpoint_db)
    )

    try:
        # Load checkpoint state
        print(f"\nLoading checkpoint for thread: {p1_metadata['thread_id']}")
        state_before = agent.get_task_state(p1_metadata['thread_id'])

        if 'error' in state_before:
            print(f"\nERROR loading state: {state_before['error']}")
            return 1

        messages_before = state_before.get('values', {}).get('messages', [])
        print(f"Messages in checkpoint: {len(messages_before)}")

        # Resume task
        print("\nResuming task to complete execution...")
        resume_instruction = """
Continue from checkpoint.
Now execute the compiled CUDA program.
Verify the execution results.
"""

        result = agent.resume_task(
            thread_id=p1_metadata['thread_id'],
            additional_instruction=resume_instruction
        )

        # Get final state
        print("\nGetting final state...")
        state_after = agent.get_task_state(p1_metadata['thread_id'])
        messages_after = state_after.get('values', {}).get('messages', [])

        print(f"Messages after resume: {len(messages_after)}")

        # Collect tool calls
        new_tool_calls = []
        for msg in messages_after[len(messages_before):]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    new_tool_calls.append(tc.get('name'))

        print(f"\nTools called in Process 2: {new_tool_calls}")

        # Verification
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        issues = []

        # Check: execute_cuda_program was called
        if 'execute_cuda_program' not in new_tool_calls:
            issues.append("execute_cuda_program was NOT called in Process 2")
        else:
            print("[OK] execute_cuda_program was called in Process 2")

        # Check: compile_cuda_code NOT called again
        p1_tools = p1_metadata['tool_calls']
        if 'compile_cuda_code' in p1_tools:
            if 'compile_cuda_code' in new_tool_calls:
                issues.append("compile_cuda_code was called AGAIN (duplicate)")
            else:
                print("[OK] compile_cuda_code was NOT called again (no duplication)")

        # Check: detect not called again
        if 'detect_cuda_environment' in p1_tools:
            if 'detect_cuda_environment' in new_tool_calls:
                issues.append("detect_cuda_environment was called again")
            else:
                print("[OK] detect_cuda_environment was NOT called again")

        # Check: binary integrity
        if p1_metadata['binaries']:
            binary = p1_metadata['binaries'][0]
            binary_path = Path(binary['path'])

            if binary_path.exists():
                current_sha256 = compute_sha256(binary_path)
                if current_sha256 == binary['sha256']:
                    print(f"[OK] Binary integrity verified (SHA256 match)")
                else:
                    issues.append(f"Binary SHA256 mismatch: {binary['sha256']} vs {current_sha256}")
            else:
                issues.append(f"Binary file not found: {binary_path}")

        # Final result
        print("\n" + "=" * 70)
        if issues:
            print("RESULT: M2 CROSS-PROCESS TEST FAILED")
            print("\nIssues:")
            for issue in issues:
                print(f"  - {issue}")
            print("=" * 70)
            return 1
        else:
            print("RESULT: M2 CROSS-PROCESS RESUME TEST PASSED")
            print("=" * 70)
            print("[OK] Task completed execution after resume")
            print("[OK] No duplicate compilation")
            print("[OK] Binary integrity preserved")
            print("[OK] Two independent OS processes verified")
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
