"""Main entry point for the Basic Agent."""

import asyncio
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from .agents.basic_agent import BasicAgent
from .config import settings

console = Console()
app = typer.Typer(help="Basic Agent - A simple agent using Google ADK framework")


@app.command()
def run(
    message: Optional[str] = typer.Argument(None, help="Message to send to the agent"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Run in interactive mode"),
) -> None:
    """Run the basic agent."""
    
    if not settings.is_configured:
        console.print("[red]Error: Google Cloud project not configured[/red]")
        console.print("[dim]Please set GOOGLE_PROJECT_ID in your .env file[/dim]")
        raise typer.Exit(1)
    
    try:
        agent = BasicAgent()
        
        if interactive:
            console.print(Panel.fit(
                "[bold cyan]Basic Agent - Interactive Mode[/bold cyan]\n\n"
                "Type 'quit' or 'exit' to stop the agent.",
                border_style="cyan"
            ))
            
            while True:
                try:
                    user_input = console.input("[bold blue]You:[/bold blue] ")
                    if user_input.lower() in ['quit', 'exit']:
                        console.print("[yellow]Goodbye![/yellow]")
                        break
                    
                    response = asyncio.run(agent.run(user_input))
                    console.print(f"[bold green]Agent:[/bold green] {response}")
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Goodbye![/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
        
        elif message:
            response = asyncio.run(agent.run(message))
            console.print(f"[bold green]Response:[/bold green] {response}")
        
        else:
            console.print("[yellow]Please provide a message or use --interactive mode[/yellow]")
            console.print("[dim]Example: basic-agent run 'Hello, how are you?'[/dim]")
            console.print("[dim]Example: basic-agent run --interactive[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error starting agent: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show agent status and configuration."""
    
    console.print(Panel.fit(
        "[bold cyan]Basic Agent Status[/bold cyan]\n\n"
        f"[bold]Agent Name:[/bold] {settings.agent_name}\n"
        f"[bold]Description:[/bold] {settings.agent_description}\n"
        f"[bold]Google Project:[/bold] {settings.google_project_id}\n"
        f"[bold]Location:[/bold] {settings.google_location}\n"
        f"[bold]Model:[/bold] {settings.vertex_ai_model}\n"
        f"[bold]Log Level:[/bold] {settings.log_level}\n"
        f"[bold]Configured:[/bold] {'Yes' if settings.is_configured else 'No'}",
        border_style="cyan"
    ))


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__
    console.print(f"[bold green]Basic Agent[/bold green] version [cyan]{__version__}[/cyan]")


def main() -> None:
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
