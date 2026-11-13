"""
GPU Research State Management

Defines the state structure for long-term GPU vulnerability research tasks.
Supports checkpointing and resume with LangGraph.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal, Annotated
from datetime import datetime
import operator


class GPUResearchState(TypedDict):
    """State for a GPU vulnerability research task"""

    # Task identification
    task_id: str
    task_description: str
    created_at: str
    updated_at: str

    # Current execution state
    phase: Literal["init", "detect", "generate", "compile", "execute", "verify", "complete", "failed"]
    step_count: int

    # CUDA environment
    cuda_env: Optional[Dict[str, Any]]

    # Code generation
    generated_code: Optional[str]
    generated_code_path: Optional[str]

    # Compilation
    compilation_attempts: Annotated[int, operator.add]  # Accumulate
    last_compilation_error: Optional[str]
    compiled_binary_path: Optional[str]

    # Execution
    execution_attempts: Annotated[int, operator.add]  # Accumulate
    execution_results: Annotated[List[Dict[str, Any]], operator.add]  # Append
    last_execution_output: Optional[str]

    # Artifacts
    artifacts: Annotated[List[str], operator.add]  # Append file paths

    # Context management
    context_summary: str
    messages: Annotated[List[Dict[str, Any]], operator.add]  # Message history

    # Error handling
    error_count: Annotated[int, operator.add]
    max_retries: int
    last_error: Optional[str]

    # Success criteria
    success: bool
    failure_reason: Optional[str]


def create_initial_state(task_id: str, task_description: str) -> GPUResearchState:
    """Create initial research task state"""
    now = datetime.now().isoformat()

    return GPUResearchState(
        task_id=task_id,
        task_description=task_description,
        created_at=now,
        updated_at=now,
        phase="init",
        step_count=0,
        cuda_env=None,
        generated_code=None,
        generated_code_path=None,
        compilation_attempts=0,
        last_compilation_error=None,
        compiled_binary_path=None,
        execution_attempts=0,
        execution_results=[],
        last_execution_output=None,
        artifacts=[],
        context_summary="Task initialized",
        messages=[],
        error_count=0,
        max_retries=3,
        last_error=None,
        success=False,
        failure_reason=None
    )
