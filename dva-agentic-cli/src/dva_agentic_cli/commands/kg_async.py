"""Asynchronous Knowledge Graph ingestion commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated
from pathlib import Path

from dva_agentic_cli.kg.async_ingest import (
    get_manager,
    JobStatus,
    IngestionJob
)

kg_async_app = typer.Typer(help="Asynchronous KG ingestion commands", rich_markup_mode=None)
console = Console()


@kg_async_app.command("submit")
def submit_ingestion(
    source: Annotated[
        str | None,
        typer.Option("--path", help="Direct path to data source"),
    ] = None,
    data_source: Annotated[
        str | None,
        typer.Option("--source", help="Data source name (from 'dva data create')"),
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
    wait: bool = typer.Option(
        False,
        help="Wait for job to complete before returning",
    ),
) -> None:
    """
    Submit an ingestion job for background processing.
    
    This allows you to ingest large datasets without blocking the CLI.
    Multiple jobs can run in parallel.
    
    Examples:
        # Submit single file
        dva kg async submit --path /path/to/file.pdf
        
        # Submit data source
        dva kg async submit --source my-dataset --provider both
        
        # Submit and wait for completion
        dva kg async submit --path /docs --wait
    """
    from dva_agentic_cli.commands.kg import resolve_data_source
    
    # Validate inputs
    if not source and not data_source:
        console.print("[red]✗ Error:[/red] Must specify either --path or --source")
        raise typer.Exit(1)
    
    if source and data_source:
        console.print("[red]✗ Error:[/red] Cannot specify both --path and --source")
        raise typer.Exit(1)
    
    # Validate provider
    if provider not in ["neo4j", "lightrag", "both"]:
        console.print(f"[red]✗ Error:[/red] Invalid provider '{provider}'. Must be: neo4j, lightrag, or both")
        raise typer.Exit(1)
    
    # Resolve source
    resolved_source = source
    source_type = "path"
    metadata = {}
    
    if data_source:
        console.print(f"[dim]Resolving data source '{data_source}'...[/dim]")
        resolved_source, src_type, src_metadata = resolve_data_source(data_source)
        source_type = "data_source"
        metadata = src_metadata or {}
        
        # Auto-detect format based on source type if not explicitly specified
        if not format:
            if src_type == "git":
                format = "git"
            elif src_type == "confluence":
                format = "confluence"
            # For "doc" type, let detect_format handle it
        
        console.print(f"[green]✓[/green] Resolved to: [cyan]{resolved_source}[/cyan]")
    
    # Submit job
    console.print(f"\n[bold]Submitting ingestion job...[/bold]")
    console.print(f"  Source: [cyan]{resolved_source}[/cyan]")
    console.print(f"  Provider: [cyan]{provider}[/cyan]")
    
    manager = get_manager()
    
    try:
        job = manager.submit_ingestion(
            source=resolved_source,
            source_type=source_type,
            format=format,
            provider=provider,
            extract_entities=extract_entities,
            build_relationships=build_relationships,
            recursive=recursive,
            metadata=metadata
        )
        
        console.print(f"\n[bold green]✓ Job submitted successfully![/bold green]")
        console.print(f"  Job ID: [cyan]{job.job_id}[/cyan]")
        console.print(f"  Status: [yellow]{job.status.value}[/yellow]")
        
        console.print(f"\n[dim]Track progress with:[/dim] dva kg async status {job.job_id}")
        console.print(f"[dim]List all jobs with:[/dim] dva kg async list")
        
        # Wait for completion if requested
        if wait:
            console.print(f"\n[bold]Waiting for job to complete...[/bold]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Processing...", total=None)
                
                try:
                    completed_job = manager.wait_for_job(job.job_id, timeout=3600)  # 1 hour timeout
                    
                    if completed_job.status == JobStatus.COMPLETED:
                        console.print(f"\n[bold green]✓ Job completed successfully![/bold green]")
                        if completed_job.result:
                            _display_result(completed_job.result)
                    elif completed_job.status == JobStatus.FAILED:
                        console.print(f"\n[bold red]✗ Job failed![/bold red]")
                        console.print(f"  Error: {completed_job.error}")
                        raise typer.Exit(1)
                    
                except TimeoutError:
                    console.print(f"\n[yellow]⚠ Job is still running after 1 hour[/yellow]")
                    console.print(f"  Check status with: dva kg async status {job.job_id}")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Failed to submit job:[/bold red] {str(e)}")
        raise typer.Exit(1)


@kg_async_app.command("status")
def job_status(
    job_id: Annotated[str, typer.Argument(help="Job ID to check")],
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
) -> None:
    """
    Check the status of an ingestion job.
    
    Example:
        dva kg async status abc123-def456
    """
    manager = get_manager()
    job = manager.get_job_status(job_id)
    
    if not job:
        console.print(f"[red]✗ Job not found:[/red] {job_id}")
        raise typer.Exit(1)
    
    # Display job info
    _display_job_info(job, verbose=verbose)


@kg_async_app.command("list")
def list_jobs(
    status: Annotated[
        str | None,
        typer.Option(help="Filter by status: pending, running, completed, failed, cancelled"),
    ] = None,
    limit: int = typer.Option(20, help="Maximum number of jobs to display"),
) -> None:
    """
    List ingestion jobs.
    
    Examples:
        # List all jobs
        dva kg async list
        
        # List only running jobs
        dva kg async list --status running
        
        # List last 50 jobs
        dva kg async list --limit 50
    """
    manager = get_manager()
    
    # Parse status filter
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
        console.print("[yellow]No jobs found[/yellow]")
        return
    
    # Create table
    table = Table(title=f"Ingestion Jobs ({len(jobs)} total)")
    table.add_column("Job ID", style="cyan")
    table.add_column("Source", style="white")
    table.add_column("Provider", style="magenta")
    table.add_column("Status", style="yellow")
    table.add_column("Created", style="dim")
    table.add_column("Duration", style="dim")
    
    for job in jobs:
        # Calculate duration
        if job.completed_at:
            duration = (job.completed_at - job.created_at).total_seconds()
            duration_str = f"{duration:.1f}s"
        elif job.started_at:
            from datetime import datetime
            duration = (datetime.utcnow() - job.started_at).total_seconds()
            duration_str = f"{duration:.1f}s (running)"
        else:
            duration_str = "-"
        
        # Status with emoji
        status_display = {
            JobStatus.PENDING: "⏳ Pending",
            JobStatus.RUNNING: "🔄 Running",
            JobStatus.COMPLETED: "✓ Completed",
            JobStatus.FAILED: "✗ Failed",
            JobStatus.CANCELLED: "⊘ Cancelled",
        }.get(job.status, job.status.value)
        
        # Truncate source
        source_display = job.source
        if len(source_display) > 40:
            source_display = "..." + source_display[-37:]
        
        table.add_row(
            job.job_id[:8] + "...",
            source_display,
            job.provider,
            status_display,
            job.created_at.strftime("%Y-%m-%d %H:%M"),
            duration_str
        )
    
    console.print(table)
    console.print(f"\n[dim]View details:[/dim] dva kg async status <job-id>")


@kg_async_app.command("cancel")
def cancel_job(
    job_id: Annotated[str, typer.Argument(help="Job ID to cancel")],
) -> None:
    """
    Cancel a pending or running job.
    
    Note: Running jobs cannot be immediately stopped,
    but will be marked for cancellation.
    
    Example:
        dva kg async cancel abc123-def456
    """
    manager = get_manager()
    
    if manager.cancel_job(job_id):
        console.print(f"[green]✓ Job cancelled:[/green] {job_id}")
    else:
        console.print(f"[red]✗ Cannot cancel job:[/red] {job_id}")
        console.print("[dim]Job may be already completed, failed, or not found[/dim]")
        raise typer.Exit(1)


@kg_async_app.command("cleanup")
def cleanup_jobs(
    days: int = typer.Option(30, help="Delete completed/failed jobs older than N days"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Clean up old completed and failed jobs.
    
    Example:
        dva kg async cleanup --days 7
    """
    if not force:
        confirm = typer.confirm(
            f"Delete completed/failed jobs older than {days} days?",
            default=False
        )
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    manager = get_manager()
    manager.queue.cleanup_old_jobs(days=days)
    
    console.print(f"[green]✓ Cleaned up jobs older than {days} days[/green]")


@kg_async_app.command("logs")
def view_logs(
    job_id: Annotated[str | None, typer.Argument(help="Job ID to filter logs")] = None,
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
) -> None:
    """
    View ingestion job logs.
    
    Examples:
        # View last 50 lines
        dva kg async logs
        
        # View last 100 lines
        dva kg async logs --lines 100
        
        # Filter by job ID
        dva kg async logs abc123-def456
        
        # Follow logs in real-time
        dva kg async logs --follow
    """
    from pathlib import Path
    
    log_file = Path.home() / ".dva-agentic" / "logs" / "async_ingestion.log"
    
    if not log_file.exists():
        console.print("[yellow]No logs found[/yellow]")
        console.print(f"[dim]Log file: {log_file}[/dim]")
        return
    
    if follow:
        # Use tail -f for following
        import subprocess
        console.print(f"[dim]Following logs from {log_file}[/dim]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        try:
            cmd = ["tail", "-f", str(log_file)]
            if job_id:
                cmd = ["tail", "-f", str(log_file), "|", "grep", job_id]
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped following logs[/dim]")
    else:
        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            
            # Filter by job_id if provided
            if job_id:
                all_lines = [line for line in all_lines if job_id in line]
            
            # Get last N lines
            display_lines = all_lines[-lines:]
            
            if not display_lines:
                if job_id:
                    console.print(f"[yellow]No logs found for job {job_id}[/yellow]")
                else:
                    console.print("[yellow]No logs found[/yellow]")
                return
            
            console.print(f"[dim]Showing last {len(display_lines)} lines from {log_file}[/dim]\n")
            
            for line in display_lines:
                # Color code by log level
                if "ERROR" in line:
                    console.print(f"[red]{line.rstrip()}[/red]")
                elif "WARNING" in line:
                    console.print(f"[yellow]{line.rstrip()}[/yellow]")
                elif "INFO" in line:
                    console.print(f"[dim]{line.rstrip()}[/dim]")
                else:
                    console.print(line.rstrip())


# Helper functions

def _display_job_info(job: IngestionJob, verbose: bool = False):
    """Display detailed job information."""
    # Status with color
    status_colors = {
        JobStatus.PENDING: "yellow",
        JobStatus.RUNNING: "blue",
        JobStatus.COMPLETED: "green",
        JobStatus.FAILED: "red",
        JobStatus.CANCELLED: "dim",
    }
    status_color = status_colors.get(job.status, "white")
    
    # Build info text
    info_lines = [
        f"[bold]Job ID:[/bold] {job.job_id}",
        f"[bold]Source:[/bold] {job.source}",
        f"[bold]Provider:[/bold] {job.provider}",
        f"[bold]Status:[/bold] [{status_color}]{job.status.value}[/{status_color}]",
        f"[bold]Created:[/bold] {job.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
    ]
    
    if job.started_at:
        info_lines.append(f"[bold]Started:[/bold] {job.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    if job.completed_at:
        info_lines.append(f"[bold]Completed:[/bold] {job.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        duration = (job.completed_at - job.created_at).total_seconds()
        info_lines.append(f"[bold]Duration:[/bold] {duration:.1f}s")
    
    if job.progress:
        stage = job.progress.get("stage", "unknown")
        info_lines.append(f"[bold]Progress:[/bold] {stage}")
    
    # Show worker info
    if job.metadata.get('worker_pid'):
        info_lines.append(f"[bold]Worker PID:[/bold] {job.metadata['worker_pid']}")
    if job.metadata.get('log_file'):
        info_lines.append(f"[bold]Log File:[/bold] {job.metadata['log_file']}")
    
    if job.error:
        info_lines.append(f"[bold red]Error:[/bold red] {job.error}")
    
    if verbose and job.metadata:
        info_lines.append(f"\n[bold]Metadata:[/bold]")
        for key, value in job.metadata.items():
            if key != 'future':  # Skip internal fields
                info_lines.append(f"  {key}: {value}")
    
    if job.result and verbose:
        info_lines.append(f"\n[bold]Results:[/bold]")
        _display_result(job.result, indent="  ")
    
    panel = Panel(
        "\n".join(info_lines),
        title="Ingestion Job Status",
        border_style=status_color
    )
    console.print(panel)


def _display_result(result: dict, indent: str = ""):
    """Display ingestion results."""
    for provider, data in result.items():
        console.print(f"{indent}[bold]{provider.upper()}:[/bold]")
        if isinstance(data, dict):
            for key, value in data.items():
                console.print(f"{indent}  {key}: [cyan]{value}[/cyan]")
        else:
            console.print(f"{indent}  {data}")
