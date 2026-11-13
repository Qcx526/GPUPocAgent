#!/usr/bin/env python
"""
Low-budget DeepSeek API test with path verification.
Tests LLM connectivity and workspace path configuration.
"""

import sys
from pathlib import Path

# Set up path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("DEEPSEEK API & WORKSPACE INTEGRATION TEST")
print("=" * 70)

try:
    from src.config import get_config, run_directory
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    config = get_config()

    # Test 1: Verify paths
    print("\n[1] Workspace Path Configuration")
    print(f"    Project root: {config.project_root}")
    print(f"    Workspace: {config.workspace_root}")

    task_id = "test_deepseek_api"
    run_id = "verify_001"
    run_dir = run_directory(task_id, run_id)
    print(f"    Test run dir: {run_dir}")
    print(f"    [OK] Path configuration verified")

    # Test 2: Create LLM client
    print("\n[2] Creating DeepSeek LLM Client")
    llm = ChatOpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
        temperature=0.3,
        max_tokens=100
    )
    print(f"    Model: {llm.model_name}")
    print(f"    Base URL: {config.llm_base_url}")
    print(f"    [OK] Client created")

    # Test 3: Simple API call
    print("\n[3] Testing API Connectivity (Low Budget)")
    print("    Sending: 'What is 2+2?'")

    response = llm.invoke([
        HumanMessage(content="What is 2+2? Answer in one word only.")
    ])

    answer = response.content.strip()
    print(f"    Response: {answer}")
    print(f"    [OK] API call successful")

    # Test 4: Tool calling preparation
    print("\n[4] Preparing for Tool Calling")
    print(f"    Workspace for runs: {config.workspace_root / 'runs'}")
    print(f"    State storage: {config.workspace_root / 'state'}")

    # Create run directories for tool testing
    (run_dir / "source").mkdir(parents=True, exist_ok=True)
    (run_dir / "build").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    print(f"    [OK] Run directories created")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
    print("\nDeepSeek API is working.")
    print("Workspace structure is ready for CUDA tools.")
    print("\nNext: Run GPUResearchAgent with real CUDA task")

except Exception as e:
    print(f"\n[FAIL] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
