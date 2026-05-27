"""Agent template management commands."""

import json
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli.registry.manager import RegistryManager
from agentic_cli.registry.base import RegistryConfig
from agentic_cli.tracker import record_activity

console = Console()
agent_template_app = typer.Typer(help="Manage agent templates", rich_markup_mode=None)

# Configuration directory and file
AGENT_CONFIG_DIR = Path.home() / ".agent-cli-agentic"
AGENT_CONFIG_FILE = AGENT_CONFIG_DIR / "config.json"


def _load_config() -> dict:
    """Load configuration from file."""
    if AGENT_CONFIG_FILE.exists():
        return json.loads(AGENT_CONFIG_FILE.read_text())
    return {}


def _get_code_workspace() -> Path:
    """Get the configured code workspace directory."""
    config = _load_config()
    workspace = config.get("code_workspace")
    if workspace:
        return Path(workspace).expanduser().resolve()
    # Default to ~/dva-code-workspace
    return Path.home() / "dva-code-workspace"


@agent_template_app.command("list")
def list_templates(
    framework: Annotated[
        Optional[str],
        typer.Option("--framework", "-f", help="Filter by framework (adk, langgraph)"),
    ] = None,
    use_case: Annotated[
        Optional[str],
        typer.Option("--use-case", "-u", help="Filter by use case"),
    ] = None,
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
    """List available agent templates."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-templates")
        if not reg:
            raise typer.Exit(1)
    
    # List templates
    templates = reg.list_items(framework=framework, use_case=use_case, category=category, tag=tag)
    
    if not templates:
        console.print("[yellow]No templates found matching the criteria[/yellow]")
        return
    
    # Display templates
    table = Table(title=f"Agent Templates ({len(templates)} found)")
    table.add_column("Name", style="cyan")
    table.add_column("Framework", style="green")
    table.add_column("Use Case", style="blue")
    table.add_column("Category", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Version", style="magenta")
    
    for template in templates:
        description = template.description[:60] + "..." if len(template.description) > 60 else template.description
        table.add_row(
            template.name,
            template.framework,
            template.use_case,
            template.category or "-",
            description,
            template.version
        )
    
    console.print(table)


@agent_template_app.command("show")
def show_template(
    name: Annotated[str, typer.Argument(help="Template name")],
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """Show detailed information about a template."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-templates")
        if not reg:
            raise typer.Exit(1)
    
    # Get template
    template = reg.get_item(name)
    if not template:
        console.print(f"[red]Template '{name}' not found[/red]")
        raise typer.Exit(1)
    
    # Display template details
    content = f"""[bold cyan]Template Details[/bold cyan]

[bold]Name:[/bold] {template.name}
[bold]Framework:[/bold] {template.framework}
[bold]Use Case:[/bold] {template.use_case}
[bold]Category:[/bold] {template.category or 'N/A'}
[bold]Version:[/bold] {template.version}
[bold]Author:[/bold] {template.author}
[bold]Created:[/bold] {template.created_at}
[bold]Updated:[/bold] {template.updated_at}

[bold]Description:[/bold]
{template.description}

[bold]Tags:[/bold] {', '.join(template.tags) if template.tags else 'None'}

[bold]Dependencies:[/bold] {', '.join(template.dependencies) if template.dependencies else 'None'}

[bold]Path:[/bold] {template.path or 'templates/' + template.framework + '/' + template.name}
"""
    
    console.print(Panel.fit(content, border_style="cyan"))


@agent_template_app.command("install")
def install_template(
    name: Annotated[str, typer.Argument(help="Template name")],
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
    """Install an agent template.

    By default, the template is installed in the configured code workspace.
    Use --target to specify a custom location.
    """
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-templates")
        if not reg:
            raise typer.Exit(1)
    
    # Determine target path
    if target:
        target_path = Path(target).resolve()
    else:
        # Use code workspace as default location
        workspace = _get_code_workspace()
        target_path = workspace / name
        # Ensure workspace directory exists
        if not workspace.exists():
            console.print(f"[yellow]Workspace directory does not exist: {workspace}[/yellow]")
            console.print(f"[dim]Creating workspace directory...[/dim]")
            try:
                workspace.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓[/green] Created: {workspace}")
            except Exception as e:
                console.print(f"[red]✗ Failed to create workspace: {e}[/red]")
                console.print(f"[dim]Falling back to current directory[/dim]")
                target_path = Path.cwd() / name
    
    # Install template
    success = reg.install_item(name, target_path, version)
    
    if success:
        record_activity(
            command="agent-template",
            subcommand="install",
            args={"name": name, "target": str(target_path), "version": version}
        )
        console.print(f"[green]Template '{name}' installed to {target_path}[/green]")
    else:
        console.print(f"[red]Failed to install template '{name}'[/red]")
        raise typer.Exit(1)


# Create subcommand for registry operations
registry_app = typer.Typer(help="Registry management commands", rich_markup_mode=None)
agent_template_app.add_typer(registry_app, name="registry")


@registry_app.command("add")
def add_registry(
    name: Annotated[str, typer.Argument(help="Registry name")],
    url_or_path: Annotated[str, typer.Argument(help="Git URL or local path")],
    default: Annotated[
        bool,
        typer.Option("--default", help="Set as default registry"),
    ] = False,
) -> None:
    """Add a new agent template registry."""
    manager = RegistryManager()
    
    # Determine if URL or path
    if url_or_path.startswith(("http://", "https://", "git@")):
        config = RegistryConfig(
            name=name,
            type="agent-templates",
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
            type="agent-templates",
            path=str(path),
            enabled=True,
            default=default
        )
    
    # Add registry
    manager.add_registry(name, config)
    console.print(f"[green]Registry '{name}' added successfully[/green]")
    
    record_activity(
        command="agent-template",
        subcommand="registry-add",
        args={"name": name, "url_or_path": url_or_path}
    )


@registry_app.command("remove")
def remove_registry(
    name: Annotated[str, typer.Argument(help="Registry name")],
) -> None:
    """Remove an agent template registry."""
    manager = RegistryManager()
    
    success = manager.remove_registry(name)
    if success:
        console.print(f"[green]Registry '{name}' removed successfully[/green]")
        record_activity(
            command="agent-template",
            subcommand="registry-remove",
            args={"name": name}
        )
    else:
        console.print(f"[red]Registry '{name}' not found[/red]")
        raise typer.Exit(1)


@registry_app.command("list")
def list_registries() -> None:
    """List all agent template registries."""
    manager = RegistryManager()
    manager.show_registries("agent-templates")


@agent_template_app.command("categories")
def list_categories(
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """List available template categories."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-templates")
        if not reg:
            raise typer.Exit(1)
    
    categories = reg.get_categories()
    
    if not categories:
        console.print("[yellow]No categories found[/yellow]")
        return
    
    table = Table(title="Template Categories")
    table.add_column("Category", style="cyan")
    
    for category in categories:
        table.add_row(category)
    
    console.print(table)


@agent_template_app.command("frameworks")
def list_frameworks(
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """List available frameworks."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-templates")
        if not reg:
            raise typer.Exit(1)
    
    frameworks = reg.get_frameworks()
    
    if not frameworks:
        console.print("[yellow]No frameworks found[/yellow]")
        return
    
    table = Table(title="Available Frameworks")
    table.add_column("Framework", style="cyan")
    
    for framework in frameworks:
        table.add_row(framework)
    
    console.print(table)


@agent_template_app.command("use-cases")
def list_use_cases(
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", "-r", help="Registry name to use"),
    ] = None,
) -> None:
    """List available use cases."""
    manager = RegistryManager()
    
    # Get registry
    if registry:
        reg = manager.get_registry(registry)
        if not reg:
            console.print(f"[red]Registry '{registry}' not found[/red]")
            raise typer.Exit(1)
    else:
        reg = manager.ensure_registry_available("agent-templates")
        if not reg:
            raise typer.Exit(1)
    
    use_cases = reg.get_use_cases()
    
    if not use_cases:
        console.print("[yellow]No use cases found[/yellow]")
        return
    
    table = Table(title="Available Use Cases")
    table.add_column("Use Case", style="cyan")
    
    for use_case in use_cases:
        table.add_row(use_case)
    
    console.print(table)
