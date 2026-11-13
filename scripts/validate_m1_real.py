#!/usr/bin/env python
"""
Real M1 Validation - End-to-End Test with Real LLM

This script performs actual validation of:
1. LLM API connectivity and tool calling
2. Agent autonomous CUDA workflow
3. Real GPU compilation and execution
4. Evidence collection and verification

Does NOT use mocks or simulations.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from src.config import get_settings
from src.llm.client import create_llm_client, verify_llm_connection
from src.agent.simple_agent import run_simple_experiment


console = Console()


def verify_tool_calling(llm, console):
    """Verify that the LLM supports native tool calling"""
    console.print("\n[bold]Step 1: Verify Tool Calling Support[/bold]")

    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage

    @tool
    def test_tool(input: str) -> str:
        """A simple test tool."""
        return f"Tool received: {input}"

    try:
        llm_with_tools = llm.bind_tools([test_tool])
        response = llm_with_tools.invoke([
            HumanMessage(content="Call the test_tool with input 'hello'")
        ])

        if hasattr(response, 'tool_calls') and len(response.tool_calls) > 0:
            console.print("  [OK] [green]Native tool calling supported[/green]")
            console.print(f"  Tool called: {response.tool_calls[0]['name']}")
            return True
        else:
            console.print("  [!] [yellow]Warning: No tool calls detected[/yellow]")
            console.print(f"  Response type: {type(response)}")
            if hasattr(response, 'content'):
                console.print(f"  Content: {response.content[:200]}")
            return False
    except Exception as e:
        console.print(f"  [X] [red]Tool calling test failed: {e}[/red]")
        return False


def validate_experiment_results(results: dict, console) -> tuple[bool, list[str]]:
    """
    Validate experiment results with strict criteria.
    Returns (success, issues) tuple.
    """
    console.print("\n[bold]Step 3: Validate Experiment Results[/bold]")

    issues = []

    # Check basic structure
    if not results.get("intermediate_steps"):
        issues.append("No intermediate steps recorded (agent did not use tools)")

    if results.get("tool_calls_count", 0) == 0:
        issues.append("No tool calls detected")

    # Check for required tool usage
    tool_names = [step.get("tool", "") for step in results.get("intermediate_steps", [])]

    required_tools = ["detect_cuda_environment", "write_cuda_source", "compile_cuda_code", "execute_cuda_program"]
    missing_tools = [t for t in required_tools if t not in tool_names]

    if missing_tools:
        issues.append(f"Missing required tools: {', '.join(missing_tools)}")

    # Check for actual execution evidence
    steps = results.get("intermediate_steps", [])

    # Find execution result
    execution_result = None
    for step in steps:
        if step.get("type") == "tool_result" and step.get("tool") == "execute_cuda_program":
            try:
                content = step.get("content", "")
                # Try to parse as dict
                if "success" in content.lower():
                    execution_result = content
                    break
            except:
                pass

    if not execution_result:
        issues.append("No GPU execution result found in tool outputs")
    else:
        # Check if execution actually succeeded
        if "success" not in execution_result.lower() or "'success': false" in execution_result.lower():
            issues.append("GPU execution did not report success")

    # Display validation table
    table = Table(title="Validation Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    table.add_row(
        "Intermediate steps recorded",
        "[OK]" if not any("intermediate" in i for i in issues) else "[X]",
        str(len(results.get("intermediate_steps", [])))
    )

    table.add_row(
        "Tool calls made",
        "[OK]" if results.get("tool_calls_count", 0) > 0 else "[X]",
        str(results.get("tool_calls_count", 0))
    )

    table.add_row(
        "Required tools used",
        "[OK]" if not missing_tools else "[X]",
        f"{len(required_tools) - len(missing_tools)}/{len(required_tools)}"
    )

    table.add_row(
        "GPU execution verified",
        "[OK]" if execution_result and "success" in execution_result.lower() else "[X]",
        "Found" if execution_result else "Not found"
    )

    console.print(table)

    success = len(issues) == 0
    return success, issues


def main():
    console.print(Panel.fit(
        "[bold cyan]M1 Real Validation - End-to-End Test[/bold cyan]",
        border_style="cyan"
    ))

    # Load configuration
    console.print("\n[bold]Loading Configuration[/bold]")
    try:
        settings = get_settings()
        console.print("  [OK] Configuration loaded")
        console.print(f"  Model: {settings.llm_model}")
        console.print(f"  Base URL: {settings.llm_base_url}")
    except Exception as e:
        console.print(f"  [X] [red]Configuration error: {e}[/red]")
        return 1

    # Create LLM client
    console.print("\n[bold]Creating LLM Client[/bold]")
    try:
        llm = create_llm_client(settings)
        success, message = verify_llm_connection(llm)

        if success:
            console.print(f"  [green]OK: {message}[/green]")
        else:
            console.print(f"  [red]FAIL: {message}[/red]")
            return 1
    except Exception as e:
        console.print(f"  [X] [red]LLM client creation failed: {e}[/red]")
        return 1

    # Verify tool calling
    if not verify_tool_calling(llm, console):
        console.print("\n[yellow]Warning: Tool calling may not work correctly[/yellow]")
        console.print("Continuing anyway to test actual behavior...")

    # Run experiment
    console.print("\n[bold]Step 2: Run Autonomous GPU Experiment[/bold]")

    task = """
Conduct a complete CUDA experiment:

1. First, detect the CUDA environment and GPU capabilities using detect_cuda_environment tool
2. Then write a simple CUDA program that adds two vectors on the GPU using write_cuda_source tool
3. Compile the program for the detected GPU architecture using compile_cuda_code tool
4. Execute the program using execute_cuda_program tool
5. Verify the results are correct

Report whether the experiment succeeded or failed based on actual tool outputs.
"""

    console.print("\n[dim]Task:[/dim]")
    console.print(Markdown(task))

    console.print("\n[yellow][*]  Agent is running...[/yellow]\n")

    try:
        results = run_simple_experiment(
            task=task,
            llm=llm,
            settings=settings,
            verbose=True
        )

        console.print("\n[bold green][OK] Experiment completed without exceptions[/bold green]")

    except Exception as e:
        console.print(f"\n[bold red][X] Experiment failed with exception: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        return 1

    # Validate results
    success, issues = validate_experiment_results(results, console)

    # Display results
    console.print("\n[bold]Experiment Output:[/bold]")
    console.print(Panel(results['output'][:1000], border_style="green" if success else "yellow"))

    console.print(f"\n[bold]Results saved to:[/bold] {results['results_saved_to']}")
    console.print(f"[dim]Total messages: {results.get('total_messages', 0)}[/dim]")
    console.print(f"[dim]Tool calls: {results.get('tool_calls_count', 0)}[/dim]")

    # Final verdict
    if success:
        console.print("\n[bold green][OK] M1 VALIDATION PASSED[/bold green]")
        console.print("All required tools were used and GPU execution succeeded.")
        return 0
    else:
        console.print("\n[bold yellow][!] M1 VALIDATION ISSUES FOUND[/bold yellow]")
        for issue in issues:
            console.print(f"  • {issue}")
        console.print("\nThe agent ran but did not fully complete the expected workflow.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
