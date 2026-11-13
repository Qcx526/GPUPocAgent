#!/usr/bin/env python
"""
Simple M1 validation without Rich formatting issues
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.simple_agent import run_simple_experiment


def main():
    print("=" * 60)
    print("M1 Real Validation - Simplified Output")
    print("=" * 60)

    # Load settings
    print("\n1. Loading configuration...")
    settings = get_settings()
    print(f"   Model: {settings.llm_model}")
    print(f"   OK")

    # Create LLM
    print("\n2. Creating LLM client...")
    llm = create_llm_client(settings)
    print("   OK")

    # Run experiment
    print("\n3. Running autonomous GPU experiment...")
    print("   (This may take 1-2 minutes)")

    task = """
Conduct a complete CUDA experiment:
1. Detect CUDA environment and GPU using detect_cuda_environment
2. Write a CUDA vector addition program using write_cuda_source
3. Compile it using compile_cuda_code
4. Execute it using execute_cuda_program
5. Verify results

Report success or failure based on actual tool outputs.
"""

    results = run_simple_experiment(task, llm, settings, verbose=False)

    print("\n4. Validating results...")

    steps = results.get("intermediate_steps", [])
    tool_calls = results.get("tool_calls_count", 0)

    print(f"   Total messages: {results.get('total_messages', 0)}")
    print(f"   Tool calls made: {tool_calls}")
    print(f"   Intermediate steps: {len(steps)}")

    # Check required tools
    tool_names = [s.get("tool", "") for s in steps if s.get("type") == "tool_call"]
    required = ["detect_cuda_environment", "write_cuda_source", "compile_cuda_code", "execute_cuda_program"]

    print(f"\n   Tools used:")
    for tool in required:
        status = "OK" if tool in tool_names else "MISSING"
        print(f"     - {tool}: {status}")

    # Check execution result - MUST verify actual success
    exec_results = [
        s for s in steps
        if s.get("type") == "tool_result" and s.get("tool") == "execute_cuda_program"
    ]

    exec_success = False
    if exec_results:
        # Parse the last execution result
        last_exec = exec_results[-1]
        content = last_exec.get("content", "")

        # Must contain success indicators
        # MUST NOT just check for presence - check for actual success
        if "'success': True" in content or '"success": true' in content.lower():
            # Additional verification: check for computation correctness
            if "0 mismatch" in content.lower() or "correct" in content.lower():
                exec_success = True
                print(f"\n   GPU execution verified: SUCCESS with correct results")
            else:
                print(f"\n   GPU execution status unclear - no verification found")
        else:
            print(f"\n   GPU execution FAILED or status unknown")

    print(f"\n   GPU execution result found: {'YES' if exec_results else 'NO'}")
    print(f"   GPU execution successful: {'YES' if exec_success else 'NO'}")

    # Save detailed results
    result_file = Path("validation_result_m1.json")
    result_file.write_text(json.dumps({
        "tool_calls_count": tool_calls,
        "intermediate_steps": steps,
        "output": results.get("output", "")[:2000],
        "tools_used": tool_names,
        "all_required_tools_used": all(t in tool_names for t in required),
        "execution_verified": exec_success
    }, indent=2), encoding='utf-8')

    print(f"\n   Detailed results saved to: {result_file}")
    print(f"   Experiment results: {results['results_saved_to']}")

    # Final verdict
    success = (
        tool_calls >= 4 and
        all(t in tool_names for t in required) and
        exec_success  # MUST have verified successful execution
    )

    print("\n" + "=" * 60)
    if success:
        print("RESULT: M1 VALIDATION PASSED")
        print("All required tools used and GPU execution verified with correct results.")
    else:
        print("RESULT: M1 VALIDATION FAILED")
        if tool_calls < 4:
            print(f"Insufficient tool calls: {tool_calls} < 4")
        if not all(t in tool_names for t in required):
            missing = [t for t in required if t not in tool_names]
            print(f"Missing tools: {missing}")
        if not exec_success:
            print("GPU execution not verified or failed")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
