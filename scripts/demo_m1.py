#!/usr/bin/env python
"""
M1 Demo - Simple GPU Agent Experiment

Demonstrates the minimal agent loop:
1. Agent detects CUDA environment
2. Agent generates a simple CUDA program
3. Agent compiles and executes it
4. Agent verifies results
5. Artifacts are saved

This validates the core M1 capability.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.config import get_settings
from src.llm.client import create_llm_client
from src.agent.simple_agent import run_simple_experiment


console = Console()


def main():
    console.print(Panel.fit(
        "[bold cyan]M1 Demo: Simple GPU Agent Experiment[/bold cyan]",
        border_style="cyan"
    ))

    # Load configuration
    try:
        settings = get_settings()
        console.print("✓ Configuration loaded", style="green")
    except ValueError as e:
        console.print(f"✗ Configuration error: {e}", style="red")
        console.print("\n[yellow]Please configure .env file with your API key[/yellow]")
        return 1

    # Create LLM client
    console.print("✓ Creating LLM client...", style="green")
    llm = create_llm_client(settings)

    # Define experiment task
    task = """
    Conduct a simple CUDA experiment:
    1. Detect the CUDA environment and GPU capabilities
    2. Write a simple CUDA program that adds two vectors on the GPU
    3. Compile the program for the detected GPU architecture
    4. Execute it and verify the results
    5. Report your findings

    The goal is to verify that basic CUDA computation works correctly.
    """

    console.print("\n[bold]Experiment Task:[/bold]")
    console.print(Markdown(task))

    console.print("\n[bold yellow]⚙️  Starting autonomous agent...[/bold yellow]\n")

    # Run experiment
    try:
        results = run_simple_experiment(
            task=task,
            llm=llm,
            settings=settings,
            verbose=True
        )

        console.print("\n[bold green]✓ Experiment completed![/bold green]")
        console.print(f"\nResults saved to: {results['results_saved_to']}")

        console.print("\n[bold]Agent Output:[/bold]")
        console.print(Panel(results['output'], border_style="green"))

        console.print(f"\n[dim]Total steps: {len(results.get('intermediate_steps', []))}[/dim]")

        return 0

    except Exception as e:
        console.print(f"\n[bold red]✗ Experiment failed: {e}[/bold red]", style="red")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        return 1


if __name__ == "__main__":
    sys.exit(main())
