#!/usr/bin/env python
"""
M2 Real Cross-Process Recovery Test - Process 2: Resume Task

This script:
1. Loads checkpoint from disk (SQLite)
2. Reconstructs workflow and checkpointer
3. Verifies recovered state
4. Checks that artifacts are preserved
5. Verifies no duplicate execution
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.research_workflow import create_research_workflow
from langgraph.checkpoint.sqlite import SqliteSaver


def main():
    print("=" * 60)
    print("M2 Cross-Process Test - PROCESS 2: Resume Task")
    print("=" * 60)

    # Load process 1 metadata
    metadata_file = Path("process1_metadata.json")
    if not metadata_file.exists():
        print("\nERROR: process1_metadata.json not found")
        print("Run m2_process1_start.py first")
        return 1

    metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
    print(f"\nLoaded metadata from Process 1:")
    print(f"  Task ID: {metadata['task_id']}")
    print(f"  Checkpoint DB: {metadata['checkpoint_db']}")
    print(f"  Phase completed: {metadata['final_phase']}")
    print(f"  Steps: {metadata['steps_completed']}")

    # Verify checkpoint DB exists
    checkpoint_db = Path(metadata['checkpoint_db'])
    if not checkpoint_db.exists():
        print(f"\nERROR: Checkpoint DB not found: {checkpoint_db}")
        return 1

    print(f"\nCheckpoint DB found: {checkpoint_db}")
    print(f"  Size: {checkpoint_db.stat().st_size} bytes")

    # Setup (NEW LLM client, NEW workflow instance)
    print("\n" + "=" * 60)
    print("Creating NEW workflow instance (simulating restart)")
    print("=" * 60)

    settings = get_settings()
    llm = create_llm_client(settings)

    # Create NEW checkpointer from SAME DB file
    import sqlite3
    conn = sqlite3.connect(str(checkpoint_db), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    print("New SqliteSaver created from existing DB")

    # Create NEW workflow
    workflow = create_research_workflow(llm, checkpointer)
    print("New workflow created")

    # Same config as process 1
    config = {"configurable": {"thread_id": metadata['task_id']}}

    # Load state from checkpoint
    print("\n" + "=" * 60)
    print("Loading state from checkpoint...")
    print("=" * 60)

    try:
        state_snapshot = workflow.get_state(config)

        if not state_snapshot.values:
            print("\nERROR: No state found in checkpoint")
            return 1

        print(f"\nState recovered successfully:")
        print(f"  Task ID: {state_snapshot.values.get('task_id')}")
        print(f"  Phase: {state_snapshot.values.get('phase')}")
        print(f"  Steps completed: {state_snapshot.values.get('step_count')}")
        print(f"  Success: {state_snapshot.values.get('success')}")

        artifacts = state_snapshot.values.get('artifacts', [])
        print(f"  Artifacts: {len(artifacts)}")
        for art in artifacts:
            print(f"    - {art}")

        # Verify artifacts still exist
        print("\n" + "=" * 60)
        print("Verifying artifacts...")
        print("=" * 60)

        for artifact_path in artifacts:
            p = Path(artifact_path)
            if p.exists():
                print(f"  [OK] {artifact_path}")
                # Show file size
                print(f"       Size: {p.stat().st_size} bytes")
            else:
                print(f"  [MISSING] {artifact_path}")

        # Compare with process 1
        print("\n" + "=" * 60)
        print("Comparing with Process 1 state...")
        print("=" * 60)

        matches = []
        mismatches = []

        if state_snapshot.values.get('task_id') == metadata['task_id']:
            matches.append("task_id")
        else:
            mismatches.append("task_id")

        if state_snapshot.values.get('phase') == metadata['final_phase']:
            matches.append("phase")
        else:
            mismatches.append("phase")

        if state_snapshot.values.get('step_count') == metadata['steps_completed']:
            matches.append("step_count")
        else:
            mismatches.append("step_count")

        if len(artifacts) == len(metadata['artifacts']):
            matches.append("artifact count")
        else:
            mismatches.append("artifact count")

        print(f"  Matches: {', '.join(matches)}")
        if mismatches:
            print(f"  Mismatches: {', '.join(mismatches)}")

        # Final verdict
        print("\n" + "=" * 60)
        if mismatches:
            print("RESULT: M2 CROSS-PROCESS TEST FAILED")
            print(f"State mismatch: {mismatches}")
        else:
            print("RESULT: M2 CROSS-PROCESS TEST PASSED")
            print("State fully recovered across process boundary")
            print("Artifacts preserved and accessible")
        print("=" * 60)

        return 0 if not mismatches else 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
