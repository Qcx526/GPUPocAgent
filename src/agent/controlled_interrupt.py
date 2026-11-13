"""
M2 Controlled Interruption with LangGraph Interrupts

Uses LangGraph's interrupt_before mechanism to stop execution
at a specific point, then resume from that exact state.
"""

from typing import TypedDict, Annotated, Literal
import operator
from pathlib import Path
import json
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.language_models import BaseChatModel
import sqlite3

from src.tools.cuda_tools import (
    detect_cuda_environment,
    write_cuda_source,
    compile_cuda_code,
    execute_cuda_program
)


class InterruptTestState(TypedDict):
    """State for controlled interruption test"""
    task_id: str
    step: str
    cuda_env: dict
    source_code: str
    source_path: str
    compiled_binary: str
    execution_output: str
    messages: Annotated[list, operator.add]
    artifacts: Annotated[list, operator.add]


def detect_step(state: InterruptTestState) -> dict:
    """Step 1: Detect CUDA"""
    print("[Step 1/4] Detecting CUDA environment...")
    result = detect_cuda_environment.invoke({})

    return {
        "step": "detected",
        "cuda_env": result,
        "messages": [f"CUDA detected: {result.get('gpu_info', {}).get('name')}"]
    }


def generate_step(state: InterruptTestState, llm: BaseChatModel) -> dict:
    """Step 2: Generate code"""
    print("[Step 2/4] Generating CUDA code...")

    prompt = f"""
Generate a simple CUDA vector addition program.
Target GPU: {state['cuda_env'].get('gpu_info', {}).get('name')}
Compute capability: {state['cuda_env'].get('gpu_info', {}).get('compute_capability')}

Generate only the complete .cu source code.
"""

    response = llm.invoke(prompt)
    code = response.content if hasattr(response, 'content') else str(response)

    # Save code
    code_dir = Path("data/interrupt_test")
    code_dir.mkdir(parents=True, exist_ok=True)
    code_path = code_dir / f"{state['task_id']}.cu"
    code_path.write_text(code, encoding='utf-8')

    return {
        "step": "generated",
        "source_code": code,
        "source_path": str(code_path),
        "artifacts": [str(code_path)],
        "messages": [f"Code generated: {code_path}"]
    }


def compile_step(state: InterruptTestState) -> dict:
    """Step 3: Compile code"""
    print("[Step 3/4] Compiling...")

    output_path = Path(state['source_path']).with_suffix("")

    result = compile_cuda_code.invoke({
        "source_file": state['source_path'],
        "output_file": str(output_path),
        "compute_capability": "75"
    })

    if result["success"]:
        return {
            "step": "compiled",
            "compiled_binary": result["output_path"],
            "artifacts": [result["output_path"]],
            "messages": [f"Compilation successful: {result['output_path']}"]
        }
    else:
        return {
            "step": "compile_failed",
            "messages": [f"Compilation failed: {result['stderr'][:500]}"]
        }


def execute_step(state: InterruptTestState) -> dict:
    """Step 4: Execute (this is where we'll interrupt before)"""
    print("[Step 4/4] Executing...")

    result = execute_cuda_program.invoke({
        "executable_path": state['compiled_binary'],
        "timeout_seconds": 30
    })

    return {
        "step": "executed",
        "execution_output": result["stdout"],
        "messages": [f"Execution: {'SUCCESS' if result['success'] else 'FAILED'}"]
    }


def create_interrupt_workflow(
    llm: BaseChatModel,
    checkpoint_db: str = "interrupt_controlled.db"
) -> tuple:
    """
    Create workflow with interrupt before execution step.

    Returns:
        (workflow, checkpointer)
    """
    # Create checkpointer
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # Create workflow
    workflow = StateGraph(InterruptTestState)

    # Add nodes
    workflow.add_node("detect", detect_step)
    workflow.add_node("generate", lambda s: generate_step(s, llm))
    workflow.add_node("compile", compile_step)
    workflow.add_node("execute", execute_step)

    # Define flow
    workflow.set_entry_point("detect")
    workflow.add_edge("detect", "generate")
    workflow.add_edge("generate", "compile")
    workflow.add_edge("compile", "execute")
    workflow.add_edge("execute", END)

    # Compile with checkpoint and interrupt BEFORE execute
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["execute"]  # STOP before execution
    )

    return app, checkpointer, conn


def process1_start_and_interrupt(llm: BaseChatModel) -> dict:
    """
    Process 1: Start task and interrupt before execution.

    Returns:
        Metadata about interrupted task
    """
    task_id = f"controlled_int_{uuid.uuid4().hex[:8]}"
    thread_id = task_id

    print("=" * 60)
    print("PROCESS 1: Start and Interrupt")
    print("=" * 60)
    print(f"Task ID: {task_id}")

    # Create workflow
    checkpoint_db = "interrupt_controlled.db"
    app, checkpointer, conn = create_interrupt_workflow(llm, checkpoint_db)

    # Initial state
    initial_state = {
        "task_id": task_id,
        "step": "init",
        "cuda_env": {},
        "source_code": "",
        "source_path": "",
        "compiled_binary": "",
        "execution_output": "",
        "messages": [],
        "artifacts": []
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Run until interrupt
        print("\nStarting workflow (will interrupt before execution)...")
        result = app.invoke(initial_state, config=config)

        print(f"\nWorkflow interrupted at step: {result['step']}")
        print(f"Artifacts created: {len(result['artifacts'])}")

        # Save metadata
        metadata = {
            "process": 1,
            "task_id": task_id,
            "thread_id": thread_id,
            "checkpoint_db": checkpoint_db,
            "interrupted_at_step": result['step'],
            "artifacts": result['artifacts'],
            "next_step": "execute"
        }

        Path("interrupt_controlled_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding='utf-8'
        )

        print(f"\nProcess 1 complete:")
        print(f"  Interrupted at: {result['step']}")
        print(f"  Artifacts: {result['artifacts']}")
        print(f"  Next step: execute")

        return metadata

    finally:
        conn.close()


def process2_resume_and_complete(llm: BaseChatModel) -> dict:
    """
    Process 2: Resume from interrupt and complete execution.

    Returns:
        Final result
    """
    # Load metadata
    metadata_file = Path("interrupt_controlled_metadata.json")
    if not metadata_file.exists():
        raise FileNotFoundError("Run process 1 first")

    metadata = json.loads(metadata_file.read_text(encoding='utf-8'))

    print("=" * 60)
    print("PROCESS 2: Resume and Complete")
    print("=" * 60)
    print(f"Task ID: {metadata['task_id']}")
    print(f"Resuming from: {metadata['interrupted_at_step']}")

    # Create NEW workflow (simulating restart)
    checkpoint_db = metadata['checkpoint_db']
    app, checkpointer, conn = create_interrupt_workflow(llm, checkpoint_db)

    config = {"configurable": {"thread_id": metadata['thread_id']}}

    try:
        # Resume from checkpoint
        print("\nResuming workflow...")
        result = app.invoke(None, config=config)  # None = continue from checkpoint

        print(f"\nWorkflow completed:")
        print(f"  Final step: {result['step']}")
        print(f"  Total artifacts: {len(result['artifacts'])}")

        # Verify no duplication
        artifacts_before = set(metadata['artifacts'])
        artifacts_after = set(result['artifacts'])
        new_artifacts = artifacts_after - artifacts_before

        print(f"\nArtifact analysis:")
        print(f"  Before resume: {len(artifacts_before)}")
        print(f"  After resume: {len(artifacts_after)}")
        print(f"  New artifacts: {len(new_artifacts)}")

        if len(new_artifacts) > 0:
            print(f"  New: {list(new_artifacts)}")

        return {
            "task_id": metadata['task_id'],
            "result": result,
            "artifacts_before": list(artifacts_before),
            "artifacts_after": list(artifacts_after),
            "no_duplication": len(artifacts_after) <= len(artifacts_before) + 1  # Allow 1 new (output)
        }

    finally:
        conn.close()
