"""Knowledge Graph commands for dva-agentic-cli."""

import json
from pathlib import Path
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_cli.tracker import record_activity

kg_app = typer.Typer(help="Knowledge Graph management commands", rich_markup_mode=None)
console = Console()

# Register workspace subcommand
from agentic_cli.commands.kg_workspace import workspace_app
from agentic_cli.config import CLI_NAME
kg_app.add_typer(workspace_app, name="workspace", help="Workspace management (LightRAG only)")

# Configuration file location (shared with data commands)
CONFIG_DIR = Path.home() / ".dva-agentic"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_data_config() -> dict:
    """Load data configuration from file."""
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text())
        return config.get("data", {})
    return {}


def resolve_data_source(source_name: str) -> tuple[str, str, dict]:
    """
    Resolve a data source name to its location, type, and metadata.
    
    Args:
        source_name: Name of the data source configured via f'{CLI_NAME} data create'
    
    Returns:
        (location, source_type, metadata) tuple
        - location: URL or path to the data source
        - source_type: Type of source (doc, confluence, git)
        - metadata: Dict with additional info (for git: name, domain, purpose, branch, tag)
    
    Raises:
        typer.Exit: If source not found or invalid
    """
    data_config = load_data_config()
    
    if not data_config.get("sources"):
        console.print("[red]✗ Error:[/red] No data sources configured.")
        console.print("[dim]Use f'{CLI_NAME} data create' to configure data sources first.[/dim]")
        raise typer.Exit(1)
    
    # Find the source
    for source in data_config["sources"]:
        if source["name"] == source_name:
            location = source["location"]
            source_type = source["type"]
            
            # Prepare metadata
            metadata = {
                "name": source.get("name", ""),
                "description": source.get("description", ""),
                "tags": source.get("tags", []),
            }
            
            # Handle git sources - extract Git-specific metadata
            if source_type == "git":
                git_info = source.get("git", {})
                metadata.update({
                    "domain": ", ".join(source.get("tags", [])),  # Use tags as domain
                    "purpose": source.get("description", ""),
                    "branch": git_info.get("branch"),
                    "tag": git_info.get("tag"),
                })
                console.print(f"[cyan]ℹ[/cyan] Git repository detected: {source['name']}")
                if git_info.get("branch"):
                    console.print(f"  Branch: [cyan]{git_info['branch']}[/cyan]")
                if git_info.get("tag"):
                    console.print(f"  Tag: [cyan]{git_info['tag']}[/cyan]")
            
            return location, source_type, metadata
    
    # Source not found
    console.print(f"[red]✗ Error:[/red] Data source '{source_name}' not found.")
    console.print("[dim]Use f'{CLI_NAME} data list' to see available sources.[/dim]")
    raise typer.Exit(1)


def validate_neo4j_connection(skip_check: bool = False) -> bool:
    """
    Validate Neo4j connection before executing commands.
    
    Args:
        skip_check: Skip validation check
    
    Returns:
        True if validation passes, False otherwise
    """
    if skip_check:
        return True
    
    from agentic_cli.kg.validation import (
        check_neo4j_availability,
        get_setup_instructions,
        validate_prerequisites,
    )
    
    # Quick check for Neo4j connection
    is_available, message = check_neo4j_availability()
    
    if is_available:
        return True
    
    # If not available, show detailed diagnostics
    console.print("\n[bold red]✗ Neo4j is not available[/bold red]")
    console.print(f"  {message}\n")
    
    # Run full prerequisite check
    console.print("[bold]Running diagnostics...[/bold]\n")
    results = validate_prerequisites()
    
    # Display results
    table = Table(title="Prerequisites Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Message", style="yellow")
    
    for component, (status, msg) in results.items():
        status_icon = "[green]✓[/green]" if status else "[red]✗[/red]"
        component_name = component.replace("_", " ").title()
        table.add_row(component_name, status_icon, msg)
    
    console.print(table)
    console.print()
    
    # Show setup instructions
    console.print(Panel(
        get_setup_instructions(results),
        title="[bold]Setup Instructions[/bold]",
        border_style="yellow",
    ))
    
    return False


@kg_app.command()
def check(
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Provider to check (neo4j, lightrag). Defaults to configured provider or lightrag.",
    ),
) -> None:
    """
    Check prerequisites and provider availability.
    
    Validates prerequisites for Neo4j or LightRAG based on configured or specified provider.
    """
    from agentic_cli.kg.config import KGConfig
    
    # Determine which provider to check
    if provider is None:
        try:
            config = KGConfig.load()
            provider = config.provider
            console.print(f"[dim]Using configured provider: {provider}[/dim]\n")
        except:
            provider = "lightrag"
            console.print(f"[dim]No configuration found, checking default provider: {provider}[/dim]\n")
    
    console.print(f"[bold]Checking {provider.upper()} Prerequisites...[/bold]\n")
    
    if provider == "neo4j":
        _check_neo4j()
    elif provider == "lightrag":
        _check_lightrag()
    else:
        console.print(f"[red]✗ Unknown provider:[/red] {provider}")
        console.print("[dim]Valid providers: neo4j, lightrag[/dim]")
        raise typer.Exit(1)


def _check_neo4j() -> None:
    """Check Neo4j prerequisites."""
    from agentic_cli.kg.validation import (
        get_setup_instructions,
        validate_prerequisites,
    )
    
    results = validate_prerequisites()
    
    # Display results
    table = Table(title="Neo4j Prerequisites Check")
    table.add_column("Component", style="cyan", width=25)
    table.add_column("Status", style="white", width=10)
    table.add_column("Message", style="yellow")
    
    all_passed = True
    for component, (status, msg) in results.items():
        status_icon = "[green]✓[/green]" if status else "[red]✗[/red]"
        component_name = component.replace("_", " ").title()
        table.add_row(component_name, status_icon, msg)
        
        if not status:
            all_passed = False
    
    console.print(table)
    console.print()
    
    if all_passed:
        console.print("[bold green]✓ All prerequisites are met![/bold green]")
        console.print("\nYou can now use Neo4j knowledge graph commands:")
        console.print("  dva kg ingest submit --path <source>")
        console.print("  dva kg query <query>")
        console.print("  dva kg visualize")
    else:
        console.print("[bold yellow]⚠ Some prerequisites are not met[/bold yellow]")
        console.print(Panel(
            get_setup_instructions(results),
            title="[bold]Setup Instructions[/bold]",
            border_style="yellow",
        ))


def _check_lightrag() -> None:
    """Check LightRAG prerequisites."""
    from agentic_cli.kg.lightrag_client import LightRAGClient
    from agentic_cli.kg.config import KGConfig
    
    # Load config to get LightRAG URL
    try:
        config = KGConfig.load()
        lightrag_url = config.lightrag_url
    except:
        lightrag_url = "http://localhost:8001"
    
    # Display results
    table = Table(title="LightRAG Prerequisites Check")
    table.add_column("Component", style="cyan", width=25)
    table.add_column("Status", style="white", width=10)
    table.add_column("Message", style="yellow")
    
    all_passed = True
    
    # Check LightRAG server
    try:
        client = LightRAGClient(base_url=lightrag_url, timeout=5.0)
        health = client.health_check()
        
        if health.get("status") == "healthy":
            table.add_row(
                "LightRAG Server",
                "[green]✓[/green]",
                f"Connected to {lightrag_url}"
            )
            
            # Show additional info
            working_dir = health.get("working_dir", "N/A")
            vector_store = health.get("vector_store", "N/A")
            graph_store = health.get("graph_store", "N/A")
            
            table.add_row("Working Directory", "[green]✓[/green]", working_dir)
            table.add_row("Vector Store", "[green]✓[/green]", vector_store)
            table.add_row("Graph Store", "[green]✓[/green]", graph_store)
        else:
            table.add_row(
                "LightRAG Server",
                "[yellow]⚠[/yellow]",
                f"Server responded but status: {health.get('status')}"
            )
            all_passed = False
            
        client.close()
        
    except Exception as e:
        table.add_row(
            "LightRAG Server",
            "[red]✗[/red]",
            f"Cannot connect to {lightrag_url}: {str(e)}"
        )
        all_passed = False
    
    # Check workspace configuration
    try:
        config = KGConfig.load()
        workspace = config.workspace
        workspace_dir = config.get_workspace_dir()
        
        from pathlib import Path
        if Path(workspace_dir).exists():
            table.add_row(
                "Workspace",
                "[green]✓[/green]",
                f"{workspace} ({workspace_dir})"
            )
        else:
            table.add_row(
                "Workspace",
                "[yellow]⚠[/yellow]",
                f"{workspace} directory not found"
            )
    except:
        table.add_row(
            "Workspace",
            "[yellow]⚠[/yellow]",
            "No workspace configured"
        )
    
    console.print(table)
    console.print()
    
    if all_passed:
        console.print("[bold green]✓ All prerequisites are met![/bold green]")
        console.print("\nYou can now use LightRAG knowledge graph commands:")
        console.print("  dva kg ingest submit --path <source>")
        console.print("  dva kg ingest submit --path <source> --async")
        console.print("  dva kg query <query>")
        console.print("  dva kg search <text>")
        console.print("  dva kg workspace list")
    else:
        console.print("[bold yellow]⚠ Some prerequisites are not met[/bold yellow]")
        console.print("\n[bold]Setup Instructions:[/bold]")
        console.print("1. Start LightRAG server:")
        console.print(f"   cd lightrag-infrastructure && ./scripts/start.sh")
        console.print("\n2. Initialize configuration:")
        console.print(f"   dva kg init --provider lightrag --lightrag-url {lightrag_url}")
        console.print("\n3. Create a workspace:")
        console.print("   dva kg workspace create default")


@kg_app.command()
def init(
    provider: str = typer.Option(
        default="neo4j",
        help="Graph database provider (neo4j, lightrag)",
    ),
    uri: str | None = typer.Option(
        default=None,
        help="Neo4j connection URI (e.g., bolt://localhost:7687)",
    ),
    username: str | None = typer.Option(
        default=None,
        help="Neo4j username",
    ),
    password: str | None = typer.Option(
        default=None,
        help="Neo4j password",
    ),
    lightrag_url: str | None = typer.Option(
        default=None,
        help="LightRAG API URL (e.g., http://localhost:8001)",
    ),
    lightrag_timeout: float | None = typer.Option(
        default=None,
        help="LightRAG request timeout in seconds",
    ),
    embeddings: str = typer.Option(
        default="vertex-ai",
        help="Embeddings provider (vertex-ai, openai, none)",
    ),
    confluence_url: str | None = typer.Option(
        default=None,
        help="Confluence base URL (e.g., https://confluence.company.com)",
    ),
    confluence_username: str | None = typer.Option(
        default=None,
        help="Confluence username/email",
    ),
    confluence_token: str | None = typer.Option(
        default=None,
        help="Confluence API token",
    ),
) -> None:
    """
    Initialize knowledge graph configuration.
    
    Sets up connection to graph database and configures embeddings provider.
    """
    from agentic_cli.kg.config import KGConfig
    
    config = KGConfig.load()
    
    # Update configuration
    config.provider = provider
    if uri:
        config.neo4j_uri = uri
    if username:
        config.neo4j_username = username
    if password:
        config.neo4j_password = password
    if lightrag_url:
        config.lightrag_url = lightrag_url
    if lightrag_timeout:
        config.lightrag_timeout = lightrag_timeout
    config.embeddings_provider = embeddings
    
    # Update Confluence configuration
    if confluence_url:
        config.confluence_url = confluence_url
    if confluence_username:
        config.confluence_username = confluence_username
    if confluence_token:
        config.confluence_api_token = confluence_token
    
    # Save configuration
    config.save()
    
    console.print("[bold green]✓[/bold green] Knowledge graph configuration saved")
    console.print(f"  Provider: [cyan]{provider}[/cyan]")
    if provider == "neo4j":
        console.print(f"  URI: [cyan]{config.neo4j_uri}[/cyan]")
        console.print(f"  Username: [cyan]{config.neo4j_username}[/cyan]")
    elif provider == "lightrag":
        console.print(f"  URL: [cyan]{config.lightrag_url}[/cyan]")
        console.print(f"  Timeout: [cyan]{config.lightrag_timeout}s[/cyan]")
    console.print(f"  Embeddings: [cyan]{embeddings}[/cyan]")
    
    # Validate connection based on provider
    if provider == "neo4j":
        console.print("\n[bold]Validating Neo4j connection...[/bold]")
        
        from agentic_cli.kg.validation import check_neo4j_availability
        
        is_available, message = check_neo4j_availability(
            uri=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password,
        )
        
        if is_available:
            console.print(f"[bold green]✓[/bold green] {message}")
        else:
            console.print(f"[bold yellow]⚠[/bold yellow] {message}")
            console.print("\n[dim]Configuration saved, but Neo4j is not accessible.[/dim]")
            console.print("[dim]fRun '{CLI_NAME} kg config --show' to verify settings.[/dim]")
    elif provider == "lightrag":
        console.print("\n[bold]Validating LightRAG connection...[/bold]")
        
        from agentic_cli.kg.lightrag_client import check_lightrag_availability
        
        is_available, message = check_lightrag_availability(base_url=config.lightrag_url)
        
        if is_available:
            console.print(f"[bold green]✓[/bold green] {message}")
        else:
            console.print(f"[bold yellow]⚠[/bold yellow] {message}")
            console.print("\n[dim]Configuration saved, but LightRAG is not accessible.[/dim]")
            console.print("[dim]Make sure LightRAG infrastructure is running.[/dim]")


@kg_app.command()
def config(
    show: bool = typer.Option(
        default=False,
        help="Show current configuration",
    ),
    reset: bool = typer.Option(
        default=False,
        help="Reset configuration to defaults",
    ),
) -> None:
    """
    Manage knowledge graph configuration.
    """
    from agentic_cli.kg.config import KGConfig
    
    if reset:
        config_path = Path.home() / ".dva-agentic" / "kg-config.json"
        if config_path.exists():
            config_path.unlink()
            console.print("[bold green]✓[/bold green] Configuration reset")
        else:
            console.print("[yellow]No configuration found[/yellow]")
        return
    
    if show:
        config = KGConfig.load()
        
        table = Table(title="Knowledge Graph Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Provider", config.provider)
        if config.provider == "neo4j":
            table.add_row("Neo4j URI", config.neo4j_uri)
            table.add_row("Neo4j Username", config.neo4j_username)
            table.add_row("Neo4j Password", "***" if config.neo4j_password else "Not set")
        elif config.provider == "lightrag":
            table.add_row("LightRAG URL", config.lightrag_url)
            table.add_row("LightRAG Timeout", f"{config.lightrag_timeout}s")
        table.add_row("Embeddings Provider", config.embeddings_provider)
        
        # Show Vertex AI configuration
        if config.embeddings_provider == "vertex-ai":
            table.add_row("Vertex AI Project", config.google_project_id or "Not set")
            table.add_row("Vertex AI Location", config.google_location)
            table.add_row("Vertex AI Model", config.vertex_ai_model)
        
        # Show Confluence configuration if set
        if config.confluence_url:
            table.add_row("Confluence URL", config.confluence_url)
            table.add_row("Confluence Username", config.confluence_username or "Not set")
            table.add_row("Confluence Token", "***" if config.confluence_api_token else "Not set")
        
        console.print(table)


# Create ingest command group
ingest_app = typer.Typer(help="Data ingestion commands", rich_markup_mode=None)
kg_app.add_typer(ingest_app, name="ingest")


@ingest_app.command("submit")
def ingest_submit(
    data_source: str | None = typer.Option(
        None,
        "--source",
        help=f"Name of data source configured via \'{CLI_NAME} data create'",
    ),
    source: str = typer.Option(
        "",
        "--path",
        help="Direct path to data source, directory, or URL",
    ),
    format: str | None = typer.Option(
        default=None,
        help="Source format (pdf, text, csv, json, confluence, directory). Auto-detected if not specified.",
    ),
    workspace: str | None = typer.Option(
        None,
        "--workspace", "-w",
        help="Target workspace (LightRAG only, uses active workspace if not specified)",
    ),
    extract_entities: bool = typer.Option(
        default=True,
        help="Extract entities using LLM",
    ),
    no_extract_entities: bool = typer.Option(
        default=False,
        help="Don't extract entities using LLM",
    ),
    build_relationships: bool = typer.Option(
        default=True,
        help="Build relationships between entities",
    ),
    no_build_relationships: bool = typer.Option(
        default=False,
        help="Don't build relationships between entities",
    ),
    recursive: bool = typer.Option(
        default=True,
        help="Recursively process subdirectories (for directory ingestion)",
    ),
    no_recursive: bool = typer.Option(
        default=False,
        help="Don't recursively process subdirectories",
    ),
    detailed_analysis: bool = typer.Option(
        default=False,
        help="Perform detailed code analysis for Git repos (functions, classes)",
    ),
    no_detailed_analysis: bool = typer.Option(
        default=False,
        help="Skip detailed code analysis, use only gitingest digest (faster, default)",
    ),
    skip_validation: bool = typer.Option(
        default=False,
        help="Skip connection validation",
        hidden=True,
    ),
    async_mode: bool = typer.Option(
        False,
        "--async",
        help="Run ingestion asynchronously in background",
    ),
) -> None:
    """
    Submit data for ingestion into the knowledge graph.
    
    You can specify a source in two ways:
    1. Direct path/URL: dva kg ingest submit --path /path/to/file.pdf
    2. Data source name: dva kg ingest submit --source my-dataset
    
    Data sources are configured using f'{CLI_NAME} data create' command.
    
    Supports: PDF, text files, CSV, JSON, Confluence, and directories.
    
    For directories, all supported files (.pdf, .txt, .md, .csv, .json) will be processed.
    
    Use --async flag to run ingestion in background:
      dva kg ingest submit --path /data --async
    """
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.async_ingest import get_manager
    
    # Load configuration to determine provider
    config = KGConfig.load()
    
    # Handle workspace parameter
    original_workspace = None
    if workspace:
        # Workspace specified - validate it's only for LightRAG
        if config.provider != "lightrag":
            console.print(
                f"[bold red]✗ Error:[/bold red] Workspaces are only supported for LightRAG provider."
            )
            console.print(f"[dim]Current provider: {config.provider}[/dim]")
            console.print(f"[dim]Remove --workspace flag or switch to LightRAG provider[/dim]")
            raise typer.Exit(1)
        
        # Validate workspace exists
        from agentic_cli.kg.workspace import WorkspaceManager
        manager = WorkspaceManager(config.workspace_base_dir)
        
        if not manager.workspace_exists(workspace):
            console.print(f"[bold red]✗ Error:[/bold red] Workspace '{workspace}' does not exist")
            console.print(f"[dim]Create it with: dva kg workspace create {workspace}[/dim]")
            raise typer.Exit(1)
        
        # Temporarily switch to specified workspace
        original_workspace = config.workspace
        config.workspace = workspace
        console.print(f"[cyan]ℹ[/cyan] Using workspace: {workspace}")
    elif config.provider == "lightrag":
        # Show active workspace for LightRAG
        console.print(f"[dim]Active workspace: {config.workspace}[/dim]")
    
    # Validate connection based on provider
    if config.provider == "neo4j":
        if not validate_neo4j_connection(skip_check=skip_validation):
            raise typer.Exit(1)
    elif config.provider == "lightrag":
        if not skip_validation:
            from agentic_cli.kg.lightrag_client import check_lightrag_availability
            is_available, message = check_lightrag_availability(base_url=config.lightrag_url)
            if not is_available:
                console.print(f"[bold red]✗ LightRAG is not available:[/bold red] {message}")
                console.print("[dim]Make sure LightRAG infrastructure is running.[/dim]")
                raise typer.Exit(1)
    
    # Resolve source - either from data source name or direct path
    resolved_source = source
    resolved_format = format
    source_metadata = None
    
    if data_source and source:
        console.print("[red]✗ Error:[/red] Cannot specify both --source and --path. Use one or the other.")
        raise typer.Exit(1)
    
    if data_source:
        # Resolve data source name to location, type, and metadata
        console.print(f"[dim]Resolving data source '{data_source}'...[/dim]")
        resolved_source, source_type, source_metadata = resolve_data_source(data_source)
        
        # Auto-detect format based on source type if not specified
        if not resolved_format:
            if source_type == "doc":
                # For doc sources, we'll let the ingest function auto-detect
                pass
            elif source_type == "confluence":
                resolved_format = "confluence"
            elif source_type == "git":
                resolved_format = "git"
        
        console.print(f"[green]✓[/green] Using source: [cyan]{resolved_source}[/cyan] (type: {source_type})")
    
    elif source:
        resolved_source = source
    else:
        console.print("[red]✗ Error:[/red] Must specify either --source (data source name) or --path (direct path).")
        console.print("[dim]Use f'{CLI_NAME} data list' to see configured data sources.[/dim]")
        raise typer.Exit(1)
    
    # Handle negation flags
    if no_extract_entities:
        extract_entities = False
    if no_build_relationships:
        build_relationships = False
    if no_recursive:
        recursive = False
    if no_detailed_analysis:
        detailed_analysis = False
    
    # Handle async mode - submit job and return
    if async_mode:
        try:
            manager = get_manager()
            job = manager.submit_ingestion(
                source=resolved_source,
                source_type="path" if not data_source else "data_source",
                format=resolved_format,
                provider=config.provider,
                extract_entities=extract_entities,
                build_relationships=build_relationships,
                recursive=recursive,
                detailed_analysis=detailed_analysis,
                workspace=workspace,
                metadata=source_metadata or {}
            )
            
            record_activity(
                command="kg", subcommand="ingest-submit",
                args={"source": data_source or resolved_source, "async": True, "provider": config.provider},
                details={"job_id": job.job_id},
            )

            console.print(f"\n[green]\u2713 Ingestion job submitted (async)[/green]")
            console.print(f"[cyan]Job ID:[/cyan] {job.job_id}")
            console.print(f"[cyan]Status:[/cyan] {job.status.value}")
            console.print(f"[cyan]Provider:[/cyan] {config.provider}")
            if workspace:
                console.print(f"[cyan]Workspace:[/cyan] {workspace}")
            console.print(f"\n[dim]Check status:[/dim] dva kg ingest list")
            console.print(f"[dim]View details:[/dim] dva kg ingest status {job.job_id[:8]}")
            return
            
        except Exception as e:
            console.print(f"[red]\u2717 Error submitting async job:[/red] {str(e)}")
            raise typer.Exit(1)
    
    # Track sync ingestion operation
    manager = get_manager()
    job = manager.queue.create_job(
        source=resolved_source,
        source_type="path" if not data_source else "data_source",
        format=resolved_format,
        provider=config.provider,
        is_async=False,
        workspace=workspace,
        metadata=source_metadata or {}
    )
    job.status = "running"
    job.started_at = __import__('datetime').datetime.utcnow()
    manager.queue.update_job(job.job_id, status=job.status, started_at=job.started_at)
    
    # Route to appropriate ingestion based on provider
    if config.provider == "neo4j":
        from agentic_cli.kg.ingest import ingest_data
        
        with console.status(f"[bold green]Ingesting data from {resolved_source}..."):
            try:
                result = ingest_data(
                    source=resolved_source,
                    format=resolved_format,
                    persona=None,  # Auto-detect based on format
                    metadata=source_metadata,
                    extract_entities=extract_entities,
                    build_relationships=build_relationships,
                    recursive=recursive,
                    detailed_analysis=detailed_analysis,
                )
                
                record_activity(
                    command="kg", subcommand="ingest-submit",
                    args={"source": data_source or resolved_source, "async": False, "provider": config.provider},
                    details={"entities": result['entities_count'], "relationships": result['relationships_count']},
                )

                console.print(f"[bold green]\u2713[/bold green] Successfully ingested data")
                console.print(f"  Source: [cyan]{result['source']}[/cyan]")
                console.print(f"  Format: [cyan]{result['format']}[/cyan]")
                console.print(f"  Entities: [cyan]{result['entities_count']}[/cyan]")
                console.print(f"  Relationships: [cyan]{result['relationships_count']}[/cyan]")
                
                # Mark job as completed
                job.status = "completed"
                job.completed_at = __import__('datetime').datetime.utcnow()
                job.result = result
                manager.queue.update_job(job.job_id, status=job.status, completed_at=job.completed_at, result=result)
                
            except Exception as e:
                # Mark job as failed
                job.status = "failed"
                job.error = str(e)
                job.completed_at = __import__('datetime').datetime.utcnow()
                manager.queue.update_job(job.job_id, status=job.status, error=job.error, completed_at=job.completed_at)
                
                console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
                raise typer.Exit(1)
    
    elif config.provider == "lightrag":
        from agentic_cli.kg.lightrag_client import LightRAGClient
        from pathlib import Path
        
        with console.status(f"[bold green]Ingesting data into LightRAG from {resolved_source}..."):
            try:
                # Use extended timeout for Git ingestion (can have thousands of documents)
                timeout = 600.0 if resolved_format == "git" else config.lightrag_timeout
                client = LightRAGClient(base_url=config.lightrag_url, timeout=timeout)
                
                # Handle Git repository ingestion
                if resolved_format == "git":
                    from agentic_cli.kg.parsers import parse_git_repository
                    
                    # Parse Git repository
                    git_metadata = source_metadata or {}
                    branch = git_metadata.get("branch")
                    tag = git_metadata.get("tag")
                    repo_metadata = {
                        "name": git_metadata.get("name", ""),
                        "domain": git_metadata.get("domain", ""),
                        "purpose": git_metadata.get("purpose", ""),
                    }
                    
                    documents = parse_git_repository(
                        repo_url=resolved_source,
                        branch=branch,
                        tag=tag,
                        repo_metadata=repo_metadata
                    )
                    
                    # Insert documents with persona metadata (with progress tracking)
                    total_docs = len(documents)
                    total_chars = 0
                    batch_size = 50  # Process in batches for better feedback
                    
                    console.print(f"[dim]Inserting {total_docs} documents in batches of {batch_size}...[/dim]")
                    
                    for i, doc in enumerate(documents, 1):
                        # Add persona to metadata
                        doc_metadata = doc.get("metadata", {})
                        doc_metadata["persona"] = "developer"
                        
                        try:
                            result = client.insert(
                                text=doc["content"],
                                metadata=doc_metadata
                            )
                            total_chars += result.get('characters', 0)
                            
                            # Progress feedback every batch
                            if i % batch_size == 0 or i == total_docs:
                                console.print(f"  [dim]Progress: {i}/{total_docs} documents ({i*100//total_docs}%)[/dim]")
                        
                        except Exception as e:
                            console.print(f"  [yellow]⚠ Skipped document {i}: {str(e)[:50]}[/yellow]")
                            continue
                    
                    console.print(f"[bold green]✓[/bold green] Successfully ingested Git repository")
                    console.print(f"  Repository: [cyan]{repo_metadata.get('name', 'unknown')}[/cyan]")
                    console.print(f"  Documents: [cyan]{total_docs}[/cyan]")
                    console.print(f"  Total characters: [cyan]{total_chars}[/cyan]")
                
                # Handle file or directory ingestion
                elif Path(resolved_source).exists():
                    source_path = Path(resolved_source)
                    if source_path.is_file():
                        result = client.insert_file(str(source_path))
                        console.print(f"[bold green]✓[/bold green] Successfully ingested file")
                        console.print(f"  Source: [cyan]{resolved_source}[/cyan]")
                        console.print(f"  Characters: [cyan]{result.get('characters', 0)}[/cyan]")
                    elif source_path.is_dir():
                        # Process directory recursively
                        total_files = 0
                        total_chars = 0
                        extensions = ['.txt', '.md', '.pdf', '.json', '.csv']
                        
                        for ext in extensions:
                            pattern = '**/*' + ext if recursive else '*' + ext
                            for file_path in source_path.glob(pattern):
                                try:
                                    result = client.insert_file(str(file_path))
                                    total_files += 1
                                    total_chars += result.get('characters', 0)
                                    console.print(f"  [dim]Ingested: {file_path.name}[/dim]")
                                except Exception as e:
                                    console.print(f"  [yellow]⚠ Skipped {file_path.name}: {e}[/yellow]")
                        
                        console.print(f"[bold green]✓[/bold green] Successfully ingested directory")
                        console.print(f"  Files: [cyan]{total_files}[/cyan]")
                        console.print(f"  Total characters: [cyan]{total_chars}[/cyan]")
                else:
                    # Assume it's raw text or URL
                    result = client.insert(resolved_source)
                    console.print(f"[bold green]✓[/bold green] Successfully ingested text")
                    console.print(f"  Characters: [cyan]{result.get('characters', 0)}[/cyan]")
                
                client.close()
                
                # Mark job as completed
                job.status = "completed"
                job.completed_at = __import__('datetime').datetime.utcnow()
                manager.queue.update_job(job.job_id, status=job.status, completed_at=job.completed_at)
                
            except Exception as e:
                # Mark job as failed
                job.status = "failed"
                job.error = str(e)
                job.completed_at = __import__('datetime').datetime.utcnow()
                manager.queue.update_job(job.job_id, status=job.status, error=job.error, completed_at=job.completed_at)
                
                console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
                raise typer.Exit(1)


@ingest_app.command("list")
def ingest_list(
    status: str | None = typer.Option(
        None,
        help="Filter by status (pending, running, completed, failed, cancelled)",
    ),
    async_only: bool = typer.Option(
        False,
        "--async-only",
        help="Show only async operations",
    ),
    sync_only: bool = typer.Option(
        False,
        "--sync-only",
        help="Show only sync operations",
    ),
    limit: int = typer.Option(20, help="Maximum number of operations to show"),
) -> None:
    """List all ingestion operations (sync and async)."""
    from agentic_cli.kg.async_ingest import get_manager, JobStatus
    
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
        
        # Filter by sync/async
        if async_only:
            jobs = [j for j in jobs if j.is_async]
        elif sync_only:
            jobs = [j for j in jobs if not j.is_async]
        
        if not jobs:
            filter_desc = []
            if status_filter:
                filter_desc.append(f"status '{status_filter.value}'")
            if async_only:
                filter_desc.append("async only")
            elif sync_only:
                filter_desc.append("sync only")
            
            if filter_desc:
                console.print(f"[yellow]No operations found with {' and '.join(filter_desc)}[/yellow]")
            else:
                console.print("[yellow]No operations found[/yellow]")
            console.print(f"[dim]Run an ingestion:[/dim] dva kg ingest submit --path <source>")
            return
        
        # Display jobs table
        table = Table(title=f"Ingestion Operations ({len(jobs)})")
        table.add_column("Job ID", style="cyan", no_wrap=True)
        table.add_column("Mode", style="dim")
        table.add_column("Status", style="bold")
        table.add_column("Provider", style="dim")
        table.add_column("Source", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("Duration", justify="right")
        
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
            if len(source_display) > 35:
                source_display = "..." + source_display[-32:]
            
            # Duration display
            if job.completed_at and job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                duration_display = f"{duration:.1f}s"
            elif job.status == JobStatus.RUNNING and job.started_at:
                from datetime import datetime
                duration = (datetime.utcnow() - job.started_at).total_seconds()
                duration_display = f"{duration:.0f}s..."
            else:
                duration_display = "-"
            
            table.add_row(
                job.job_id[:8],
                "async" if job.is_async else "sync",
                f"[{status_style}]{job.status.value}[/{status_style}]",
                job.provider,
                source_display,
                job.created_at.strftime("%Y-%m-%d %H:%M"),
                duration_display
            )
        
        console.print(table)
        console.print(f"\n[dim]View details:[/dim] dva kg ingest status <job-id>")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


@ingest_app.command("status")
def ingest_status(
    job_id: Annotated[str, typer.Argument(help="Job ID to check")],
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
) -> None:
    """Check the status of an ingestion operation."""
    from agentic_cli.kg.async_ingest import get_manager, JobStatus
    
    try:
        manager = get_manager()
        job = manager.get_job(job_id)
        
        if not job:
            console.print(f"[red]✗ Operation not found:[/red] {job_id}")
            raise typer.Exit(1)
        
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
            f"[cyan]Mode:[/cyan] {'Async' if job.is_async else 'Sync'}",
            f"[cyan]Status:[/cyan] [{status_style}]{job.status.value}[/{status_style}]",
            f"[cyan]Provider:[/cyan] {job.provider}",
            f"[cyan]Source:[/cyan] {job.source}",
            f"[cyan]Format:[/cyan] {job.format or 'auto-detect'}",
            f"[cyan]Created:[/cyan] {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        if job.workspace:
            info_lines.append(f"[cyan]Workspace:[/cyan] {job.workspace}")
        
        if job.started_at:
            info_lines.append(f"[cyan]Started:[/cyan] {job.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if job.completed_at:
            info_lines.append(f"[cyan]Completed:[/cyan] {job.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            duration = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
            info_lines.append(f"[cyan]Duration:[/cyan] {duration:.1f}s")
        
        if job.error:
            info_lines.append(f"[red]Error:[/red] {job.error}")
        
        if verbose and job.metadata:
            info_lines.append(f"\n[cyan]Metadata:[/cyan]")
            for key, value in job.metadata.items():
                info_lines.append(f"  {key}: {value}")
        
        if verbose and job.result:
            info_lines.append(f"\n[cyan]Result:[/cyan]")
            for key, value in job.result.items():
                info_lines.append(f"  {key}: {value}")
        
        panel = Panel(
            "\n".join(info_lines),
            title=f"Ingestion Operation {job.job_id[:8]}",
            border_style=status_style
        )
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


@ingest_app.command("cancel")
def ingest_cancel(
    job_id: Annotated[str, typer.Argument(help="Job ID to cancel")],
) -> None:
    """Cancel a running or pending ingestion operation (async only)."""
    from agentic_cli.kg.async_ingest import get_manager
    
    try:
        manager = get_manager()
        job = manager.get_job(job_id)
        
        if not job:
            console.print(f"[red]✗ Operation not found:[/red] {job_id}")
            raise typer.Exit(1)
        
        if not job.is_async:
            console.print(f"[yellow]⚠ Cannot cancel sync operation[/yellow]")
            console.print("[dim]Sync operations run in foreground and cannot be cancelled[/dim]")
            raise typer.Exit(1)
        
        success = manager.cancel_job(job_id)
        
        if success:
            console.print(f"[green]✓ Operation cancelled:[/green] {job_id}")
        else:
            console.print(f"[yellow]⚠ Operation not found or already completed:[/yellow] {job_id}")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)


@kg_app.command()
def sync(
    repos: bool = typer.Option(False, "--repos", help="Sync only onboarded repositories"),
    projects: bool = typer.Option(False, "--projects", help="Sync only created agent projects"),
    activity: bool = typer.Option(False, "--activity", help="Sync only recent CLI activity"),
    activity_limit: int = typer.Option(50, help="Max activity records to include"),
    since: str | None = typer.Option(None, help="Only sync activity since this ISO date (e.g. 2026-04-01)"),
    skip_validation: bool = typer.Option(False, help="Skip LightRAG validation", hidden=True),
) -> None:
    """
    Sync platform data from tracker.db to the Knowledge Graph.

    Pushes onboarded repos, agent projects, and CLI activity into LightRAG
    so that agents connected via KG MCP can query full platform context.

    With no flags, syncs everything. Use --repos, --projects, or --activity
    to sync selectively.

    Examples:
        dva kg sync                     # sync all
        dva kg sync --repos             # just repos
        dva kg sync --activity --since 2026-04-01  # recent activity
    """
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.sync import sync_to_lightrag

    # If no flags given, sync everything
    sync_all = not (repos or projects or activity)
    do_repos = sync_all or repos
    do_projects = sync_all or projects
    do_activity = sync_all or activity

    # Validate LightRAG connection
    config = KGConfig.load()
    if config.provider != "lightrag" and not skip_validation:
        console.print("[yellow]⚠ KG sync currently targets LightRAG only.[/yellow]")
        console.print(f"[dim]Current provider: {config.provider}. Switch with: dva kg init --provider lightrag[/dim]")
        raise typer.Exit(1)

    if not skip_validation:
        from agentic_cli.kg.lightrag_client import check_lightrag_availability
        is_available, message = check_lightrag_availability(base_url=config.lightrag_url)
        if not is_available:
            console.print(f"[bold red]✗ LightRAG is not available:[/bold red] {message}")
            raise typer.Exit(1)

    # Run sync
    parts = []
    if do_repos:
        parts.append("repos")
    if do_projects:
        parts.append("projects")
    if do_activity:
        parts.append("activity")

    with console.status(f"[bold green]Syncing {', '.join(parts)} to KG..."):
        result = sync_to_lightrag(
            sync_repos=do_repos,
            sync_projects=do_projects,
            sync_activity=do_activity,
            activity_limit=activity_limit,
            activity_since=since,
        )

    # Report results
    if result.errors:
        for err in result.errors:
            console.print(f"[red]✗ Error:[/red] {err}")

    table = Table(title="KG Sync Results")
    table.add_column("Data", style="cyan")
    table.add_column("Records", justify="right")
    table.add_column("Status", style="bold")

    if do_repos:
        status = f"[green]✓ synced[/green]" if result.repos_synced else "[dim]no data[/dim]"
        table.add_row("Repositories", str(result.repos_synced), status)
    if do_projects:
        status = f"[green]✓ synced[/green]" if result.projects_synced else "[dim]no data[/dim]"
        table.add_row("Agent Projects", str(result.projects_synced), status)
    if do_activity:
        status = f"[green]✓ synced[/green]" if result.activities_synced else "[dim]no data[/dim]"
        table.add_row("Activity Log", str(result.activities_synced), status)

    console.print(table)
    console.print(f"\n[dim]Total characters pushed: {result.total_chars:,}[/dim]")

    if result.total_documents > 0 and not result.errors:
        console.print("[bold green]✓ Platform context now available to agents via KG MCP[/bold green]")

    record_activity(
        command="kg", subcommand="sync",
        args={"repos": do_repos, "projects": do_projects, "activity": do_activity},
        details={
            "repos_synced": result.repos_synced,
            "projects_synced": result.projects_synced,
            "activities_synced": result.activities_synced,
            "total_chars": result.total_chars,
        },
    )


@kg_app.command()
def query(
    query_text: Annotated[str, typer.Argument(help="Query to execute")],
    format: str = typer.Option(
        default="natural",
        help="Query format (natural, cypher)",
    ),
    limit: int = typer.Option(
        default=10,
        help="Maximum number of results",
    ),
    mode: str = typer.Option(
        default="hybrid",
        help="LightRAG query mode (naive, local, global, hybrid)",
    ),
    persona: str = typer.Option(
        default=None,
        help="Filter by persona (developer, business, or None for all)",
    ),
    skip_validation: bool = typer.Option(
        default=False,
        help="Skip connection validation",
        hidden=True,
    ),
) -> None:
    """
    Query the knowledge graph with optional persona filtering.
    
    Neo4j: Supports natural language queries (converted to Cypher) or direct Cypher queries.
           Use --persona to filter by developer (code) or business (docs) context.
    
    LightRAG: Supports natural language queries with different modes (naive, local, global, hybrid).
              Persona filter applies to document metadata.
    
    Examples:
        # Query all contexts
        dva kg query "authentication"
        
        # Query only code (developer persona)
        dva kg query "authentication functions" --persona developer
        
        # Query only docs (business persona)
        dva kg query "authentication requirements" --persona business
    """
    from agentic_cli.kg.config import KGConfig
    
    # Load configuration to determine provider
    config = KGConfig.load()
    
    # Provider-specific handling
    if config.provider == "neo4j":
        # Validate Neo4j connection
        if not validate_neo4j_connection(skip_check=skip_validation):
            raise typer.Exit(1)
    elif config.provider == "lightrag":
        # Validate LightRAG connection
        if not skip_validation:
            from agentic_cli.kg.lightrag_client import check_lightrag_availability
            is_available, message = check_lightrag_availability(base_url=config.lightrag_url)
            if not is_available:
                console.print(f"[bold red]✗ LightRAG is not available:[/bold red] {message}")
                raise typer.Exit(1)
    else:
        console.print(f"[bold red]✗ Unknown provider:[/bold red] {config.provider}")
        console.print("[dim]fRun '{CLI_NAME} kg init' to configure a provider.[/dim]")
        raise typer.Exit(1)
    
    # Add persona context to query if specified
    persona_context = ""
    if persona:
        if persona == "developer":
            persona_context = " (filtering code/developer context)"
        elif persona == "business":
            persona_context = " (filtering docs/business context)"
        console.print(f"[dim]Persona filter: {persona}{persona_context}[/dim]")
    
    with console.status("[bold green]Executing query..."):
        try:
            if config.provider == "neo4j":
                from agentic_cli.kg.query import execute_query
                
                # Add persona filter to query if specified
                if persona and format == "natural":
                    # Enhance query with persona context
                    enhanced_query = f"{query_text} [persona: {persona}]"
                    results = execute_query(enhanced_query, format=format, limit=limit, persona=persona)
                else:
                    results = execute_query(query_text, format=format, limit=limit, persona=persona)
                
                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    return
                
                console.print(f"[bold green]✓[/bold green] Found {len(results)} results\n")
                
                for i, result in enumerate(results, 1):
                    console.print(f"[bold cyan]{i}.[/bold cyan] {result}")
            
            elif config.provider == "lightrag":
                from agentic_cli.kg.lightrag_client import LightRAGClient
                
                # Add persona context to LightRAG query
                enhanced_query = query_text
                if persona:
                    if persona == "developer":
                        enhanced_query = f"From the code/developer perspective: {query_text}"
                    elif persona == "business":
                        enhanced_query = f"From the documentation/business perspective: {query_text}"
                
                # Use extended timeout for query operations (can take several minutes with large graphs)
                timeout = max(config.lightrag_timeout, 300.0)  # At least 5 minutes
                client = LightRAGClient(base_url=config.lightrag_url, timeout=timeout)
                result = client.query(enhanced_query, mode=mode, top_k=limit)
                client.close()
                
                console.print(f"[bold green]✓[/bold green] Query executed (mode: {mode})\n")
                console.print(result.get("result", result))
            
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
            raise typer.Exit(1)


@kg_app.command()
def search(
    text: Annotated[str, typer.Argument(help="Text to search for")],
    semantic: bool = typer.Option(
        default=True,
        help="Use semantic search (embeddings)",
    ),
    exact: bool = typer.Option(
        default=False,
        help="Use exact match instead of semantic search",
    ),
    limit: int = typer.Option(
        default=10,
        help="Maximum number of results",
    ),
    persona: str = typer.Option(
        default=None,
        help="Filter by persona (developer, business, or None for all)",
    ),
    skip_validation: bool = typer.Option(
        default=False,
        help="Skip connection validation",
        hidden=True,
    ),
) -> None:
    """
    Search the knowledge graph using semantic or exact matching with optional persona filtering.
    
    Neo4j: Supports both semantic (vector) and exact (text) search.
    LightRAG: Supports semantic search via the search endpoint.
           Use --persona to filter by developer (code) or business (docs) context.
    
    Examples:
        # Search all contexts
        dva kg search "patient"
        
        # Search only code (developer persona)
        dva kg search "authentication" --persona developer
        
        # Search only docs (business persona)
        dva kg search "requirements" --persona business
    """
    from agentic_cli.kg.config import KGConfig
    
    # Load configuration to determine provider
    config = KGConfig.load()
    
    # Provider-specific handling
    if config.provider == "neo4j":
        # Validate Neo4j connection
        if not validate_neo4j_connection(skip_check=skip_validation):
            raise typer.Exit(1)
    elif config.provider == "lightrag":
        # Validate LightRAG connection
        if not skip_validation:
            from agentic_cli.kg.lightrag_client import check_lightrag_availability
            is_available, message = check_lightrag_availability(base_url=config.lightrag_url)
            if not is_available:
                console.print(f"[bold red]✗ LightRAG is not available:[/bold red] {message}")
                raise typer.Exit(1)
    else:
        console.print(f"[bold red]✗ Unknown provider:[/bold red] {config.provider}")
        console.print("[dim]fRun '{CLI_NAME} kg init' to configure a provider.[/dim]")
        raise typer.Exit(1)
    
    # Handle exact flag
    if exact:
        semantic = False
    
    # Add persona context to search if specified
    persona_context = ""
    if persona:
        if persona == "developer":
            persona_context = " (filtering code/developer context)"
        elif persona == "business":
            persona_context = " (filtering docs/business context)"
        console.print(f"[dim]Persona filter: {persona}{persona_context}[/dim]")
    
    with console.status("[bold green]Searching..."):
        try:
            if config.provider == "neo4j":
                from agentic_cli.kg.search import search_graph
                
                results = search_graph(text, semantic=semantic, limit=limit)
                
                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    return
                
                console.print(f"[bold green]✓[/bold green] Found {len(results)} results\n")
                
                for result in results:
                    console.print(f"[bold cyan]{result['entity']}[/bold cyan]")
                    console.print(f"  Type: {result['type']}")
                    if 'score' in result:
                        console.print(f"  Relevance: {result['score']:.2f}")
                    console.print(f"  {result['description']}\n")
            
            elif config.provider == "lightrag":
                from agentic_cli.kg.lightrag_client import LightRAGClient
                
                # Add persona context to LightRAG search
                enhanced_text = text
                if persona:
                    if persona == "developer":
                        enhanced_text = f"From the code/developer perspective: {text}"
                    elif persona == "business":
                        enhanced_text = f"From the documentation/business perspective: {text}"
                
                # Use extended timeout for search operations (can take several minutes with large graphs)
                timeout = max(config.lightrag_timeout, 300.0)  # At least 5 minutes
                client = LightRAGClient(base_url=config.lightrag_url, timeout=timeout)
                result = client.search(enhanced_text, top_k=limit)
                client.close()
                
                console.print(f"[bold green]✓[/bold green] Search completed\n")
                console.print(result.get("results", result))
            
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
            raise typer.Exit(1)


@kg_app.command()
def stats(
    skip_validation: bool = typer.Option(
        default=False,
        help="Skip connection validation",
        hidden=True,
    ),
) -> None:
    """
    Display knowledge graph statistics.
    """
    from agentic_cli.kg.config import KGConfig
    
    # Load configuration to determine provider
    config = KGConfig.load()
    
    # Validate connection based on provider
    if config.provider == "neo4j":
        if not validate_neo4j_connection(skip_check=skip_validation):
            raise typer.Exit(1)
    elif config.provider == "lightrag":
        if not skip_validation:
            from agentic_cli.kg.lightrag_client import check_lightrag_availability
            is_available, message = check_lightrag_availability(base_url=config.lightrag_url)
            if not is_available:
                console.print(f"[bold red]✗ LightRAG is not available:[/bold red] {message}")
                raise typer.Exit(1)
    
    try:
        if config.provider == "neo4j":
            from agentic_cli.kg.stats import get_stats
            
            stats = get_stats()
            
            table = Table(title="Knowledge Graph Statistics (Neo4j)")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green", justify="right")
            
            table.add_row("Total Nodes", str(stats['nodes']))
            table.add_row("Total Relationships", str(stats['relationships']))
            table.add_row("Node Types", str(stats['node_types']))
            table.add_row("Relationship Types", str(stats['relationship_types']))
            
            console.print(table)
            
            if stats.get('top_entities'):
                console.print("\n[bold]Top Entities:[/bold]")
                for entity in stats['top_entities'][:5]:
                    console.print(f"  • {entity['name']} ({entity['connections']} connections)")
        
        elif config.provider == "lightrag":
            from agentic_cli.kg.lightrag_client import LightRAGClient
            
            client = LightRAGClient(base_url=config.lightrag_url, timeout=config.lightrag_timeout)
            stats = client.get_stats()
            doc_status = client.get_document_status()
            client.close()
            
            # Main stats table
            table = Table(title="Knowledge Graph Statistics (LightRAG)")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")
            
            # Display basic stats
            for key, value in stats.items():
                if key != "files":  # Skip file list for main table
                    metric_name = key.replace('_', ' ').title()
                    table.add_row(metric_name, str(value))
            
            console.print(table)
            
            # Document ingestion status table
            if doc_status.get("total_documents", 0) > 0:
                console.print("\n")
                status_table = Table(title="Document Ingestion Status")
                status_table.add_column("Status", style="cyan")
                status_table.add_column("Count", style="green", justify="right")
                
                total = doc_status.get("total_documents", 0)
                completed = doc_status.get("completed", 0)
                processing = doc_status.get("processing", 0)
                pending = doc_status.get("pending", 0)
                failed = doc_status.get("failed", 0)
                
                status_table.add_row("Total Documents", str(total))
                status_table.add_row("✓ Completed", str(completed), style="green")
                status_table.add_row("⏳ Processing", str(processing), style="yellow")
                status_table.add_row("⏸ Pending", str(pending), style="cyan" if pending > 0 else "dim")
                status_table.add_row("✗ Failed", str(failed), style="red" if failed > 0 else "dim")
                
                console.print(status_table)
                
                # Show failed documents if any
                if failed > 0:
                    console.print("\n[bold yellow]⚠ Failed Documents:[/bold yellow]")
                    for doc in doc_status.get("documents", []):
                        if doc.get("status") == "failed":
                            error = doc.get("error", "Unknown error")[:80]
                            console.print(f"  • {doc.get('id', 'Unknown')[:20]}... - {error}...")
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
        raise typer.Exit(1)


@kg_app.command()
def clear(
    provider: str = typer.Option(
        default=None,
        help="Provider to clear (neo4j, lightrag, or both). If not specified, uses configured provider.",
    ),
    yes: bool = typer.Option(
        default=False,
        help="Skip confirmation prompt",
    ),
    show_stats: bool = typer.Option(
        default=True,
        help="Show statistics before and after clearing",
    ),
) -> None:
    """
    Clear all data from the knowledge graph.
    
    This will delete all nodes, relationships, and documents from the specified provider.
    Use with caution as this operation cannot be undone.
    
    Examples:
        # Clear configured provider (with confirmation)
        dva kg clear
        
        # Clear LightRAG without confirmation
        dva kg clear --provider lightrag --yes
        
        # Clear Neo4j with stats
        dva kg clear --provider neo4j --show-stats
        
        # Clear both providers
        dva kg clear --provider both --yes
    """
    from agentic_cli.kg.config import KGConfig
    
    config = KGConfig.load()
    
    # Determine which provider(s) to clear
    if provider is None:
        provider = config.provider
    
    providers_to_clear = []
    if provider == "both":
        providers_to_clear = ["neo4j", "lightrag"]
    else:
        providers_to_clear = [provider]
    
    # Validate providers
    valid_providers = ["neo4j", "lightrag"]
    for p in providers_to_clear:
        if p not in valid_providers:
            console.print(f"[bold red]✗ Invalid provider:[/bold red] {p}")
            console.print(f"[dim]Valid providers: {', '.join(valid_providers)}[/dim]")
            raise typer.Exit(1)
    
    # Show current stats if requested
    if show_stats:
        console.print("\n[bold]Current Statistics:[/bold]\n")
        for p in providers_to_clear:
            try:
                if p == "neo4j":
                    from agentic_cli.kg.stats import get_graph_stats
                    stats = get_graph_stats()
                    console.print(f"[cyan]Neo4j:[/cyan]")
                    console.print(f"  Nodes: {stats.get('node_count', 0)}")
                    console.print(f"  Relationships: {stats.get('relationship_count', 0)}")
                elif p == "lightrag":
                    from agentic_cli.kg.lightrag_client import LightRAGClient
                    client = LightRAGClient(base_url=config.lightrag_url, timeout=config.lightrag_timeout)
                    stats = client.get_stats()
                    doc_status = client.get_document_status()
                    client.close()
                    console.print(f"[cyan]LightRAG:[/cyan]")
                    console.print(f"  Entities: {stats.get('entity_count', 0)}")
                    console.print(f"  Relations: {stats.get('relation_count', 0)}")
                    console.print(f"  Documents: {doc_status.get('total_documents', 0)}")
            except Exception as e:
                console.print(f"[yellow]⚠ Could not fetch stats for {p}: {e}[/yellow]")
        console.print()
    
    # Confirmation prompt
    if not yes:
        provider_names = " and ".join(providers_to_clear)
        console.print(f"[bold yellow]⚠ Warning:[/bold yellow] This will delete ALL data from {provider_names}.")
        console.print("[dim]This operation cannot be undone.[/dim]\n")
        
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)
    
    # Clear each provider
    for p in providers_to_clear:
        console.print(f"\n[bold]Clearing {p}...[/bold]")
        
        try:
            if p == "neo4j":
                # Clear Neo4j data
                from agentic_cli.kg.neo4j_client import Neo4jClient
                
                client = Neo4jClient(config)
                client.connect()
                
                # Delete all nodes and relationships
                with console.status("[bold green]Deleting all nodes and relationships..."):
                    result = client.execute_cypher("MATCH (n) WHERE n._source = 'dva_kg' DETACH DELETE n")
                
                client.close()
                console.print(f"[bold green]✓[/bold green] Neo4j data cleared successfully")
                
            elif p == "lightrag":
                # Clear LightRAG data
                from agentic_cli.kg.lightrag_client import LightRAGClient
                
                with console.status("[bold green]Clearing LightRAG data..."):
                    client = LightRAGClient(base_url=config.lightrag_url, timeout=config.lightrag_timeout)
                    result = client.clear()
                    client.close()
                
                console.print(f"[bold green]✓[/bold green] LightRAG data cleared successfully")
                
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error clearing {p}: {str(e)}")
            raise typer.Exit(1)
    
    # Show final stats if requested
    if show_stats:
        console.print("\n[bold]Final Statistics:[/bold]\n")
        for p in providers_to_clear:
            try:
                if p == "neo4j":
                    from agentic_cli.kg.stats import get_graph_stats
                    stats = get_graph_stats()
                    console.print(f"[cyan]Neo4j:[/cyan]")
                    console.print(f"  Nodes: {stats.get('node_count', 0)}")
                    console.print(f"  Relationships: {stats.get('relationship_count', 0)}")
                elif p == "lightrag":
                    from agentic_cli.kg.lightrag_client import LightRAGClient
                    client = LightRAGClient(base_url=config.lightrag_url, timeout=config.lightrag_timeout)
                    stats = client.get_stats()
                    doc_status = client.get_document_status()
                    client.close()
                    console.print(f"[cyan]LightRAG:[/cyan]")
                    console.print(f"  Entities: {stats.get('entity_count', 0)}")
                    console.print(f"  Relations: {stats.get('relation_count', 0)}")
                    console.print(f"  Documents: {doc_status.get('total_documents', 0)}")
            except Exception as e:
                console.print(f"[yellow]⚠ Could not fetch final stats for {p}: {e}[/yellow]")
    
    console.print(f"\n[bold green]✓ Successfully cleared {' and '.join(providers_to_clear)}[/bold green]")


@kg_app.command()
def tool(
    name: str = typer.Option(
        default="knowledge_graph",
        help="Name for the generated tool",
    ),
    output: Path | None = typer.Option(
        default=None,
        help="Output path for the tool file",
    ),
    operations: str = typer.Option(
        default="search,query,traverse",
        help="Comma-separated list of operations to include",
    ),
) -> None:
    """
    Generate an ADK tool class for knowledge graph operations.
    """
    from agentic_cli.kg.tool_generator import generate_tool
    
    try:
        ops = [op.strip() for op in operations.split(",")]
        tool_code = generate_tool(name=name, operations=ops)
        
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(tool_code)
            console.print(f"[bold green]✓[/bold green] Tool generated: {output}")
        else:
            console.print(tool_code)
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
        raise typer.Exit(1)


@kg_app.command()
def visualize(
    output: Path = typer.Option(
        default=Path("graph.html"),
        help="Output file for visualization",
    ),
    filter: str | None = typer.Option(
        default=None,
        help="Filter nodes by type or property",
    ),
    depth: int = typer.Option(
        default=2,
        help="Maximum depth for graph traversal",
    ),
) -> None:
    """
    Generate an interactive visualization of the knowledge graph.
    
    Note: This command currently only supports Neo4j provider.
    """
    from agentic_cli.kg.config import KGConfig
    
    # Load configuration to check provider
    config = KGConfig.load()
    
    if config.provider != "neo4j":
        console.print(f"[bold yellow]⚠ Visualization is only supported for Neo4j provider[/bold yellow]")
        console.print(f"  Current provider: [cyan]{config.provider}[/cyan]")
        console.print("\n[dim]To use visualization:[/dim]")
        console.print("  1. Switch to Neo4j: dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password")
        console.print("  2. Ingest your data: dva kg ingest --path /your/data")
        console.print("  3. Run visualization: dva kg visualize")
        raise typer.Exit(1)
    
    # Validate Neo4j connection
    if not validate_neo4j_connection():
        raise typer.Exit(1)
    
    from agentic_cli.kg.visualize import create_visualization
    
    with console.status("[bold green]Creating visualization..."):
        try:
            create_visualization(output=output, filter=filter, depth=depth)
            console.print(f"[bold green]✓[/bold green] Visualization saved: {output}")
            console.print(f"  Open in browser: file://{output.absolute()}")
            
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
            raise typer.Exit(1)
