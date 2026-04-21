"""Main entry point for the ADK agent project."""

import asyncio
import logging
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from src.config import settings
from src.agents.example import ExampleAgent
from src.workflows.example_workflow import simple_workflow, multi_step_workflow

# Setup logging
logging.basicConfig(
    level=settings.log_level,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
console = Console()


async def demo_agent():
    """Demonstrate basic agent usage."""
    console.print(Panel.fit("🤖 ADK Agent Demo", style="bold blue"))

    # Create agent
    agent = ExampleAgent(model=settings.agent_model)
    console.print(f"[green]✓[/green] Created agent: {agent}")

    # Process some input
    test_inputs = [
        "Hello, I'm testing the ADK agent!",
        "What can you help me with?",
        "Tell me about artificial intelligence.",
    ]

    for i, input_text in enumerate(test_inputs, 1):
        console.print(f"\n[cyan]Input {i}:[/cyan] {input_text}")
        result = await agent.process({"text": input_text})
        
        if result["success"]:
            console.print(f"[green]Output:[/green] {result['result']}")
        else:
            console.print(f"[red]Error:[/red] {result.get('error')}")

    # Show stats
    console.print("\n[bold]Agent Statistics:[/bold]")
    stats = agent.get_stats()
    
    table = Table(show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in stats.items():
        table.add_row(key, str(value))
    
    console.print(table)


async def demo_workflows():
    """Demonstrate workflow usage."""
    console.print(Panel.fit("🔄 Workflow Demo", style="bold blue"))

    # Simple workflow
    console.print("\n[bold cyan]Running Simple Workflow[/bold cyan]")
    result1 = await simple_workflow("Process this text with the agent")
    console.print(f"[green]✓[/green] Workflow completed: {result1['workflow']}")

    # Multi-step workflow
    console.print("\n[bold cyan]Running Multi-Step Workflow[/bold cyan]")
    result2 = await multi_step_workflow("Analyze and summarize this important text")
    console.print(f"[green]✓[/green] Workflow completed: {result2['workflow']}")
    console.print(f"Success: {result2['success']}")


async def main():
    """Main application entry point."""
    console.print(
        Panel.fit(
            "[bold green]ADK Agent Project[/bold green]\n"
            f"Environment: {settings.environment}\n"
            f"Provider: {settings.agent_provider}\n"
            f"Model: {settings.agent_model}",
            title="Welcome",
            border_style="green",
        )
    )

    # Check configuration based on provider
    if settings.agent_provider == "vertex_ai":
        if settings.is_vertex_ai_configured():
            console.print(
                f"[green]✓[/green] Vertex AI configured: "
                f"Project {settings.google_project_id} in {settings.google_location}"
            )
        else:
            console.print(
                "[yellow]⚠ Warning:[/yellow] Vertex AI not properly configured. "
                "Set GOOGLE_PROJECT_ID and GOOGLE_LOCATION in .env file."
            )
    elif not settings.openai_api_key and not settings.anthropic_api_key:
        console.print(
            "[yellow]⚠ Warning:[/yellow] No API keys configured. "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file."
        )

    try:
        # Run demos
        await demo_agent()
        console.print("\n" + "=" * 60 + "\n")
        await demo_workflows()

        console.print(
            Panel.fit(
                "[bold green]✓ Demo completed successfully![/bold green]\n"
                "Check the code in src/ to customize your agents.",
                border_style="green",
            )
        )

    except Exception as e:
        logger.error(f"Error running demo: {e}", exc_info=True)
        console.print(f"[red]✗ Error:[/red] {e}")


if __name__ == "__main__":
    asyncio.run(main())
