"""Main CLI entry point for dva-agentic-cli."""

import typer
from rich.console import Console
from typing_extensions import Annotated

from dva_agentic_cli import __version__
from dva_agentic_cli.config import CLI_NAME
from dva_agentic_cli.commands.project import project_app
from dva_agentic_cli.commands.init import init_app
from dva_agentic_cli.commands.kg import kg_app
from dva_agentic_cli.commands.data import data_app
from dva_agentic_cli.commands.mcp import mcp_app
from dva_agentic_cli.commands.agent import agent_app
from dva_agentic_cli.commands.skill import skill_app
from dva_agentic_cli.commands.code import code_app
from dva_agentic_cli.commands.domain import domain_app
from dva_agentic_cli.commands.product import product_app
from dva_agentic_cli.commands.history import history_app
from dva_agentic_cli.commands.agent_template import agent_template_app
from dva_agentic_cli.commands.agent_tool import agent_tool_app

app = typer.Typer(
    name=CLI_NAME,
    help="DVA Agentic CLI - Command-line interface for agentic workflows using ADK agent platform",
    add_completion=False,
    rich_markup_mode=None,  # Disable rich markup to avoid help rendering issues
)
console = Console()

# Register command groups
app.add_typer(init_app, name="init")
app.add_typer(project_app, name="project")
app.add_typer(kg_app, name="kg")
app.add_typer(data_app, name="data")
app.add_typer(mcp_app, name="mcp")
app.add_typer(agent_app, name="agent")
app.add_typer(skill_app, name="skill")
app.add_typer(code_app, name="code")
app.add_typer(domain_app, name="domain")
app.add_typer(product_app, name="product")
app.add_typer(history_app, name="history")
app.add_typer(agent_template_app, name="agent-template")
app.add_typer(agent_tool_app, name="agent-tool")


def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        console.print(f"[bold green]{CLI_NAME}[/bold green] version [cyan]{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show version information",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """
    DVA Agentic CLI - Command-line interface for agentic workflows.
    
    Use --help with any command to see available options.
    """
    pass


@app.command()
def dashboard(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to serve the dashboard")] = 8500,
    host: Annotated[str, typer.Option("--host", help="Host to bind to")] = "127.0.0.1",
) -> None:
    """
    Launch the DVA Agentic Dashboard (web UI) for validating agents.

    Opens a browser to http://localhost:8500 with:
      - Overview (products, domains, repos, MCP health)
      - Domain detail (repos, docs, persona skills)
      - Agent project validation (file checks, config)
      - Template catalogue (use cases, frameworks, tools)
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[red]✗[/red] Dashboard requires extra dependencies.")
        console.print("[dim]Install with: pip install 'dva-agentic-cli[dashboard]'[/dim]")
        raise typer.Exit(1)

    console.print(
        f"[bold cyan]DVA Agentic Dashboard[/bold cyan] starting at "
        f"[link=http://{host}:{port}]http://{host}:{port}[/link]"
    )
    uvicorn.run("dva_agentic_cli.dashboard.api:app", host=host, port=port, log_level="info")


@app.command()
def hello(
    name: Annotated[str, typer.Argument(help="Name to greet")] = "World",
) -> None:
    """
    Simple hello command to verify CLI is working.
    
    This is a placeholder command that will be replaced with actual ADK agent commands.
    """
    console.print(f"[bold green]Hello[/bold green] [cyan]{name}[/cyan]! 👋")
    console.print("[dim]DVA Agentic CLI is ready for your commands.[/dim]")


if __name__ == "__main__":
    app()
