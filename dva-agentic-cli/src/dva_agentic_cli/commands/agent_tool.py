"""Agent tool management commands."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from dva_agentic_cli.registry.manager import RegistryManager
from dva_agentic_cli.registry.base import RegistryConfig
from dva_agentic_cli.tracker import record_activity

console = Console()
agent_tool_app = typer.Typer(help="Manage agent tools", rich_markup_mode=None)


@agent_tool_app.command("list")
def list_tools(
    category: Annotated[
        Optional[str],
        typer.Option("--category", "-c", help="Filter by category"),
    ] = None,
    tag: Annotated[
        Optional[str],
        typer.Option("--tag", "-t", help="Filter by tag"),
    ] = None,
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """List available agent tools."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-tools")
        if not reg:
            raise typer.Exit(1)
    
    # List tools
    tools = reg.list_items(category=category, tag=tag)
    
    if not tools:
        console.print("[yellow]No tools found matching the criteria[/yellow]")
        return
    
    # Display tools
    table = Table(title=f"Agent Tools ({len(tools)} found)")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Class", style="blue")
    table.add_column("Description", style="white")
    table.add_column("Version", style="magenta")
    
    for tool in tools:
        description = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
        table.add_row(
            tool.name,
            tool.category or "-",
            tool.class_name,
            description,
            tool.version
        )
    
    console.print(table)


@agent_tool_app.command("show")
def show_tool(
    name: Annotated[str, typer.Argument(help="Tool name")],
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """Show detailed information about a tool."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-tools")
        if not reg:
            raise typer.Exit(1)
    
    # Get tool
    tool = reg.get_item(name)
    if not tool:
        console.print(f"[red]Tool '{name}' not found[/red]")
        raise typer.Exit(1)
    
    # Display tool details
    content = f"""[bold cyan]Tool Details[/bold cyan]

[bold]Name:[/bold] {tool.name}
[bold]Category:[/bold] {tool.category or 'N/A'}
[bold]Version:[/bold] {tool.version}
[bold]Author:[/bold] {tool.author}
[bold]Created:[/bold] {tool.created_at}
[bold]Updated:[/bold] {tool.updated_at}

[bold]Entry Point:[/bold] {tool.entry_point}
[bold]Class Name:[/bold] {tool.class_name}

[bold]Description:[/bold]
{tool.description}

[bold]Tags:[/bold] {', '.join(tool.tags) if tool.tags else 'None'}

[bold]Dependencies:[/bold] {', '.join(tool.dependencies) if tool.dependencies else 'None'}

[bold]Path:[/bold] {tool.path or 'tools/' + (tool.category or 'misc') + '/' + tool.name}
"""
    
    console.print(Panel.fit(content, border_style="cyan"))


@agent_tool_app.command("install")
def install_tool(
    name: Annotated[str, typer.Argument(help="Tool name")],
    target: Annotated[
        Optional[str],
        typer.Option("--target", "-t", help="Target directory (default: current directory)"),
    ] = None,
    version: Annotated[
        Optional[str],
        typer.Option("--version", "-v", help="Specific version to install"),
    ] = None,
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """Install an agent tool."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-tools")
        if not reg:
            raise typer.Exit(1)
    
    # Determine target path
    if target:
        target_path = Path(target).resolve()
    else:
        target_path = Path.cwd() / "tools"
    
    # Install tool
    success = reg.install_item(name, target_path, version)
    
    if success:
        record_activity(
            command="agent-tool",
            subcommand="install",
            args={"name": name, "target": str(target_path), "version": version}
        )
        console.print(f"[green]Tool '{name}' installed to {target_path}[/green]")
    else:
        console.print(f"[red]Failed to install tool '{name}'[/red]")
        raise typer.Exit(1)


# Create subcommand for registry operations
registry_app = typer.Typer(help="Registry management commands", rich_markup_mode=None)
agent_tool_app.add_typer(registry_app, name="registry")


@registry_app.command("add")
def add_registry(
    name: Annotated[str, typer.Argument(help="Registry name")],
    url_or_path: Annotated[str, typer.Argument(help="Git URL or local path")],
    default: Annotated[
        bool,
        typer.Option("--default", help="Set as default registry"),
    ] = False,
) -> None:
    """Add a new agent tool registry."""
    manager = RegistryManager()
    
    # Determine if URL or path
    if url_or_path.startswith(("http://", "https://", "git@")):
        config = RegistryConfig(
            name=name,
            type="agent-tools",
            url=url_or_path,
            enabled=True,
            default=default
        )
    else:
        # Local path
        path = Path(url_or_path).expanduser()
        if not path.exists():
            console.print(f"[red]Path does not exist: {path}[/red]")
            raise typer.Exit(1)
        
        config = RegistryConfig(
            name=name,
            type="agent-tools",
            path=str(path),
            enabled=True,
            default=default
        )
    
    # Add registry
    manager.add_registry(name, config)
    console.print(f"[green]Registry '{name}' added successfully[/green]")
    
    record_activity(
        command="agent-tool",
        subcommand="registry-add",
        args={"name": name, "url_or_path": url_or_path}
    )


@registry_app.command("remove")
def remove_registry(
    name: Annotated[str, typer.Argument(help="Registry name")],
) -> None:
    """Remove an agent tool registry."""
    manager = RegistryManager()
    
    success = manager.remove_registry(name)
    if success:
        console.print(f"[green]Registry '{name}' removed successfully[/green]")
        record_activity(
            command="agent-tool",
            subcommand="registry-remove",
            args={"name": name}
        )
    else:
        console.print(f"[red]Registry '{name}' not found[/red]")
        raise typer.Exit(1)


@registry_app.command("list")
def list_registries() -> None:
    """List all agent tool registries."""
    manager = RegistryManager()
    manager.show_registries("agent-tools")


@agent_tool_app.command("categories")
def list_categories(
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """List available tool categories."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-tools")
        if not reg:
            raise typer.Exit(1)
    
    categories = reg.get_categories()
    
    if not categories:
        console.print("[yellow]No categories found[/yellow]")
        return
    
    table = Table(title="Tool Categories")
    table.add_column("Category", style="cyan")
    
    for category in categories:
        table.add_row(category)
    
    console.print(table)


@agent_tool_app.command("dependencies")
def show_dependencies(
    name: Annotated[str, typer.Argument(help="Tool name")],
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """Show dependencies for a specific tool."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-tools")
        if not reg:
            raise typer.Exit(1)
    
    dependencies = reg.get_dependencies(name)
    
    if not dependencies:
        console.print(f"[yellow]Tool '{name}' has no dependencies[/yellow]")
        return
    
    table = Table(title=f"Dependencies for {name}")
    table.add_column("Dependency", style="cyan")
    
    for dep in dependencies:
        table.add_row(dep)
    
    console.print(table)
