"""
GPU Research Agent - Deep Agents Integration

Unified entry point for long-term GPU vulnerability research using Deep Agents.
This replaces the scattered M1/M2 implementations with a single production agent.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from src.tools.cuda_tools import (
    detect_cuda_environment,
    write_cuda_source,
    compile_cuda_code,
    execute_cuda_program
)
from src.config import Settings


class GPUResearchAgent:
    """
    Production GPU research agent using Deep Agents.

    Capabilities:
    - Long-term CVE research tasks
    - Autonomous CUDA experimentation
    - Checkpoint and resume across process boundaries
    - Artifact management and verification
    """

    def __init__(
        self,
        llm: BaseChatModel,
        settings: Settings,
        checkpoint_db: str = "gpu_research_checkpoints.db"
    ):
        """
        Initialize GPU research agent.

        Args:
            llm: Language model instance
            settings: Application settings
            checkpoint_db: Path to SQLite checkpoint database
        """
        self.settings = settings
        self.checkpoint_db = checkpoint_db

        # Create SQLite checkpointer
        self.conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
        self.checkpointer = SqliteSaver(self.conn)

        # Collect CUDA tools
        cuda_tools = [
            detect_cuda_environment,
            write_cuda_source,
            compile_cuda_code,
            execute_cuda_program
        ]

        # Create Deep Agent with GPU tools
        self.agent = create_deep_agent(
            model=llm,
            tools=cuda_tools,
            checkpointer=self.checkpointer
        )

    def start_research_task(
        self,
        task_id: str,
        task_description: str,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new research task.

        Args:
            task_id: Unique task identifier
            task_description: Research goal description
            thread_id: Optional thread ID (defaults to task_id)

        Returns:
            Task execution result
        """
        if thread_id is None:
            thread_id = task_id

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        result = self.agent.invoke({
            "messages": [("user", task_description)]
        }, config=config)

        return {
            "task_id": task_id,
            "thread_id": thread_id,
            "result": result,
            "checkpoint_db": self.checkpoint_db
        }

    def resume_task(
        self,
        thread_id: str,
        additional_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resume a previously started task.

        Args:
            thread_id: Thread ID of the task to resume
            additional_instruction: Optional additional instruction

        Returns:
            Task execution result
        """
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        # Load checkpoint state
        state = self.agent.get_state(config)

        if not state.values:
            raise ValueError(f"No checkpoint found for thread {thread_id}")

        # Continue from checkpoint
        if additional_instruction:
            result = self.agent.invoke({
                "messages": [("user", additional_instruction)]
            }, config=config)
        else:
            # Resume with current state
            result = self.agent.invoke(None, config=config)

        return {
            "thread_id": thread_id,
            "result": result,
            "checkpoint_db": self.checkpoint_db
        }

    def get_task_state(self, thread_id: str) -> Dict[str, Any]:
        """
        Get current state of a task.

        Args:
            thread_id: Thread ID of the task

        Returns:
            Task state snapshot
        """
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        state = self.agent.get_state(config)

        if not state.values:
            return {"error": f"No checkpoint found for thread {thread_id}"}

        return {
            "thread_id": thread_id,
            "values": state.values,
            "next": state.next,
            "metadata": state.metadata
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def create_gpu_research_agent(
    settings: Settings,
    llm: BaseChatModel,
    checkpoint_db: str = "gpu_research_checkpoints.db"
) -> GPUResearchAgent:
    """
    Factory function to create GPU research agent.

    Args:
        settings: Application settings
        llm: Language model instance
        checkpoint_db: Path to checkpoint database

    Returns:
        Configured GPUResearchAgent instance
    """
    return GPUResearchAgent(llm, settings, checkpoint_db)
