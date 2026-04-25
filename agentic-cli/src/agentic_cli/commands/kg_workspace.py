"""Workspace management commands for dva kg."""

from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from agentic_cli.kg.config import KGConfig
from agentic_cli.kg.workspace import WorkspaceManager

workspace_app = typer.Typer(
    help="Workspace management commands (LightRAG only)",
    rich_markup_mode=None
)
console = Console()


def _check_provider_support(config: KGConfig) -> bool:
    """
    Check if current provider supports workspaces.
    
    Args:
        config: KG configuration
        
    Returns:
        True if supported, exits otherwise
    """
    if not config.supports_workspaces():
        console.print(
            f"[bold red]✗ Error:[/bold red] Workspaces are only supported for LightRAG provider."
        )
        console.print(f"[dim]Current provider: {config.provider}[/dim]")
        console.print(
            f"[dim]To use workspaces, switch to LightRAG: "
            f"dva kg init --provider lightrag[/dim]"
        )
        raise typer.Exit(1)
    return True


@workspace_app.command()
def create(
    name: Annotated[str, typer.Argument(help="Workspace name")],
    description: Annotated[str, typer.Option("--description", "-d", help="Workspace description")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="Comma-separated tags")] = None,
    environment: Annotated[str, typer.Option("--env", "-e", help="Environment (development, evaluation, production, staging)")] = "development",
    parent: Annotated[str, typer.Option("--parent", "-p", help="Parent workspace to clone from")] = None,
) -> None:
    """Create a new workspace."""
    config = KGConfig.load()
    _check_provider_support(config)
    
    manager = WorkspaceManager(config.workspace_base_dir)
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    
    try:
        if parent:
            # Clone from parent
            metadata = manager.clone_workspace(parent, name, description, tag_list)
            console.print(f"[green]✓[/green] Workspace '{name}' created as clone of '{parent}'")
        else:
            # Create new workspace
            metadata = manager.create_workspace(
                name=name,
                description=description,
                tags=tag_list,
                environment=environment
            )
            console.print(f"[green]✓[/green] Workspace '{name}' created")
        
        # Show metadata
        panel = Panel(
            f"[cyan]Name:[/cyan] {metadata.name}\n"
            f"[cyan]Environment:[/cyan] {metadata.environment}\n"
            f"[cyan]Created:[/cyan] {metadata.created_at}\n"
            f"[cyan]Tags:[/cyan] {', '.join(metadata.tags) if metadata.tags else 'None'}\n"
            f"[cyan]Path:[/cyan] {manager.get_workspace_path(name)}",
            title="Workspace Details"
        )
        console.print(panel)
        
        # Suggest switching to new workspace
        if config.workspace != name:
            console.print(
                f"\n[dim]To switch to this workspace: "
                f"dva kg workspace switch {name}[/dim]"
            )
        
    except ValueError as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command("list")
def list_workspaces() -> None:
    """List all workspaces."""
    config = KGConfig.load()
    _check_provider_support(config)
    
    manager = WorkspaceManager(config.workspace_base_dir)
    
    try:
        workspaces = manager.list_workspaces()
        
        if not workspaces:
            console.print("[yellow]No workspaces found[/yellow]")
            console.print(
                f"[dim]Create a workspace: dva kg workspace create <name>[/dim]"
            )
            return
        
        table = Table(title="Knowledge Graph Workspaces")
        table.add_column("Name", style="cyan")
        table.add_column("Environment", style="green")
        table.add_column("Documents", justify="right")
        table.add_column("Entities", justify="right")
        table.add_column("Created", style="dim")
        table.add_column("Active", justify="center")
        
        for ws in sorted(workspaces, key=lambda x: x.name):
            is_active = "✓" if ws.name == config.workspace else ""
            active_style = "bold green" if is_active else ""
            
            table.add_row(
                ws.name,
                ws.environment,
                str(ws.document_count),
                str(ws.entity_count),
                ws.created_at[:10],  # Just date
                is_active,
                style=active_style
            )
        
        console.print(table)
        console.print(f"\n[dim]Active workspace: {config.workspace}[/dim]")
        console.print(f"[dim]Base directory: {config.workspace_base_dir}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def switch(
    name: Annotated[str, typer.Argument(help="Workspace name to switch to")],
) -> None:
    """Switch to a different workspace."""
    config = KGConfig.load()
    _check_provider_support(config)
    
    manager = WorkspaceManager(config.workspace_base_dir)
    
    try:
        # Verify workspace exists
        workspace = manager.get_workspace(name)
        
        # Update config
        config.workspace = name
        config.save()
        
        console.print(f"[green]✓[/green] Switched to workspace '{name}'")
        console.print(f"[dim]Environment: {workspace.environment}[/dim]")
        console.print(f"[dim]Path: {manager.get_workspace_path(name)}[/dim]")
        
        # Show stats if available
        if workspace.document_count > 0:
            console.print(
                f"\n[cyan]Stats:[/cyan] "
                f"{workspace.document_count} documents, "
                f"{workspace.entity_count} entities, "
                f"{workspace.relation_count} relations"
            )
        
    except ValueError as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def current() -> None:
    """Show current active workspace."""
    config = KGConfig.load()
    _check_provider_support(config)
    
    manager = WorkspaceManager(config.workspace_base_dir)
    
    try:
        workspace = manager.get_workspace(config.workspace)
        
        panel = Panel(
            f"[cyan]Name:[/cyan] {workspace.name}\n"
            f"[cyan]Environment:[/cyan] {workspace.environment}\n"
            f"[cyan]Description:[/cyan] {workspace.description or 'None'}\n"
            f"[cyan]Tags:[/cyan] {', '.join(workspace.tags) if workspace.tags else 'None'}\n"
            f"[cyan]Documents:[/cyan] {workspace.document_count}\n"
            f"[cyan]Entities:[/cyan] {workspace.entity_count}\n"
            f"[cyan]Relations:[/cyan] {workspace.relation_count}\n"
            f"[cyan]Created:[/cyan] {workspace.created_at}\n"
            f"[cyan]Last Updated:[/cyan] {workspace.last_updated or 'Never'}\n"
            f"[cyan]Path:[/cyan] {manager.get_workspace_path(workspace.name)}",
            title="Current Workspace"
        )
        console.print(panel)
        
        if workspace.parent_workspace:
            console.print(
                f"\n[dim]Parent workspace: {workspace.parent_workspace}[/dim]"
            )
        if workspace.snapshot_of:
            console.print(f"[dim]Snapshot of: {workspace.snapshot_of}[/dim]")
        
    except ValueError as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def delete(
    name: Annotated[str, typer.Argument(help="Workspace name to delete")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    force: Annotated[bool, typer.Option("--force", "-f", help="Force delete default workspace")] = False,
) -> None:
    """Delete a workspace."""
    config = KGConfig.load()
    _check_provider_support(config)
    
    manager = WorkspaceManager(config.workspace_base_dir)
    
    # Check if trying to delete active workspace
    if name == config.workspace:
        console.print(
            "[red]✗[/red] Cannot delete active workspace. "
            "Switch to another workspace first."
        )
        console.print(f"[dim]Current workspace: {config.workspace}[/dim]")
        console.print(f"[dim]Switch with: dva kg workspace switch <name>[/dim]")
        raise typer.Exit(1)
    
    # Get workspace info for confirmation
    try:
        workspace = manager.get_workspace(name)
    except ValueError as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
    
    # Confirmation prompt
    if not yes:
        console.print(f"\n[bold yellow]⚠ Warning:[/bold yellow] This will delete workspace '{name}'")
        console.print(f"[dim]Environment: {workspace.environment}[/dim]")
        console.print(f"[dim]Documents: {workspace.document_count}[/dim]")
        console.print(f"[dim]Path: {manager.get_workspace_path(name)}[/dim]")
        console.print("[dim]This operation cannot be undone.[/dim]\n")
        
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)
    
    try:
        manager.delete_workspace(name, force=force)
        console.print(f"[green]✓[/green] Workspace '{name}' deleted")
        
    except ValueError as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def info(
    name: Annotated[str, typer.Argument(help="Workspace name")],
) -> None:
    """Show detailed information about a workspace."""
    config = KGConfig.load()
    _check_provider_support(config)
    
    manager = WorkspaceManager(config.workspace_base_dir)
    
    try:
        workspace = manager.get_workspace(name)
        
        is_active = "Yes" if name == config.workspace else "No"
        
        panel = Panel(
            f"[cyan]Name:[/cyan] {workspace.name}\n"
            f"[cyan]Active:[/cyan] {is_active}\n"
            f"[cyan]Environment:[/cyan] {workspace.environment}\n"
            f"[cyan]Description:[/cyan] {workspace.description or 'None'}\n"
            f"[cyan]Tags:[/cyan] {', '.join(workspace.tags) if workspace.tags else 'None'}\n"
            f"[cyan]Provider:[/cyan] {workspace.provider}\n"
            f"[cyan]Documents:[/cyan] {workspace.document_count}\n"
            f"[cyan]Entities:[/cyan] {workspace.entity_count}\n"
            f"[cyan]Relations:[/cyan] {workspace.relation_count}\n"
            f"[cyan]Created:[/cyan] {workspace.created_at}\n"
            f"[cyan]Last Updated:[/cyan] {workspace.last_updated or 'Never'}\n"
            f"[cyan]Path:[/cyan] {manager.get_workspace_path(name)}",
            title=f"Workspace: {name}"
        )
        console.print(panel)
        
        if workspace.parent_workspace:
            console.print(f"\n[cyan]Parent Workspace:[/cyan] {workspace.parent_workspace}")
        if workspace.snapshot_of:
            console.print(f"[cyan]Snapshot Of:[/cyan] {workspace.snapshot_of}")
        
    except ValueError as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def update(
    name: Annotated[str, typer.Argument(help="Workspace name")],
    description: Annotated[str, typer.Option("--description", "-d", help="New description")] = None,
    tags: Annotated[str, typer.Option("--tags", "-t", help="New comma-separated tags")] = None,
    environment: Annotated[str, typer.Option("--env", "-e", help="New environment")] = None,
) -> None:
    """Update workspace metadata."""
    config = KGConfig.load()
    _check_provider_support(config)
    
    manager = WorkspaceManager(config.workspace_base_dir)
    
    if not any([description, tags, environment]):
        console.print("[yellow]⚠[/yellow] No updates specified")
        console.print("[dim]Use --description, --tags, or --env to update metadata[/dim]")
        raise typer.Exit(0)
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    
    try:
        workspace = manager.update_workspace_metadata(
            name=name,
            description=description,
            tags=tag_list,
            environment=environment
        )
        
        console.print(f"[green]✓[/green] Workspace '{name}' updated")
        
        # Show updated metadata
        panel = Panel(
            f"[cyan]Name:[/cyan] {workspace.name}\n"
            f"[cyan]Environment:[/cyan] {workspace.environment}\n"
            f"[cyan]Description:[/cyan] {workspace.description or 'None'}\n"
            f"[cyan]Tags:[/cyan] {', '.join(workspace.tags) if workspace.tags else 'None'}\n"
            f"[cyan]Last Updated:[/cyan] {workspace.last_updated}",
            title="Updated Workspace"
        )
        console.print(panel)
        
    except ValueError as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1)
