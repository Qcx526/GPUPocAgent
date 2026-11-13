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

    experiment_data = {
        "task": task,
        "timestamp": timestamp,
        "output": results.get("output"),
        "intermediate_steps": [
            {
                "action": step[0].tool,
                "action_input": step[0].tool_input,
                "observation": str(step[1])[:500]  # Truncate long outputs
            }
            for step in results.get("intermediate_steps", [])
        ]
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

    results = {
        "output": final_message.content if hasattr(final_message, 'content') else str(final_message),
        "intermediate_steps": []  # LangGraph tracks this differently
    }

    # Save results
    results_dir = settings.data_dir / "experiments"
    results_path = save_experiment_results(task, results, results_dir)

    # Add metadata
    results["results_saved_to"] = str(results_path)
    results["all_messages"] = [str(m) for m in messages["messages"]]

    return results
