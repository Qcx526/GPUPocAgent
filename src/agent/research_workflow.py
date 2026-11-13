"""
GPU Research StateGraph with Checkpointing

Implements a LangGraph-based workflow for long-term GPU research tasks.
Supports interruption and resume from checkpoints.
"""

from typing import Dict, Any, Literal
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.language_models import BaseChatModel

from src.agent.state import GPUResearchState, create_initial_state
from src.tools.cuda_tools import (
    detect_cuda_environment,
    write_cuda_source,
    compile_cuda_code,
    execute_cuda_program
)
from src.config import Settings


def detect_node(state: GPUResearchState) -> Dict[str, Any]:
    """Detect CUDA environment"""
    print(f"[Phase: detect] Detecting CUDA environment...")

    result = detect_cuda_environment.invoke({})

    return {
        "phase": "generate",
        "cuda_env": result,
        "step_count": state["step_count"] + 1,
        "context_summary": f"CUDA detected: {result.get('nvcc_version', 'unknown')}"
    }


def generate_node(state: GPUResearchState, llm: BaseChatModel) -> Dict[str, Any]:
    """Generate CUDA code with LLM"""
    print(f"[Phase: generate] Generating CUDA code...")

    # Use LLM to generate code based on task
    prompt = f"""
Generate a CUDA C program for: {state['task_description']}

Requirements:
- Target GPU: {state.get('cuda_env', {}).get('gpu_info', {}).get('name', 'unknown')}
- Compute capability: {state.get('cuda_env', {}).get('gpu_info', {}).get('compute_capability', '7.5')}
- Include verification of results
- Print clear success/failure message

Generate only the complete .cu source code, no explanations.
"""

    response = llm.invoke(prompt)
    code = response.content if hasattr(response, 'content') else str(response)

    # Save code
    code_dir = Path("data/generated_code")
    code_dir.mkdir(parents=True, exist_ok=True)
    code_path = code_dir / f"{state['task_id']}.cu"
    code_path.write_text(code, encoding='utf-8')

    return {
        "phase": "compile",
        "generated_code": code,
        "generated_code_path": str(code_path),
        "step_count": state["step_count"] + 1,
        "artifacts": [str(code_path)],
        "context_summary": "CUDA code generated"
    }


def compile_node(state: GPUResearchState) -> Dict[str, Any]:
    """Compile CUDA code"""
    print(f"[Phase: compile] Compiling CUDA code (attempt {state['compilation_attempts'] + 1})...")

    if not state.get("generated_code_path"):
        return {
            "phase": "failed",
            "error_count": 1,
            "last_error": "No source code path",
            "failure_reason": "Missing source code"
        }

    # Compile
    output_path = Path(state["generated_code_path"]).with_suffix("")

    result = compile_cuda_code.invoke({
        "source_file": state["generated_code_path"],
        "output_file": str(output_path),
        "compute_capability": state.get("cuda_env", {}).get("gpu_info", {}).get("compute_capability", "75").replace(".", "")
    })

    if result["success"]:
        return {
            "phase": "execute",
            "compiled_binary_path": result["output_path"],
            "compilation_attempts": 1,
            "step_count": state["step_count"] + 1,
            "artifacts": [result["output_path"]],
            "context_summary": "Compilation successful"
        }
    else:
        # Check if we should retry
        new_attempts = state["compilation_attempts"] + 1
        if new_attempts >= state["max_retries"]:
            return {
                "phase": "failed",
                "compilation_attempts": 1,
                "last_compilation_error": result["stderr"],
                "error_count": 1,
                "failure_reason": f"Compilation failed after {new_attempts} attempts"
            }
        else:
            # Could implement auto-fix here in future
            return {
                "phase": "failed",
                "compilation_attempts": 1,
                "last_compilation_error": result["stderr"],
                "error_count": 1,
                "failure_reason": "Compilation failed"
            }


def execute_node(state: GPUResearchState) -> Dict[str, Any]:
    """Execute compiled CUDA program"""
    print(f"[Phase: execute] Executing CUDA program (attempt {state['execution_attempts'] + 1})...")

    if not state.get("compiled_binary_path"):
        return {
            "phase": "failed",
            "error_count": 1,
            "failure_reason": "No compiled binary"
        }

    result = execute_cuda_program.invoke({
        "executable_path": state["compiled_binary_path"],
        "timeout_seconds": 30
    })

    execution_record = {
        "attempt": state["execution_attempts"] + 1,
        "success": result["success"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "return_code": result["return_code"]
    }

    if result["success"]:
        return {
            "phase": "verify",
            "execution_attempts": 1,
            "execution_results": [execution_record],
            "last_execution_output": result["stdout"],
            "step_count": state["step_count"] + 1,
            "context_summary": "Execution successful"
        }
    else:
        new_attempts = state["execution_attempts"] + 1
        if new_attempts >= state["max_retries"]:
            return {
                "phase": "failed",
                "execution_attempts": 1,
                "execution_results": [execution_record],
                "error_count": 1,
                "failure_reason": f"Execution failed after {new_attempts} attempts"
            }
        else:
            return {
                "phase": "failed",
                "execution_attempts": 1,
                "execution_results": [execution_record],
                "error_count": 1,
                "failure_reason": "Execution failed"
            }


def verify_node(state: GPUResearchState) -> Dict[str, Any]:
    """Verify results"""
    print(f"[Phase: verify] Verifying results...")

    # Simple verification: check if output contains success indicators
    output = state.get("last_execution_output") or ""

    success_indicators = ["success", "passed", "correct", "verified", "ok"]
    failure_indicators = ["error", "failed", "incorrect", "mismatch"]

    output_lower = output.lower()

    has_success = any(ind in output_lower for ind in success_indicators)
    has_failure = any(ind in output_lower for ind in failure_indicators)

    if has_success and not has_failure:
        return {
            "phase": "complete",
            "success": True,
            "step_count": state["step_count"] + 1,
            "context_summary": "Task completed successfully"
        }
    elif has_failure:
        return {
            "phase": "failed",
            "success": False,
            "failure_reason": "Verification failed: output indicates errors",
            "error_count": 1
        }
    else:
        # Inconclusive - treat as success if execution succeeded
        return {
            "phase": "complete",
            "success": True,
            "step_count": state["step_count"] + 1,
            "context_summary": "Task completed (verification inconclusive but execution succeeded)"
        }


def create_research_workflow(
    llm: BaseChatModel,
    checkpointer=None
) -> Any:
    """
    Create a checkpointed StateGraph for GPU research.

    Args:
        llm: Language model for code generation
        checkpointer: Checkpoint saver (default: MemorySaver)

    Returns:
        Compiled StateGraph with checkpointing
    """
    # Create checkpointer if not provided
    if checkpointer is None:
        checkpointer = MemorySaver()

    # Create graph
    workflow = StateGraph(GPUResearchState)

    # Add nodes
    workflow.add_node("detect", detect_node)
    workflow.add_node("generate", lambda state: generate_node(state, llm))
    workflow.add_node("compile", compile_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("verify", verify_node)

    # Set entry point
    workflow.set_entry_point("detect")

    # Add edges
    workflow.add_edge("detect", "generate")
    workflow.add_edge("generate", "compile")
    workflow.add_edge("compile", "execute")
    workflow.add_edge("execute", "verify")
    workflow.add_edge("verify", END)

    # Compile with checkpointing
    app = workflow.compile(checkpointer=checkpointer)

    return app
