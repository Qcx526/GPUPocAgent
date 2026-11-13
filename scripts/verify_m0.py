#!/usr/bin/env python
"""
M0 Verification Script - Test core technology stack

This script verifies:
1. Environment configuration (.env)
2. LLM API connectivity (Qwen gateway with DeepSeek model)
3. Tool calling capability
4. Basic LangChain/LangGraph integration

Run this after setting up .env file to ensure everything works.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from src.config import get_settings
from src.llm.client import create_llm_client, verify_llm_connection


console = Console()


@tool
def get_cuda_version() -> str:
    """Get the CUDA version installed on the system.

    Returns:
        CUDA version string
    """
    return "CUDA 13.3 (mock response for testing)"


@tool
def check_gpu_availability() -> dict:
    """Check if NVIDIA GPU is available and get basic info.

    Returns:
        Dictionary with GPU availability and info
    """
    return {
        "available": True,
        "name": "NVIDIA GeForce GTX 1660",
        "compute_capability": "7.5",
        "memory_mb": 6144
    }


def main():
    console.print(Panel.fit(
        "[bold cyan]GPUVulnAgent - M0 Technology Stack Verification[/bold cyan]",
        border_style="cyan"
    ))

    results = Table(title="Verification Results", show_header=True, header_style="bold magenta")
    results.add_column("Component", style="cyan", width=30)
    results.add_column("Status", width=15)
    results.add_column("Details", style="dim")

    # 1. Check configuration
    console.print("\n[bold]Step 1: Configuration[/bold]")
    try:
        settings = get_settings()
        results.add_row(
            "Configuration (.env)",
            "[green]✓ PASS[/green]",
            f"Model: {settings.llm_model}"
        )
        console.print(f"  ✓ Loaded settings from .env")
        console.print(f"  • Model: {settings.llm_model}")
        console.print(f"  • Base URL: {settings.llm_base_url}")
    except Exception as e:
        results.add_row(
            "Configuration (.env)",
            "[red]✗ FAIL[/red]",
            str(e)
        )
        console.print(f"  ✗ [red]Configuration error: {e}[/red]")
        console.print("\n[yellow]Please copy .env.example to .env and configure your API key.[/yellow]")
        console.print(results)
        return 1

    # 2. Test LLM connectivity
    console.print("\n[bold]Step 2: LLM Connectivity[/bold]")
    try:
        client = create_llm_client(settings)
        console.print(f"  • Created LLM client")

        success, message = verify_llm_connection(client)
        if success:
            results.add_row(
                "LLM API Connection",
                "[green]✓ PASS[/green]",
                "Basic message invocation successful"
            )
            console.print(f"  ✓ [green]{message}[/green]")
        else:
            results.add_row(
                "LLM API Connection",
                "[red]✗ FAIL[/red]",
                message
            )
            console.print(f"  ✗ [red]{message}[/red]")
            console.print(results)
            return 1

    except Exception as e:
        results.add_row(
            "LLM API Connection",
            "[red]✗ FAIL[/red]",
            str(e)
        )
        console.print(f"  ✗ [red]Connection failed: {e}[/red]")
        console.print(results)
        return 1

    # 3. Test tool calling
    console.print("\n[bold]Step 3: Tool Calling[/bold]")
    try:
        tools = [get_cuda_version, check_gpu_availability]
        llm_with_tools = client.bind_tools(tools)
        console.print(f"  • Bound {len(tools)} tools to LLM")

        # Test tool calling
        response = llm_with_tools.invoke([
            HumanMessage(content="Check if GPU is available and get CUDA version")
        ])

        console.print(f"  • Invoked LLM with tool calling request")

        # Check response
        has_tool_calls = hasattr(response, 'tool_calls') and len(response.tool_calls) > 0

        if has_tool_calls:
            results.add_row(
                "Tool Calling",
                "[green]✓ PASS[/green]",
                f"LLM called {len(response.tool_calls)} tool(s)"
            )
            console.print(f"  ✓ [green]LLM successfully invoked tools[/green]")
            for tc in response.tool_calls:
                console.print(f"    → Tool: {tc['name']}")
        else:
            # Some models might not support tool calling or might respond differently
            results.add_row(
                "Tool Calling",
                "[yellow]⚠ WARN[/yellow]",
                "No tool calls detected - model may have limitations"
            )
            console.print(f"  ⚠ [yellow]Warning: No tool calls detected[/yellow]")
            console.print(f"  Response type: {type(response)}")
            if hasattr(response, 'content'):
                console.print(f"  Content: {response.content[:200]}")

    except Exception as e:
        results.add_row(
            "Tool Calling",
            "[red]✗ FAIL[/red]",
            str(e)
        )
        console.print(f"  ✗ [red]Tool calling failed: {e}[/red]")

    # 4. Test LangGraph availability
    console.print("\n[bold]Step 4: LangGraph Components[/bold]")
    try:
        from langgraph.graph import StateGraph, END
        from langgraph.checkpoint.memory import MemorySaver

        results.add_row(
            "LangGraph",
            "[green]✓ PASS[/green]",
            "StateGraph and checkpoint imports successful"
        )
        console.print(f"  ✓ LangGraph core components available")

    except Exception as e:
        results.add_row(
            "LangGraph",
            "[red]✗ FAIL[/red]",
            str(e)
        )
        console.print(f"  ✗ [red]LangGraph import failed: {e}[/red]")

    # Display summary
    console.print("\n")
    console.print(results)

    console.print("\n[bold green]M0 Verification Complete![/bold green]")
    console.print("\n[dim]Next steps:[/dim]")
    console.print("  1. Review any warnings or failures above")
    console.print("  2. Proceed to M1: Building minimal GPU agent loop")

    return 0


if __name__ == "__main__":
    sys.exit(main())
