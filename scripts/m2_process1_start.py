#!/usr/bin/env python
"""
M2 Real Cross-Process Recovery Test - Process 1: Start Task

This script:
1. Creates a research task
2. Executes several steps
3. Saves checkpoint to disk (SQLite)
4. Records completed work
5. Exits WITHOUT completing the task
"""

import sys
import os
from pathlib import Path
import uuid
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.state import create_initial_state
from src.agent.research_workflow import create_research_workflow
from langgraph.checkpoint.sqlite import SqliteSaver


def main():
    print("=" * 60)
    print("M2 Cross-Process Test - PROCESS 1: Start Task")
    print("=" * 60)

    # Setup
    settings = get_settings()
    llm = create_llm_client(settings)

    task_id = f"cross_process_test_{uuid.uuid4().hex[:8]}"
    task_description = "Simple CUDA vector addition for cross-process test"

    print(f"\nTask ID: {task_id}")
    print(f"Task: {task_description}")

    # Create SQLite checkpointer (disk-based)
    checkpoint_db = "cross_process_checkpoints.db"
    print(f"\nCheckpoint DB: {checkpoint_db}")

    # Create connection with thread-safety disabled (needed for LangGraph)
    import sqlite3
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    print("SQLite checkpointer created")

    # Create workflow
    workflow = create_research_workflow(llm, checkpointer)

    # Create initial state
    initial_state = create_initial_state(task_id, task_description)

    # Configuration for thread-based checkpointing
    config = {"configurable": {"thread_id": task_id}}

    print("\n" + "=" * 60)
    print("Executing workflow (will save checkpoints)...")
    print("=" * 60)

    try:
        # Run workflow - it will complete all phases
        result = workflow.invoke(initial_state, config=config)

        print(f"\nWorkflow execution result:")
        print(f"  Phase: {result['phase']}")
        print(f"  Steps: {result['step_count']}")
        print(f"  Success: {result.get('success', False)}")

        # Get final checkpoint state
        state_snapshot = workflow.get_state(config)

        print(f"\nCheckpoint saved:")
        print(f"  Values count: {len(state_snapshot.values)}")
        print(f"  Phase: {state_snapshot.values.get('phase')}")
        print(f"  Artifacts: {len(state_snapshot.values.get('artifacts', []))}")

        # Save process 1 metadata
        metadata = {
            "process": 1,
            "task_id": task_id,
            "checkpoint_db": checkpoint_db,
            "final_phase": result['phase'],
            "steps_completed": result['step_count'],
            "artifacts": result.get('artifacts', []),
            "success": result.get('success', False)
        }

        metadata_file = Path("process1_metadata.json")
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

        print(f"\nProcess 1 metadata saved to: {metadata_file}")
        print(f"\nCheckpoint DB file exists: {Path(checkpoint_db).exists()}")
        print(f"Checkpoint DB size: {Path(checkpoint_db).stat().st_size} bytes")

        print("\n" + "=" * 60)
        print("PROCESS 1 COMPLETE")
        print("=" * 60)
        print(f"Task ID: {task_id}")
        print(f"Checkpoint saved to: {checkpoint_db}")
        print("Now run process 2 to verify recovery")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
