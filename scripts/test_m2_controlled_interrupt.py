#!/usr/bin/env python
"""
M2 Final Test: Controlled Interruption and Resume

Tests true mid-task interruption using LangGraph's interrupt mechanism.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.controlled_interrupt import (
    process1_start_and_interrupt,
    process2_resume_and_complete
)


def main():
    print("=" * 60)
    print("M2 FINAL TEST: Controlled Mid-Task Interruption")
    print("=" * 60)

    settings = get_settings()
    llm = create_llm_client(settings)

    # Process 1: Start and interrupt
    print("\n### Running Process 1 ###\n")
    try:
        metadata = process1_start_and_interrupt(llm)
    except Exception as e:
        print(f"ERROR in Process 1: {e}")
        import traceback
        print(traceback.format_exc())
        return 1

    # Process 2: Resume and complete
    print("\n### Running Process 2 ###\n")
    try:
        result = process2_resume_and_complete(llm)

        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        success = True

        # Check completion
        if result['result']['step'] != 'executed':
            print(f"[X] Task did not complete execution (step: {result['result']['step']})")
            success = False
        else:
            print("[OK] Task completed execution")

        # Check duplication
        if result['no_duplication']:
            print("[OK] No artifact duplication detected")
        else:
            print("[X] Possible artifact duplication")
            success = False

        print("\n" + "=" * 60)
        if success:
            print("RESULT: M2 CONTROLLED INTERRUPT TEST PASSED")
            print("[OK] Task interrupted before execution")
            print("[OK] Task resumed and completed")
            print("[OK] No duplicate operations")
        else:
            print("RESULT: M2 CONTROLLED INTERRUPT TEST FAILED")
        print("=" * 60)

        return 0 if success else 1

    except Exception as e:
        print(f"ERROR in Process 2: {e}")
        import traceback
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
