"""Knowledge Graph ingestion commands (sync and async)."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated
from pathlib import Path

# Import async management functions
from agentic_cli.config import CLI_NAME
from agentic_cli.kg.async_ingest import (
    get_manager,
    JobStatus,
    IngestionJob
)

# Create the ingest app with async subcommand
ingest_app = typer.Typer(help="Data ingestion commands", rich_markup_mode=None)
async_app = typer.Typer(help="Async ingestion management", rich_markup_mode=None)

# Register async as subcommand of ingest
ingest_app.add_typer(async_app, name="async", help="Manage async ingestion jobs")

console = Console()


# ============================================================================
# ASYNC MANAGEMENT COMMANDS (dva kg ingest async ...)
# ============================================================================

@async_app.command("submit")
def submit_async_ingestion(
    source: Annotated[
        str | None,
        typer.Option("--path", help="Direct path to data source"),
    ] = None,
    data_source: Annotated[
        str | None,
        typer.Option("--source", help=f"Data source name (from \'{CLI_NAME} data create')"),
    ] = None,
    format: Annotated[
        str | None,
        typer.Option(help="Source format (auto-detected if not specified)"),
    ] = None,
    provider: Annotated[
        str,
        typer.Option(help="Target provider: neo4j, lightrag, or both"),
    ] = "lightrag",
    extract_entities: bool = typer.Option(
        True,
        help="Extract entities using LLM (Neo4j only)",
    ),
    build_relationships: bool = typer.Option(
        True,
        help="Build relationships between entities (Neo4j only)",
    ),
    recursive: bool = typer.Option(
        True,
        help="Recursively process subdirectories",
    ),
    detailed_analysis: bool = typer.Option(
        False,
        help="Perform detailed code analysis for Git repos",
    ),
    workspace: Annotated[
        str | None,
        typer.Option("--workspace", "-w", help="Target workspace (LightRAG only)"),
    ] = None,
) -> None:
    """Submit an ingestion job to run asynchronously."""
    from agentic_cli.commands.kg import load_data_config, resolve_data_source
    
    # Validate source specification
    if not source and not data_source:
        console.print("[red]✗ Error:[/red] Must specify either --path or --source")
        raise typer.Exit(1)
    
    if source and data_source:
        console.print("[red]✗ Error:[/red] Cannot specify both --path and --source")
        raise typer.Exit(1)
    
    # Resolve data source if specified
    resolved_source = source
    resolved_format = format
    source_metadata = None
    
    if data_source:
        console.print(f"[dim]Resolving data source '{data_source}'...[/dim]")
        try:
            resolved_source, source_type, source_metadata = resolve_data_source(data_source)
            
            # Auto-detect format based on source type
            if not resolved_format:
                if source_type == "confluence":
                    resolved_format = "confluence"
                elif source_type == "git":
                    resolved_format = "git"
            
            console.print(f"[green]✓[/green] Using source: [cyan]{resolved_source}[/cyan]")
        except Exception as e:
            console.print(f"[red]✗ Error resolving data source:[/red] {str(e)}")
            raise typer.Exit(1)
    
    if not resolved_source:
        console.print("[red]✗ Error:[/red] No source path specified")
        raise typer.Exit(1)
    
    # Submit job
    try:
        manager = get_manager()
        job = manager.submit_job(
            source=resolved_source,
            format=resolved_format,
            provider=provider,
            extract_entities=extract_entities,
            build_relationships=build_relationships,
            recursive=recursive,
            detailed_analysis=detailed_analysis,
            workspace=workspace,
            metadata=source_metadata or {}
        )
        
        console.print(f"\n[green]✓ Job submitted successfully[/green]")
        console.print(f"[cyan]Job ID:[/cyan] {job.job_id}")
        console.print(f"[cyan]Status:[/cyan] {job.status.value}")
        console.print(f"\n[dim]Check status:[/dim] dva kg ingest async status {job.job_id}")
        console.print(f"[dim]View all jobs:[/dim] dva kg ingest async list")
        
    except Exception as e:
        console.print(f"[red]✗ Error submitting job:[/red] {str(e)}")
        raise typer.Exit(1)


@async_app.command("status")
def job_status(
    job_id: Annotated[str, typer.Argument(help="Job ID to check")],
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
) -> None:
    """Check the status of an async ingestion job."""
    try:
        manager = get_manager()
        job = manager.get_job(job_id)
        
        if not job:
            console.print(f"[red]✗ Job not found:[/red] {job_id}")
            raise typer.Exit(1)
        
        _display_job_info(job, verbose=verbose)
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


@async_app.command("list")
def list_jobs(
    status: Annotated[
        str | None,
        typer.Option(help="Filter by status (pending, running, completed, failed, cancelled)"),
    ] = None,
    limit: int = typer.Option(20, help="Maximum number of jobs to show"),
) -> None:
    """List async ingestion jobs."""
    try:
        manager = get_manager()
        
        # Filter by status if specified
        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status.lower())
            except ValueError:
                console.print(f"[red]✗ Invalid status:[/red] {status}")
                console.print("[dim]Valid statuses: pending, running, completed, failed, cancelled[/dim]")
                raise typer.Exit(1)
        
        jobs = manager.list_jobs(status=status_filter, limit=limit)
        
        if not jobs:
            if status_filter:
                console.print(f"[yellow]No jobs found with status '{status_filter.value}'[/yellow]")
            else:
                console.print("[yellow]No jobs found[/yellow]")
            console.print(f"[dim]Submit a job:[/dim] dva kg ingest async submit --path <source>")
            return
        
        # Display jobs table
        table = Table(title=f"Async Ingestion Jobs ({len(jobs)})")
        table.add_column("Job ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Provider", style="dim")
        table.add_column("Source", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("Progress", justify="right")
        
        for job in jobs:
            # Status styling
            status_style = {
                JobStatus.PENDING: "yellow",
                JobStatus.RUNNING: "blue",
                JobStatus.COMPLETED: "green",
                JobStatus.FAILED: "red",
                JobStatus.CANCELLED: "dim"
            }.get(job.status, "white")
            
            # Truncate source path
            source_display = str(job.source)
            if len(source_display) > 40:
                source_display = "..." + source_display[-37:]
            
            # Progress display
            if job.status == JobStatus.RUNNING and job.progress:
                progress_display = f"{job.progress.get('current', 0)}/{job.progress.get('total', 0)}"
            elif job.status == JobStatus.COMPLETED:
                progress_display = "✓"
            elif job.status == JobStatus.FAILED:
                progress_display = "✗"
            else:
                progress_display = "-"
            
            table.add_row(
                job.job_id[:8],
                f"[{status_style}]{job.status.value}[/{status_style}]",
                job.provider,
                source_display,
                job.created_at.strftime("%Y-%m-%d %H:%M"),
                progress_display
            )
        
        console.print(table)
        console.print(f"\n[dim]View details:[/dim] dva kg ingest async status <job-id>")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


@async_app.command("cancel")
def cancel_job(
    job_id: Annotated[str, typer.Argument(help="Job ID to cancel")],
) -> None:
    """Cancel a running or pending async ingestion job."""
    try:
        manager = get_manager()
        success = manager.cancel_job(job_id)
        
        if success:
            console.print(f"[green]✓ Job cancelled:[/green] {job_id}")
        else:
            console.print(f"[yellow]⚠ Job not found or already completed:[/yellow] {job_id}")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


@async_app.command("cleanup")
def cleanup_jobs(
    days: int = typer.Option(30, help="Delete completed/failed jobs older than N days"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Clean up old completed/failed jobs."""
    try:
        manager = get_manager()
        
        if not force:
            confirm = typer.confirm(
                f"Delete completed/failed jobs older than {days} days?",
                default=False
            )
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)
        
        count = manager.cleanup_old_jobs(days=days)
        console.print(f"[green]✓ Cleaned up {count} old jobs[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


@async_app.command("logs")
def view_logs(
    job_id: Annotated[str | None, typer.Argument(help="Job ID to filter logs")] = None,
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
) -> None:
    """View logs for async ingestion jobs."""
    try:
        manager = get_manager()
        
        if job_id:
            # Show logs for specific job
            job = manager.get_job(job_id)
            if not job:
                console.print(f"[red]✗ Job not found:[/red] {job_id}")
                raise typer.Exit(1)
            
            console.print(f"[cyan]Logs for job {job_id}:[/cyan]\n")
            
            if job.logs:
                for log_entry in job.logs[-lines:]:
                    console.print(log_entry)
            else:
                console.print("[dim]No logs available[/dim]")
        else:
            # Show recent logs from all jobs
            console.print(f"[cyan]Recent logs (last {lines} entries):[/cyan]\n")
            # Implementation would aggregate logs from recent jobs
            console.print("[dim]Specify a job ID to view specific logs[/dim]")
            
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _display_job_info(job: IngestionJob, verbose: bool = False) -> None:
    """Display detailed job information."""
    # Status styling
    status_style = {
        JobStatus.PENDING: "yellow",
        JobStatus.RUNNING: "blue",
        JobStatus.COMPLETED: "green",
        JobStatus.FAILED: "red",
        JobStatus.CANCELLED: "dim"
    }.get(job.status, "white")
    
    # Build info panel
    info_lines = [
        f"[cyan]Job ID:[/cyan] {job.job_id}",
        f"[cyan]Status:[/cyan] [{status_style}]{job.status.value}[/{status_style}]",
        f"[cyan]Provider:[/cyan] {job.provider}",
        f"[cyan]Source:[/cyan] {job.source}",
        f"[cyan]Format:[/cyan] {job.format or 'auto-detect'}",
        f"[cyan]Created:[/cyan] {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    
    if job.started_at:
        info_lines.append(f"[cyan]Started:[/cyan] {job.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if job.completed_at:
        info_lines.append(f"[cyan]Completed:[/cyan] {job.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        duration = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
        info_lines.append(f"[cyan]Duration:[/cyan] {duration:.1f}s")
    
    if job.workspace:
        info_lines.append(f"[cyan]Workspace:[/cyan] {job.workspace}")
    
    if job.progress:
        current = job.progress.get('current', 0)
        total = job.progress.get('total', 0)
        if total > 0:
            pct = (current / total) * 100
            info_lines.append(f"[cyan]Progress:[/cyan] {current}/{total} ({pct:.1f}%)")
    
    if job.error:
        info_lines.append(f"[red]Error:[/red] {job.error}")
    
    if verbose and job.metadata:
        info_lines.append(f"\n[cyan]Metadata:[/cyan]")
        for key, value in job.metadata.items():
            info_lines.append(f"  {key}: {value}")
    
    panel = Panel(
        "\n".join(info_lines),
        title=f"Job {job.job_id[:8]}",
        border_style=status_style
    )
    console.print(panel)
    
    # Show recent logs if available
    if verbose and job.logs:
        console.print(f"\n[cyan]Recent logs:[/cyan]")
        for log_entry in job.logs[-10:]:
            console.print(f"  {log_entry}")
