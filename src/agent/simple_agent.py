"""
Simple GPU Agent - M1 Minimal Implementation

This implements a simple reactive agent that can autonomously:
1. Detect CUDA environment
2. Generate CUDA test programs
3. Compile and execute them
4. Verify results and save artifacts

Uses LangChain's create_react_agent for simplicity in M1.
Will evolve to LangGraph/Deep Agents in M2+ for persistence.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

from langgraph.prebuilt import create_react_agent
from langchain_core.language_models import BaseChatModel

from src.tools.cuda_tools import CUDA_TOOLS
from src.config import Settings


# System message for the agent
AGENT_SYSTEM_MESSAGE = """You are an expert GPU security researcher specializing in CUDA and NVIDIA GPU systems.

Your task is to autonomously conduct GPU experiments by:
1. Understanding the research goal
2. Detecting available CUDA environment and GPU capabilities
3. Generating appropriate CUDA test programs
4. Compiling and executing them safely
5. Analyzing results and saving evidence
6. Reporting findings clearly

When conducting experiments:
- Always start by detecting the CUDA environment
- Generate minimal, focused CUDA programs
- Check compilation output carefully
- Verify execution results match expectations
- Save all artifacts with descriptive names
- Report both successes and failures honestly
"""


def create_simple_agent(
    llm: BaseChatModel,
    settings: Settings,
    verbose: bool = True
):
    """
    Create a simple ReAct agent for M1 GPU experiments using LangGraph.

    Args:
        llm: Language model instance
        settings: Application settings
        verbose: Enable verbose output

    Returns:
        Configured LangGraph agent
    """
    # Create ReAct agent using LangGraph's prebuilt
    agent = create_react_agent(
        model=llm,
        tools=CUDA_TOOLS,
        prompt=AGENT_SYSTEM_MESSAGE
    )

    return agent


def save_experiment_results(
    task: str,
    results: Dict[str, Any],
    output_dir: Path
) -> Path:
    """
    Save experiment results to a structured JSON file.

    Args:
        task: Original task/goal
        results: Agent execution results
        output_dir: Directory to save results

    Returns:
        Path to saved results file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_{timestamp}.json"
    output_path = output_dir / filename

    # intermediate_steps is now a list of dicts
    experiment_data = {
        "task": task,
        "timestamp": timestamp,
        "output": results.get("output"),
        "intermediate_steps": results.get("intermediate_steps", []),
        "tool_calls_count": results.get("tool_calls_count", 0),
        "total_messages": results.get("total_messages", 0)
    }

    output_path.write_text(json.dumps(experiment_data, indent=2), encoding='utf-8')

    return output_path


def run_simple_experiment(
    task: str,
    llm: BaseChatModel,
    settings: Settings,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run a simple GPU experiment with the agent.

    Args:
        task: Experiment goal/task description
        llm: Language model instance
        settings: Application settings
        verbose: Enable verbose output

    Returns:
        Experiment results including output and artifacts
    """
    # Create agent
    agent = create_simple_agent(llm, settings, verbose=verbose)

    # Run experiment with LangGraph agent
    messages = agent.invoke({"messages": [("user", task)]})

    # Extract results from LangGraph message format
    final_message = messages["messages"][-1]

    # Extract intermediate steps from message history
    intermediate_steps = []
    for msg in messages["messages"]:
        # AIMessage with tool_calls
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                intermediate_steps.append({
                    "type": "tool_call",
                    "tool": tool_call.get("name", "unknown"),
                    "args": tool_call.get("args", {}),
                    "id": tool_call.get("id", "")
                })
        # ToolMessage with tool results
        elif hasattr(msg, 'content') and hasattr(msg, 'name'):
            if msg.__class__.__name__ == 'ToolMessage':
                intermediate_steps.append({
                    "type": "tool_result",
                    "tool": getattr(msg, 'name', 'unknown'),
                    "content": str(msg.content)[:1000],  # Limit length
                    "tool_call_id": getattr(msg, 'tool_call_id', '')
                })

    results = {
        "output": final_message.content if hasattr(final_message, 'content') else str(final_message),
        "intermediate_steps": intermediate_steps,
        "total_messages": len(messages["messages"]),
        "tool_calls_count": sum(1 for s in intermediate_steps if s["type"] == "tool_call")
    }

    # Save results
    results_dir = settings.data_dir / "experiments"
    results_path = save_experiment_results(task, results, results_dir)

    # Add metadata
    results["results_saved_to"] = str(results_path)
    results["all_messages"] = [
        {
            "type": msg.__class__.__name__,
            "content": str(msg.content)[:500] if hasattr(msg, 'content') else str(msg)[:500]
        }
        for msg in messages["messages"]
    ]

    return results
