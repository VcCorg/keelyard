"""Knowledge Graph commands for agentic-cli."""

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

# Register OKF bundle subcommand
from agentic_cli.commands.kg_okf import okf_app
kg_app.add_typer(okf_app, name="okf", help="Open Knowledge Format (OKF) bundle commands")

# Configuration file location (shared with data commands)
CONFIG_DIR = Path.home() / ".agent-cli-agentic"
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
        console.print(f"[dim]Use '{CLI_NAME} data create' to configure data sources first.[/dim]")
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
    console.print(f"[dim]Use '{CLI_NAME} data list' to see available sources.[/dim]")
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
        help="Provider to check (neo4j, postgres, lightrag, weaviate). Defaults to configured provider.",
    ),
) -> None:
    """
    Check prerequisites and provider availability.
    
    Validates prerequisites for Neo4j, PostgreSQL, or LightRAG based on configured or specified provider.
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
    elif provider == "postgres":
        _check_postgres()
    elif provider == "lightrag":
        _check_lightrag()
    elif provider == "weaviate":
        _check_weaviate()
    else:
        console.print(f"[red]✗ Unknown provider:[/red] {provider}")
        console.print("[dim]Valid providers: neo4j, postgres, lightrag, weaviate[/dim]")
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
        console.print(f"  {CLI_NAME} kg ingest submit --path <source>")
        console.print(f"  {CLI_NAME} kg query <query>")
        console.print(f"  {CLI_NAME} kg visualize")
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
    
    # Check LightRAG availability
    is_available, message = check_lightrag_availability(base_url=lightrag_url)
    status_icon = "[green]✓[/green]" if is_available else "[red]✗[/red]"
    table.add_row("LightRAG Service", status_icon, message)
    if not is_available:
        all_passed = False
    
    console.print(table)
    console.print()
    
    if all_passed:
        console.print("[bold green]✓ All prerequisites are met![/bold green]")
        console.print("\nYou can now use LightRAG knowledge graph commands:")
        console.print(f"  {CLI_NAME} kg ingest submit --path <source>")
        console.print(f"  {CLI_NAME} kg query <query>")
        console.print(f"  {CLI_NAME} kg search <text>")
    else:
        console.print("[bold yellow]⚠ Some prerequisites are not met[/bold yellow]")
        console.print("\nTo start LightRAG:")
        console.print("  1. Navigate to LightRAG directory")
        console.print("  2. Run: docker-compose up -d")
        console.print("  3. Configure with: dva kg init --provider lightrag --lightrag-url <url>")


def _check_postgres() -> None:
    """Check PostgreSQL prerequisites."""
    from agentic_cli.kg.postgres_client import check_postgres_availability
    from agentic_cli.kg.config import KGConfig
    
    # Load config to get PostgreSQL settings
    try:
        config = KGConfig.load()
        host = config.postgres_host or "localhost"
        port = config.postgres_port or 5432
        user = config.postgres_user or "postgres"
        password = config.postgres_password or "postgres"
        database = config.postgres_database or "knowledge_graph"
    except:
        host = "localhost"
        port = 5432
        user = "postgres"
        password = "postgres"
        database = "knowledge_graph"
    
    # Display results
    table = Table(title="PostgreSQL Prerequisites Check")
    table.add_column("Component", style="cyan", width=25)
    table.add_column("Status", style="white", width=10)
    table.add_column("Message", style="yellow")
    
    all_passed = True
    
    # Check PostgreSQL availability
    is_available, message = check_postgres_availability(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
    status_icon = "[green]✓[/green]" if is_available else "[red]✗[/red]"
    table.add_row("PostgreSQL Service", status_icon, message)
    if not is_available:
        all_passed = False
    
    # Check psycopg2
    try:
        import psycopg2
        table.add_row("psycopg2 Library", "[green]✓[/green]", "Installed")
    except ImportError:
        table.add_row("psycopg2 Library", "[red]✗[/red]", "Not installed (pip install psycopg2-binary)")
        all_passed = False
    
    console.print(table)
    console.print()
    
    if all_passed:
        console.print("[bold green]✓ All prerequisites are met![/bold green]")
        console.print("\nYou can now use PostgreSQL knowledge graph commands:")
        console.print(f"  {CLI_NAME} kg ingest submit --path <source> --provider postgres")
        console.print(f"  {CLI_NAME} kg query <query>")
        console.print(f"  {CLI_NAME} kg search <text>")
        console.print(f"\nTo setup KG tables:")
        console.print("  cd /Users/your-user/agentic-project/myAgentPG/kg-infrastructure/postgres-graph")
        console.print("  ./setup-kg.sh")
    else:
        console.print("[bold yellow]⚠ Some prerequisites are not met[/bold yellow]")
        console.print("\nTo start PostgreSQL with pgvector and Apache AGE:")
        console.print("  1. Navigate to: /Users/your-user/agentic-project/myAgentPG/kg-infrastructure/postgres-graph")
        console.print("  2. Run: docker-compose up -d")
        console.print("  3. Run: ./setup-kg.sh")
        console.print("  4. Configure with: dva kg init --provider postgres --postgres-host <host>")


def _check_weaviate() -> None:
    """Check Weaviate prerequisites."""
    from agentic_cli.kg.weaviate_client import check_weaviate_availability
    from agentic_cli.kg.config import KGConfig
    
    # Load config to get Weaviate settings
    try:
        config = KGConfig.load()
        host = config.weaviate_host or "localhost"
        port = config.weaviate_port or 8080
        scheme = config.weaviate_scheme or "http"
    except:
        host = "localhost"
        port = 8080
        scheme = "http"
    
    # Display results
    table = Table(title="Weaviate Prerequisites Check")
    table.add_column("Component", style="cyan", width=25)
    table.add_column("Status", style="white", width=10)
    table.add_column("Message", style="yellow")
    
    all_passed = True
    
    # Check Weaviate availability
    is_available, message = check_weaviate_availability(
        host=host,
        port=port,
        scheme=scheme
    )
    status_icon = "[green]✓[/green]" if is_available else "[red]✗[/red]"
    table.add_row("Weaviate Service", status_icon, message)
    if not is_available:
        all_passed = False
    
    # Check weaviate-client
    try:
        import weaviate
        table.add_row("weaviate-client Library", "[green]✓[/green]", "Installed")
    except ImportError:
        table.add_row("weaviate-client Library", "[red]✗[/red]", "Not installed (pip install weaviate-client)")
        all_passed = False
    
    console.print(table)
    console.print()
    
    if all_passed:
        console.print("[bold green]✓ All prerequisites are met![/bold green]")
        console.print("\nYou can now use Weaviate knowledge graph commands:")
        console.print(f"  {CLI_NAME} kg ingest submit --path <source> --provider weaviate")
        console.print(f"  {CLI_NAME} kg query <query>")
        console.print(f"  {CLI_NAME} kg search <text>")
    else:
        console.print("[bold yellow]⚠ Some prerequisites are not met[/bold yellow]")
        console.print("\nTo start Weaviate:")
        console.print("  1. Navigate to: /Users/your-user/agentic-project/myAgentPG/kg-infrastructure/weaviate")
        console.print("  2. Run: docker-compose up -d")
        console.print("  3. Configure with: dva kg init --provider weaviate --weaviate-host <host>")


@kg_app.command()
def init(
    provider: str = typer.Option(
        default="neo4j",
        help="Graph database provider (neo4j, postgres, lightrag, weaviate)",
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
    postgres_host: str | None = typer.Option(
        default=None,
        help="PostgreSQL host (e.g., localhost)",
    ),
    postgres_port: int | None = typer.Option(
        default=None,
        help="PostgreSQL port (e.g., 5432)",
    ),
    postgres_user: str | None = typer.Option(
        default=None,
        help="PostgreSQL username",
    ),
    postgres_password: str | None = typer.Option(
        default=None,
        help="PostgreSQL password",
    ),
    postgres_database: str | None = typer.Option(
        default=None,
        help="PostgreSQL database name",
    ),
    postgres_graph: str | None = typer.Option(
        default=None,
        help="Apache AGE graph name",
    ),
    lightrag_url: str | None = typer.Option(
        default=None,
        help="LightRAG API URL (e.g., http://localhost:8001)",
    ),
    lightrag_timeout: float | None = typer.Option(
        default=None,
        help="LightRAG request timeout in seconds",
    ),
    weaviate_host: str | None = typer.Option(
        default=None,
        help="Weaviate host (e.g., localhost)",
    ),
    weaviate_port: int | None = typer.Option(
        default=None,
        help="Weaviate port (e.g., 8080)",
    ),
    weaviate_scheme: str | None = typer.Option(
        default=None,
        help="Weaviate connection scheme (http or https)",
    ),
    weaviate_api_key: str | None = typer.Option(
        default=None,
        help="Weaviate API key (for authentication)",
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
    if postgres_host:
        config.postgres_host = postgres_host
    if postgres_port:
        config.postgres_port = postgres_port
    if postgres_user:
        config.postgres_user = postgres_user
    if postgres_password:
        config.postgres_password = postgres_password
    if postgres_database:
        config.postgres_database = postgres_database
    if postgres_graph:
        config.postgres_graph = postgres_graph
    if lightrag_url:
        config.lightrag_url = lightrag_url
    if lightrag_timeout:
        config.lightrag_timeout = lightrag_timeout
    if weaviate_host:
        config.weaviate_host = weaviate_host
    if weaviate_port:
        config.weaviate_port = weaviate_port
    if weaviate_scheme:
        config.weaviate_scheme = weaviate_scheme
    if weaviate_api_key:
        config.weaviate_api_key = weaviate_api_key
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
    elif provider == "postgres":
        console.print(f"  Host: [cyan]{config.postgres_host}[/cyan]")
        console.print(f"  Port: [cyan]{config.postgres_port}[/cyan]")
        console.print(f"  Database: [cyan]{config.postgres_database}[/cyan]")
        console.print(f"  Graph: [cyan]{config.postgres_graph}[/cyan]")
    elif provider == "lightrag":
        console.print(f"  URL: [cyan]{config.lightrag_url}[/cyan]")
        console.print(f"  Timeout: [cyan]{config.lightrag_timeout}s[/cyan]")
    elif provider == "weaviate":
        console.print(f"  Host: [cyan]{config.weaviate_host}[/cyan]")
        console.print(f"  Port: [cyan]{config.weaviate_port}[/cyan]")
        console.print(f"  Scheme: [cyan]{config.weaviate_scheme}[/cyan]")
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
            console.print(f"[dim]Run '{CLI_NAME} kg config --show' to verify settings.[/dim]")
    elif provider == "weaviate":
        console.print("\n[bold]Validating Weaviate connection...[/bold]")
        
        from agentic_cli.kg.weaviate_client import check_weaviate_availability
        
        is_available, message = check_weaviate_availability(
            host=config.weaviate_host,
            port=config.weaviate_port,
            scheme=config.weaviate_scheme,
            api_key=config.weaviate_api_key
        )
        
        if is_available:
            console.print(f"[bold green]✓[/bold green] {message}")
        else:
            console.print(f"[bold yellow]⚠[/bold yellow] {message}")
            console.print("\n[dim]Configuration saved, but Weaviate is not accessible.[/dim]")
            console.print(f"[dim]Run '{CLI_NAME} kg config --show' to verify settings.[/dim]")
    elif provider == "postgres":
        console.print("\n[bold]Validating PostgreSQL connection...[/bold]")
        
        from agentic_cli.kg.postgres_client import check_postgres_availability
        
        is_available, message = check_postgres_availability(
            host=config.postgres_host,
            port=config.postgres_port,
            user=config.postgres_user,
            password=config.postgres_password,
            database=config.postgres_database
        )
        
        if is_available:
            console.print(f"[bold green]✓[/bold green] {message}")
        else:
            console.print(f"[bold yellow]⚠[/bold yellow] {message}")
            console.print("\n[dim]Configuration saved, but PostgreSQL is not accessible.[/dim]")
            console.print("[dim]Make sure PostgreSQL with pgvector and Apache AGE is running.[/dim]")
            console.print(f"[dim]Run: cd /Users/your-user/agentic-project/myAgentPG/kg-infrastructure/postgres-graph && docker-compose up -d[/dim]")
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
        config_path = Path.home() / ".agent-cli-agentic" / "kg-config.json"
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
        elif config.provider == "postgres":
            table.add_row("PostgreSQL Host", config.postgres_host)
            table.add_row("PostgreSQL Port", str(config.postgres_port))
            table.add_row("PostgreSQL User", config.postgres_user)
            table.add_row("PostgreSQL Password", "***" if config.postgres_password else "Not set")
            table.add_row("PostgreSQL Database", config.postgres_database)
            table.add_row("Apache AGE Graph", config.postgres_graph)
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
    domain: str | None = typer.Option(
        None,
        "--domain",
        help="Domain slug — auto-fetches tracked Confluence docs, tags with domain metadata, defaults workspace to domain slug",
    ),
    product: str | None = typer.Option(
        None,
        "--product",
        help="Product name to tag ingested nodes/job with (e.g. CWOW). Derived from --domain if omitted.",
    ),
    depth: int = typer.Option(
        3,
        "--depth",
        help="Max child-page crawl depth for Confluence pages (used with --domain or --format confluence)",
    ),
    top: int | None = typer.Option(
        None,
        "--top",
        help="Limit to first N pages for testing/validation (ingests all pages if not specified)",
    ),
) -> None:
    """
    Submit data for ingestion into the knowledge graph.
    
    You can specify a source in two ways:
    1. Direct path/URL: {CLI_NAME} kg ingest submit --path /path/to/file.pdf
    2. Data source name: {CLI_NAME} kg ingest submit --source my-dataset
    
    Data sources are configured using f'{CLI_NAME} data create' command.
    
    Supports: PDF, text files, CSV, JSON, Confluence pages, and directories.
    
    For directories, all supported files (.pdf, .txt, .md, .csv, .json) will be processed.
    
    Use --domain to build a domain knowledge graph from Confluence docs:
      {CLI_NAME} kg ingest submit --domain cwow-facility
      {CLI_NAME} kg ingest submit --domain cwow-facility --path <confluence-page-url>
      {CLI_NAME} kg ingest submit --domain cwow-facility --path <confluence-page-url> --depth 4
    
    Use --async flag to run ingestion in background:
      {CLI_NAME} kg ingest submit --path /data --async
    """
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.async_ingest import get_manager
    
    # Load configuration to determine provider
    config = KGConfig.load()
    
    # Default workspace to domain slug when --domain is set
    if domain and not workspace and config.provider == "lightrag":
        workspace = domain

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
            console.print(f"[dim]Create it with: {CLI_NAME} kg workspace create {workspace}[/dim]")
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
            elif config.provider == "weaviate":
                # Validate Weaviate connection
                if not skip_validation:
                    from agentic_cli.kg.weaviate_client import check_weaviate_availability
                    is_available, message = check_weaviate_availability(
                        host=config.weaviate_host,
                        port=config.weaviate_port,
                        scheme=config.weaviate_scheme,
                        api_key=config.weaviate_api_key
                    )
                    if not is_available:
                        console.print(f"[bold red]✗ Weaviate is not available:[/bold red] {message}")
                        raise typer.Exit(1)
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
        # Auto-detect Confluence format from URL pattern
        if not resolved_format and ("confluence" in resolved_source.lower() or "/pages/" in resolved_source or "/spaces/" in resolved_source):
            resolved_format = "confluence"
    elif domain and not source and not data_source:
        # Domain-only mode: use domain slug as source, will fetch tracked docs below
        resolved_source = f"domain:{domain}"
        resolved_format = "confluence"  # Domain docs are Confluence pages
        if source_metadata is None:
            source_metadata = {}
        source_metadata["domain"] = domain
    else:
        console.print("[red]✗ Error:[/red] Must specify either --source (data source name), --path (direct path), or --domain.")
        console.print(f"[dim]Use '{CLI_NAME} data list' to see configured data sources.[/dim]")
        raise typer.Exit(1)

    # Tag the ingestion with product (and domain). A knowledge graph should be
    # tied to a product; the domain is optional. When --domain is given we can
    # derive the product from the registered domain if it wasn't passed explicitly.
    if source_metadata is None:
        source_metadata = {}
    resolved_product = product
    if not resolved_product and domain:
        try:
            from agentic_cli.tracker import get_domain as _get_domain
            _d = _get_domain(domain)
            if _d and _d.get("product"):
                resolved_product = _d.get("product")
        except Exception:
            pass
    if resolved_product:
        source_metadata["product"] = resolved_product
        console.print(f"[cyan]ℹ[/cyan] Tagging ingestion with product: {resolved_product}")
    if domain:
        source_metadata.setdefault("domain", domain)

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
            
            # Add top to metadata if specified
            if top:
                job.metadata["top"] = top
            
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
            console.print(f"\n[dim]Check status:[/dim] {CLI_NAME} kg ingest list")
            console.print(f"[dim]View details:[/dim] {CLI_NAME} kg ingest status {job.job_id[:8]}")
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
        from agentic_cli.kg.parsers import parse_confluence_tree
        
        # Handle domain mode for Neo4j
        if domain and resolved_source.startswith("domain:"):
            from agentic_cli.tracker import get_domain, get_domain_docs
            
            console.print(f"[dim]Fetching tracked docs for domain '{domain}'...[/dim]")
            d = get_domain(domain)
            if not d:
                console.print(f"[red]✗ Domain '{domain}' not found.[/red]")
                raise typer.Exit(1)
            
            docs = get_domain_docs(domain)
            if not docs:
                console.print(f"[yellow]No tracked docs for domain '{domain}'.[/yellow]")
                raise typer.Exit(1)
            
            # Limit to top N pages if --top is specified
            if top:
                docs = docs[:top]
                console.print(f"[yellow]Limiting to top {top} pages for testing/validation[/yellow]")
            
            console.print(f"[dim]Found {len(docs)} tracked docs, ingesting to Neo4j...[/dim]")
            
            total_entities = 0
            total_relationships = 0
            failed_count = 0
            
            try:
                conf_base = config.confluence_url or "https://confluence.example.com"
            except Exception:
                conf_base = "https://confluence.example.com"
            
            for doc_rec in docs:
                page_id = doc_rec.get("source_page_id")
                title = doc_rec.get("title", page_id)
                page_url = f"{conf_base}/pages/{page_id}"
                space_key = doc_rec.get("source_space_key")
                
                # Check if this is a release page and create Release node directly
                release_node_id = None
                is_release_page = "Release" in title
                if is_release_page:
                    try:
                        from agentic_cli.kg.neo4j_client import Neo4jClient
                        with Neo4jClient() as neo4j:
                            release_node = neo4j.create_release_node(
                                page_id=str(page_id),
                                title=title,
                                source_url=page_url,
                                domain=domain,
                                product=d.get("product", ""),
                                space_key=space_key,
                            )
                            release_node_id = release_node.get("id")
                            console.print(f"    [dim]Created Release node: {title} (page_id: {page_id})[/dim]")
                    except Exception as e:
                        console.print(f"    [yellow]Failed to create Release node: {e}[/yellow]")
                
                try:
                    # Try MCP mode first (bypasses KG config check)
                    try:
                        documents = parse_confluence_tree(page_url, include_children=True, max_depth=depth, use_mcp=True, include_attachments=True)
                        console.print(f"    [dim]Found {len(documents)} documents via MCP (page + children + attachments)[/dim]")
                    except Exception as mcp_error:
                        console.print(f"    [yellow]MCP mode failed: {mcp_error}[/yellow]")
                        console.print(f"    [dim]Falling back to direct Confluence API...[/dim]")
                        # Fall back to direct API mode (requires KG config)
                        documents = parse_confluence_tree(page_url, include_children=True, max_depth=depth, use_mcp=False, include_attachments=True)
                        console.print(f"    [dim]Found {len(documents)} documents via direct API (page + children + attachments)[/dim]")
                    
                    # Limit total documents if --top is specified
                    if top and len(documents) > top:
                        documents = documents[:top]
                        console.print(f"    [yellow]Limiting to top {top} documents for testing/validation[/yellow]")
                    
                    # Ingest each document to Neo4j
                    for doc in documents:
                        doc_metadata = doc.get("metadata", {})
                        doc_metadata["domain"] = domain
                        doc_metadata["product"] = d.get("product", "")
                        # Preserve original document title and source from Confluence
                        # Title is in doc["metadata"]["title"] for Confluence documents
                        doc_metadata["document_title"] = doc_metadata.get("title", doc.get("title", ""))
                        if "source" in doc_metadata and not doc_metadata["source"]:
                            # Use the source from the document if available
                            doc_metadata["source"] = doc_metadata.get("source", "")
                        
                        # Check if this document is the release page itself (not a child/attachment)
                        doc_page_id = doc_metadata.get("page_id")
                        is_this_release_page = is_release_page and str(doc_page_id) == str(page_id)
                        
                        # Skip ingestion for release pages themselves - they only create Release nodes
                        if is_this_release_page:
                            console.print(f"    [dim]Skipping document ingestion for release page: {title}[/dim]")
                            continue
                        
                        # Write content to temporary file for ingest_data
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                            f.write(doc["content"])
                            temp_file = f.name
                        
                        try:
                            # Release nodes are created directly from domain_docs tracking
                            result = ingest_data(
                                source=temp_file,
                                format="text",
                                persona=None,
                                metadata=doc_metadata,
                                extract_entities=extract_entities,
                                build_relationships=build_relationships,
                                recursive=False,
                                detailed_analysis=False,
                            )
                            
                            total_entities += result.get('entities_count', 0)
                            total_relationships += result.get('relationships_count', 0)
                        finally:
                            # Clean up temp file
                            import os
                            os.unlink(temp_file)
                    
                    console.print(f"  [green]✓[/green] {title}")
                except Exception as e:
                    console.print(f"  [yellow]⚠ {title}: {e}[/yellow]")
                    failed_count += 1
            
            result = {
                "source": f"domain:{domain}",
                "format": "confluence",
                "entities_count": total_entities,
                "relationships_count": total_relationships,
                "documents_processed": len(docs),
                "documents_failed": failed_count
            }
            
            record_activity(
                command="kg", subcommand="ingest-submit",
                args={"source": data_source or resolved_source, "async": False, "provider": config.provider},
                details={"entities": total_entities, "relationships": total_relationships},
            )

            console.print(f"[bold green]\u2713[/bold green] Successfully ingested domain docs")
            console.print(f"  Domain: [cyan]{domain}[/cyan]")
            console.print(f"  Documents processed: [cyan]{len(docs) - failed_count}/{len(docs)}[/cyan]")
            console.print(f"  Entities: [cyan]{total_entities}[/cyan]")
            console.print(f"  Relationships: [cyan]{total_relationships}[/cyan]")
            
            # Mark domain as ingested
            from agentic_cli.tracker import mark_domain_ingested
            mark_domain_ingested(domain)
            
            # Mark job as completed
            job.status = "completed"
            job.completed_at = __import__('datetime').datetime.utcnow()
            job.result = result
            manager.queue.update_job(job.job_id, status=job.status, completed_at=job.completed_at, result=result)
        else:
            # Regular Neo4j ingestion
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
                
                # Handle Confluence page/space ingestion (+ domain tracked docs)
                if resolved_format == "confluence" or (domain and not resolved_source):
                    from agentic_cli.kg.parsers import parse_confluence_tree, parse_confluence

                    all_documents = []

                    # Fetch tracked domain docs when --domain is set
                    if domain:
                        from agentic_cli.tracker import get_domain, get_domain_docs
                        d = get_domain(domain)
                        if not d:
                            console.print(f"[red]✗ Domain '{domain}' not found.[/red]")
                            raise typer.Exit(1)

                        domain_product = d.get("product", "")

                        docs = get_domain_docs(domain)
                        if docs:
                            console.print(f"[dim]Fetching {len(docs)} tracked docs for domain '{domain}'...[/dim]")
                            try:
                                conf_base = config.confluence_url or "https://confluence.example.com"
                            except Exception:
                                conf_base = "https://confluence.example.com"

                            for doc_rec in docs:
                                page_id = doc_rec.get("source_page_id")
                                title = doc_rec.get("title", page_id)
                                page_url = f"{conf_base}/pages/{page_id}"
                                try:
                                    # Use MCP mode to bypass KG config check, include attachments by default
                                    fetched = parse_confluence_tree(page_url, include_children=True, max_depth=depth, use_mcp=True, include_attachments=True)
                                    all_documents.extend(fetched)
                                    child_count = len(fetched) - 1 if len(fetched) > 1 else 0
                                    suffix = f" (+{child_count} children)" if child_count else ""
                                    console.print(f"  [green]✓[/green] {title}{suffix}")
                                except Exception as e:
                                    console.print(f"  [yellow]⚠ {title}: {e}[/yellow]")
                        else:
                            console.print(f"[dim]No tracked docs for domain '{domain}'.[/dim]")

                    # Fetch explicit page/space URL
                    if resolved_source:
                        if "/pages/" in resolved_source:
                            console.print(f"[dim]Fetching page tree from {resolved_source} (depth={depth})...[/dim]")
                            fetched = parse_confluence_tree(resolved_source, include_children=True, max_depth=depth)
                        else:
                            console.print(f"[dim]Fetching space pages from {resolved_source}...[/dim]")
                            fetched = parse_confluence(resolved_source)
                        all_documents.extend(fetched)
                        root_title = fetched[0]["metadata"]["title"] if fetched else resolved_source
                        console.print(f"  [green]✓[/green] {root_title} ({len(fetched)} pages)")

                    if not all_documents:
                        console.print("[yellow]No Confluence documents found to ingest.[/yellow]")
                        raise typer.Exit(1)

                    # Deduplicate by page_id
                    seen_ids = set()
                    documents = []
                    for doc in all_documents:
                        pid = doc["metadata"].get("page_id", "")
                        if pid and pid in seen_ids:
                            continue
                        if pid:
                            seen_ids.add(pid)
                        documents.append(doc)

                    total_docs = len(documents)
                    total_chars = 0

                    console.print(f"[dim]Inserting {total_docs} unique Confluence documents...[/dim]")

                    for i, doc in enumerate(documents, 1):
                        doc_metadata = doc.get("metadata", {})
                        doc_metadata["persona"] = "business_analyst"
                        if domain:
                            doc_metadata["domain"] = domain
                            doc_metadata["product"] = domain_product

                        try:
                            result = client.insert(
                                text=doc["content"],
                                metadata=doc_metadata,
                            )
                            total_chars += result.get("characters", 0)

                            if i % 10 == 0 or i == total_docs:
                                console.print(f"  [dim]Progress: {i}/{total_docs} ({i*100//total_docs}%)[/dim]")
                        except Exception as e:
                            console.print(f"  [yellow]⚠ Skipped: {doc_metadata.get('title', '?')}: {str(e)[:50]}[/yellow]")
                            continue

                    console.print(f"[bold green]✓[/bold green] Successfully ingested Confluence content")
                    console.print(f"  Documents: [cyan]{total_docs}[/cyan]")
                    console.print(f"  Total characters: [cyan]{total_chars}[/cyan]")
                    if domain:
                        console.print(f"  Domain: [cyan]{domain}[/cyan]")
                        console.print(f"\n[dim]Next steps:[/dim]")
                        console.print(f"[dim]  Build static context: {CLI_NAME} domain init-context {domain}[/dim]")
                        console.print(f"[dim]  Onboard repos: {CLI_NAME} code onboard --path <repo> --domain {domain} --kg[/dim]")

                # Handle Git repository ingestion
                elif resolved_format == "git":
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
            console.print(f"[dim]Run an ingestion:[/dim] {CLI_NAME} kg ingest submit --path <source>")
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
        console.print(f"\n[dim]View details:[/dim] {CLI_NAME} kg ingest status <job-id>")
        
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
        {CLI_NAME} kg sync                     # sync all
        {CLI_NAME} kg sync --repos             # just repos
        {CLI_NAME} kg sync --activity --since 2026-04-01  # recent activity
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
        console.print(f"[dim]Current provider: {config.provider}. Switch with: {CLI_NAME} kg init --provider lightrag[/dim]")
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
    
    PostgreSQL: Supports Cypher queries via Apache AGE.
               Use --format cypher for direct Cypher queries.
    
    LightRAG: Supports natural language queries with different modes (naive, local, global, hybrid).
              Persona filter applies to document metadata.
    
    Examples:
        # Query all contexts
        {CLI_NAME} kg query "authentication"
        
        # Query only code (developer persona)
        {CLI_NAME} kg query "authentication functions" --persona developer
        
        # Query only docs (business persona)
        {CLI_NAME} kg query "authentication requirements" --persona business
        
        # Direct Cypher query (PostgreSQL/Neo4j)
        {CLI_NAME} kg query "MATCH (n) RETURN n LIMIT 10" --format cypher
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
    elif config.provider == "postgres":
        # Validate PostgreSQL connection
        if not skip_validation:
            from agentic_cli.kg.postgres_client import check_postgres_availability
            is_available, message = check_postgres_availability(
                host=config.postgres_host,
                port=config.postgres_port,
                user=config.postgres_user,
                password=config.postgres_password,
                database=config.postgres_database
            )
            if not is_available:
                console.print(f"[bold red]✗ PostgreSQL is not available:[/bold red] {message}")
                raise typer.Exit(1)
    elif config.provider == "weaviate":
        # Validate Weaviate connection
        if not skip_validation:
            from agentic_cli.kg.weaviate_client import check_weaviate_availability
            is_available, message = check_weaviate_availability(
                host=config.weaviate_host,
                port=config.weaviate_port,
                scheme=config.weaviate_scheme,
                api_key=config.weaviate_api_key
            )
            if not is_available:
                console.print(f"[bold red]✗ Weaviate is not available:[/bold red] {message}")
                raise typer.Exit(1)
    else:
        console.print(f"[bold red]✗ Unknown provider:[/bold red] {config.provider}")
        console.print(f"[dim]Run '{CLI_NAME} kg init' to configure a provider.[/dim]")
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
                
                # Display results
                for i, result in enumerate(results[:limit], 1):
                    console.print(f"[cyan]{i}.[/cyan] {result}")
            
            elif config.provider == "postgres":
                from agentic_cli.kg.postgres_client import PostgresClient
                
                client = PostgresClient(
                    host=config.postgres_host,
                    port=config.postgres_port,
                    user=config.postgres_user,
                    password=config.postgres_password,
                    database=config.postgres_database,
                    graph_name=config.postgres_graph
                )
                client.connect()
                
                # PostgreSQL only supports Cypher format via Apache AGE
                if format == "natural":
                    console.print("[yellow]PostgreSQL requires Cypher format. Use --format cypher[/yellow]")
                    console.print(f"[dim]Converting natural query to Cypher: {query_text}[/dim]")
                    # For now, just use the query as-is (would need LLM conversion in production)
                    cypher_query = query_text
                else:
                    cypher_query = query_text
                
                results = client.execute_cypher(cypher_query, parameters={})
                client.close()
                
                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    return
                
                console.print(f"[bold green]✓[/bold green] Found {len(results)} results\n")
                
                # Display results
                for i, result in enumerate(results[:limit], 1):
                    console.print(f"[cyan]{i}.[/cyan] {result}")
            
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
            
            elif config.provider == "weaviate":
                from agentic_cli.kg.weaviate_client import WeaviateClient
                
                client = WeaviateClient(
                    host=config.weaviate_host,
                    port=config.weaviate_port,
                    scheme=config.weaviate_scheme,
                    api_key=config.weaviate_api_key
                )
                client.connect()
                
                # Weaviate uses semantic search by default
                results = client.search(query_text, class_name="Code", limit=limit)
                client.close()
                
                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    return
                
                console.print(f"[bold green]✓[/bold green] Found {len(results)} results\n")
                
                # Display results
                for i, result in enumerate(results[:limit], 1):
                    console.print(f"[cyan]{i}.[/cyan] {result}")
            
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
    PostgreSQL: Supports semantic search via pgvector and exact text search.
    LightRAG: Supports semantic search via the search endpoint.
              Use --persona to filter by developer (code) or business (docs) context.
    
    Examples:
        # Search all contexts
        {CLI_NAME} kg search "patient"
        
        # Search only code (developer persona)
        {CLI_NAME} kg search "authentication" --persona developer
        
        # Search only docs (business persona)
        {CLI_NAME} kg search "requirements" --persona business
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
    elif config.provider == "postgres":
        # Validate PostgreSQL connection
        if not skip_validation:
            from agentic_cli.kg.postgres_client import check_postgres_availability
            is_available, message = check_postgres_availability(
                host=config.postgres_host,
                port=config.postgres_port,
                user=config.postgres_user,
                password=config.postgres_password,
                database=config.postgres_database
            )
            if not is_available:
                console.print(f"[bold red]✗ PostgreSQL is not available:[/bold red] {message}")
                raise typer.Exit(1)
    elif config.provider == "weaviate":
        # Validate Weaviate connection
        if not skip_validation:
            from agentic_cli.kg.weaviate_client import check_weaviate_availability
            is_available, message = check_weaviate_availability(
                host=config.weaviate_host,
                port=config.weaviate_port,
                scheme=config.weaviate_scheme,
                api_key=config.weaviate_api_key
            )
            if not is_available:
                console.print(f"[bold red]✗ Weaviate is not available:[/bold red] {message}")
                raise typer.Exit(1)
    else:
        console.print(f"[bold red]✗ Unknown provider:[/bold red] {config.provider}")
        console.print(f"[dim]Run '{CLI_NAME} kg init' to configure a provider.[/dim]")
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
            
            elif config.provider == "postgres":
                from agentic_cli.kg.postgres_client import PostgresClient
                
                client = PostgresClient(
                    host=config.postgres_host,
                    port=config.postgres_port,
                    user=config.postgres_user,
                    password=config.postgres_password,
                    database=config.postgres_database,
                    graph_name=config.postgres_graph
                )
                client.connect()
                
                # For now, use exact match (semantic search requires embeddings)
                results = client.find_nodes(
                    label=None,
                    properties={"name": text},
                    limit=limit
                )
                client.close()
                
                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    return
                
                console.print(f"[bold green]✓[/bold green] Found {len(results)} results\n")
                
                # Display results
                for i, result in enumerate(results[:limit], 1):
                    console.print(f"[cyan]{i}.[/cyan] {result}")
            
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
            
            elif config.provider == "weaviate":
                from agentic_cli.kg.weaviate_client import WeaviateClient
                
                client = WeaviateClient(
                    host=config.weaviate_host,
                    port=config.weaviate_port,
                    scheme=config.weaviate_scheme,
                    api_key=config.weaviate_api_key
                )
                client.connect()
                
                # Weaviate uses semantic search by default
                results = client.search(text, class_name="Code", limit=limit)
                client.close()
                
                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    return
                
                console.print(f"[bold green]✓[/bold green] Found {len(results)} results\n")
                
                # Display results
                for i, result in enumerate(results[:limit], 1):
                    console.print(f"[cyan]{i}.[/cyan] {result}")
            
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
            raise typer.Exit(1)


@kg_app.command()
def stats(
    domain: str = typer.Option(
        default=None,
        help="Domain slug to filter statistics (only shows nodes with matching domain property)",
    ),
    skip_validation: bool = typer.Option(
        default=False,
        help="Skip connection validation",
        hidden=True,
    ),
) -> None:
    """
    Display knowledge graph statistics.
    
    Shows statistics for the configured provider (Neo4j, PostgreSQL, or LightRAG).
    """
    from agentic_cli.kg.config import KGConfig
    
    # Load configuration to determine provider
    config = KGConfig.load()
    
    # Validate connection based on provider
    if config.provider == "neo4j":
        if not validate_neo4j_connection(skip_check=skip_validation):
            raise typer.Exit(1)
    elif config.provider == "postgres":
        if not skip_validation:
            from agentic_cli.kg.postgres_client import check_postgres_availability
            is_available, message = check_postgres_availability(
                host=config.postgres_host,
                port=config.postgres_port,
                user=config.postgres_user,
                password=config.postgres_password,
                database=config.postgres_database
            )
            if not is_available:
                console.print(f"[bold red]✗ PostgreSQL is not available:[/bold red] {message}")
                raise typer.Exit(1)
    elif config.provider == "lightrag":
        if not skip_validation:
            from agentic_cli.kg.lightrag_client import check_lightrag_availability
            is_available, message = check_lightrag_availability(base_url=config.lightrag_url)
            if not is_available:
                console.print(f"[bold red]✗ LightRAG is not available:[/bold red] {message}")
                raise typer.Exit(1)
    elif config.provider == "weaviate":
        if not skip_validation:
            from agentic_cli.kg.weaviate_client import check_weaviate_availability
            is_available, message = check_weaviate_availability(
                host=config.weaviate_host,
                port=config.weaviate_port,
                scheme=config.weaviate_scheme,
                api_key=config.weaviate_api_key
            )
            if not is_available:
                console.print(f"[bold red]✗ Weaviate is not available:[/bold red] {message}")
                raise typer.Exit(1)
    
    try:
        if config.provider == "neo4j":
            from agentic_cli.kg.stats import get_stats
            
            stats = get_stats(domain=domain)
            
            title = "Knowledge Graph Statistics (Neo4j)"
            if domain:
                title = f"Knowledge Graph Statistics (Neo4j) - Domain: {domain}"
            
            table = Table(title=title)
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
        
        elif config.provider == "postgres":
            from agentic_cli.kg.postgres_client import PostgresClient
            
            client = PostgresClient(
                host=config.postgres_host,
                port=config.postgres_port,
                user=config.postgres_user,
                password=config.postgres_password,
                database=config.postgres_database,
                graph_name=config.postgres_graph
            )
            
            # Connect to PostgreSQL
            client.connect()
            
            # Get entity counts from code_entities table
            stats = client.get_graph_stats()
            client.close()
            
            table = Table(title="Knowledge Graph Statistics (PostgreSQL)")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green", justify="right")
            
            table.add_row("Total Code Entities", str(stats.get('code_entities', 0)))
            table.add_row("Total Document Entities", str(stats.get('document_entities', 0)))
            table.add_row("Total Relationships", str(stats.get('relationships', 0)))
            
            console.print(table)
        
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
        
        elif config.provider == "weaviate":
            from agentic_cli.kg.weaviate_client import WeaviateClient
            
            client = WeaviateClient(
                host=config.weaviate_host,
                port=config.weaviate_port,
                scheme=config.weaviate_scheme,
                api_key=config.weaviate_api_key
            )
            client.connect()
            stats = client.get_graph_stats()
            client.close()
            
            table = Table(title="Knowledge Graph Statistics (Weaviate)")
            table.add_column("Class", style="cyan")
            table.add_column("Count", style="green", justify="right")
            
            for class_name, count in stats.items():
                if class_name != "total_objects":
                    table.add_row(class_name, str(count))
            
            table.add_row("Total Objects", str(stats.get('total_objects', 0)))
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise typer.Exit(1)


@kg_app.command()
def clear(
    provider: str = typer.Option(
        default=None,
        help="Provider to clear (neo4j, postgres, lightrag, or both). If not specified, uses configured provider.",
    ),
    domain: str = typer.Option(
        default=None,
        help="Domain slug to clear (only deletes nodes with matching domain property). If not specified, clears all data.",
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
        {CLI_NAME} kg clear
        
        # Clear PostgreSQL without confirmation
        {CLI_NAME} kg clear --provider postgres --yes
        
        # Clear LightRAG without confirmation
        {CLI_NAME} kg clear --provider lightrag --yes
        
        # Clear Neo4j with stats
        {CLI_NAME} kg clear --provider neo4j --show-stats
        
        # Clear both providers
        {CLI_NAME} kg clear --provider both --yes
    """
    from agentic_cli.kg.config import KGConfig
    
    config = KGConfig.load()
    
    # Determine which provider(s) to clear
    if provider is None:
        provider = config.provider
    
    providers_to_clear = []
    if provider == "both":
        providers_to_clear = ["neo4j", "lightrag", "postgres", "weaviate"]
    else:
        providers_to_clear = [provider]
    
    # Validate providers
    valid_providers = ["neo4j", "postgres", "lightrag", "weaviate"]
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
                    from agentic_cli.kg.stats import get_stats
                    stats = get_stats()
                    console.print(f"[cyan]Neo4j:[/cyan]")
                    console.print(f"  Nodes: {stats.get('nodes', 0)}")
                    console.print(f"  Relationships: {stats.get('relationships', 0)}")
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
        if domain:
            console.print(f"[bold yellow]⚠ Warning:[/bold yellow] This will delete ALL data with domain='{domain}' from {provider_names}.")
        else:
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
                
                # Delete nodes by domain or all data
                if domain:
                    with console.status(f"[bold green]Deleting nodes with domain='{domain}'..."):
                        # First delete relationships between domain nodes
                        client.execute_cypher(f"MATCH (n)-[r]-(m) WHERE n.domain = '{domain}' DELETE r")
                        # Then delete the domain nodes
                        result = client.execute_cypher(f"MATCH (n) WHERE n.domain = '{domain}' DELETE n")
                else:
                    with console.status("[bold green]Deleting all nodes and relationships..."):
                        result = client.execute_cypher("MATCH (n) WHERE n._source = 'dva_kg' DETACH DELETE n")
                
                client.close()
                if domain:
                    console.print(f"[bold green]✓[/bold green] Neo4j data for domain='{domain}' cleared successfully")
                else:
                    console.print(f"[bold green]✓[/bold green] Neo4j data cleared successfully")
                
            elif p == "postgres":
                # Clear PostgreSQL data
                from agentic_cli.kg.postgres_client import PostgresClient
                
                with console.status("[bold green]Clearing PostgreSQL data..."):
                    client = PostgresClient(
                        host=config.postgres_host,
                        port=config.postgres_port,
                        user=config.postgres_user,
                        password=config.postgres_password,
                        database=config.postgres_database,
                        graph_name=config.postgres_graph
                    )
                    client.connect()
                    client.clear_graph()
                    client.close()
                
                console.print(f"[bold green]✓[/bold green] PostgreSQL data cleared successfully")
                
            elif p == "lightrag":
                # Clear LightRAG data
                from agentic_cli.kg.lightrag_client import LightRAGClient
                
                with console.status("[bold green]Clearing LightRAG data..."):
                    client = LightRAGClient(base_url=config.lightrag_url, timeout=config.lightrag_timeout)
                    result = client.clear()
                    client.close()
                
                console.print(f"[bold green]✓[/bold green] LightRAG data cleared successfully")
                
            elif p == "weaviate":
                # Clear Weaviate data
                from agentic_cli.kg.weaviate_client import WeaviateClient
                
                with console.status("[bold green]Clearing Weaviate data..."):
                    client = WeaviateClient(
                        host=config.weaviate_host,
                        port=config.weaviate_port,
                        scheme=config.weaviate_scheme,
                        api_key=config.weaviate_api_key
                    )
                    client.connect()
                    client.clear_graph()
                    client.close()
                
                console.print(f"[bold green]✓[/bold green] Weaviate data cleared successfully")
                
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error clearing {p}: {str(e)}")
            raise typer.Exit(1)
    
    # Show final stats if requested
    if show_stats:
        console.print("\n[bold]Final Statistics:[/bold]\n")
        for p in providers_to_clear:
            try:
                if p == "neo4j":
                    from agentic_cli.kg.stats import get_stats
                    stats = get_stats()
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
    
    # Reset kg_ingested flag for all domains
    from agentic_cli.tracker import update_domain, get_domains
    
    try:
        domains = get_domains()
        for domain in domains:
            if domain.get("kg_ingested", 0) == 1:
                update_domain(domain["name"], kg_ingested=0)
        console.print(f"[dim]Reset KG Ingested flag for {len(domains)} domain(s)[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not reset kg_ingested flags: {e}[/yellow]")


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
    domain: str | None = typer.Option(
        default=None,
        help="Filter nodes by domain slug",
    ),
    depth: int = typer.Option(
        default=2,
        help="Maximum depth for graph traversal",
    ),
) -> None:
    """
    Generate an interactive visualization of the knowledge graph.
    
    Note: This command currently only supports Neo4j provider.
    
    Examples:
        # Visualize entire graph
        {CLI_NAME} kg visualize
        
        # Visualize by domain
        {CLI_NAME} kg visualize --domain cwow-facility
        
        # Visualize by node type
        {CLI_NAME} kg visualize --filter Document
        
        # Visualize by domain with custom depth
        {CLI_NAME} kg visualize --domain cwow-patient --depth 3
    """
    from agentic_cli.kg.config import KGConfig
    
    # Load configuration to check provider
    config = KGConfig.load()
    
    if config.provider != "neo4j":
        console.print(f"[bold yellow]⚠ Visualization is only supported for Neo4j provider[/bold yellow]")
        console.print(f"  Current provider: [cyan]{config.provider}[/cyan]")
        console.print("\n[dim]To use visualization:[/dim]")
        console.print(f"  1. Switch to Neo4j: {CLI_NAME} kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password")
        console.print(f"  2. Ingest your data: {CLI_NAME} kg ingest --path /your/data")
        console.print(f"  3. Run visualization: {CLI_NAME} kg visualize")
        raise typer.Exit(1)
    
    # Validate Neo4j connection
    if not validate_neo4j_connection():
        raise typer.Exit(1)
    
    from agentic_cli.kg.visualize import create_visualization
    
    with console.status("[bold green]Creating visualization..."):
        try:
            create_visualization(output=output, filter=filter, domain=domain, depth=depth)
            console.print(f"[bold green]✓[/bold green] Visualization saved: {output}")
            console.print(f"  Open in browser: file://{output.absolute()}")
            
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
            raise typer.Exit(1)


@kg_app.command("check-release-links")
def check_release_links() -> None:
    """Check if Release nodes are linked to Document (requirement) nodes."""
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.neo4j_client import Neo4jClient
    
    console.print("[bold]Checking Release-Document links...[/bold]")
    
    try:
        config = KGConfig.load()
        
        with Neo4jClient(config) as client:
            results = client.check_release_requirement_links()
            
            # Display results
            console.print(f"\n[bold]Release Nodes:[/bold] {results['release_nodes_count']}")
            console.print(f"[bold]Document Nodes:[/bold] {results['document_nodes_count']}")
            console.print(f"[bold]Release-Document Links:[/bold] {results['release_document_links_count']}")
            
            if results['release_nodes_count'] > 0 and results['release_document_links_count'] == 0:
                console.print("\n[red]✗ Warning: Release nodes exist but are not linked to documents![/red]")
            
            if results['release_nodes_sample']:
                console.print("\n[bold]Sample Release Nodes:[/bold]")
                for node in results['release_nodes_sample'][:5]:
                    console.print(f"  - {node['name']} (id: {node['id']}, labels: {node['labels']})")
                    if node['metadata']:
                        import json
                        try:
                            metadata = json.loads(node['metadata']) if isinstance(node['metadata'], str) else node['metadata']
                            console.print(f"    Metadata: {json.dumps(metadata, indent=2)[:200]}...")
                        except:
                            console.print(f"    Metadata: {str(node['metadata'])[:200]}...")
            
            if results['document_nodes_sample']:
                console.print("\n[bold]Sample Document Nodes:[/bold]")
                for node in results['document_nodes_sample'][:5]:
                    console.print(f"  - {node['name']} (id: {node['id']}, domain: {node['domain']})")
                    if node['metadata']:
                        import json
                        try:
                            metadata = json.loads(node['metadata']) if isinstance(node['metadata'], str) else node['metadata']
                            console.print(f"    Metadata: {json.dumps(metadata, indent=2)[:200]}...")
                        except:
                            console.print(f"    Metadata: {str(node['metadata'])[:200]}...")
            
            if results['release_relationships_sample']:
                console.print("\n[bold]Sample Release-Document Links:[/bold]")
                for rel in results['release_relationships_sample'][:10]:
                    console.print(f"  - {rel['release_name']} -> {rel['doc_name']} ({rel['rel_type']})")
            else:
                console.print("\n[yellow]No Release-Document relationships found[/yellow]")
    
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


@kg_app.command("get-release-requirements")
def get_release_requirements(
    release_name: Annotated[str, typer.Argument(help="Release name (e.g., 'Release 29')")]
) -> None:
    """Get all requirements (FREQ IDs) associated with a specific release."""
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.neo4j_client import Neo4jClient
    
    console.print(f"[bold]Getting requirements for release: {release_name}[/bold]")
    
    try:
        config = KGConfig.load()
        
        with Neo4jClient(config) as client:
            results = client.get_requirements_by_release(release_name)
            
            if "error" in results:
                console.print(f"[red]✗ {results['error']}[/red]")
                raise typer.Exit(1)
            
            # Display release info
            console.print(f"\n[bold]Release:[/bold] {results['release']['name']}")
            
            # Display documents
            console.print(f"[bold]Documents:[/bold] {len(results['documents'])}")
            for doc in results['documents']:
                console.print(f"  - {doc['name']}")
                console.print(f"    Source: {doc['source']}")
            
            # Display FREQ IDs
            console.print(f"\n[bold]FREQ Requirements:[/bold] {results['freq_count']}")
            if results['freq_ids']:
                for freq_id in results['freq_ids']:
                    console.print(f"  - {freq_id}")
            else:
                console.print("  [yellow]No FREQ IDs found in documents[/yellow]")
    
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# kg link
# ═══════════════════════════════════════════════════════════════════════════════

@kg_app.command("link")
def link(
    domain: Annotated[str, typer.Option("--domain", help="Domain slug to link (e.g. cwow-facility)")],
    dry_run: Annotated[bool, typer.Option("--dry-run/--no-dry-run", help="Preview candidates without writing edges")] = False,
    threshold: Annotated[float, typer.Option("--threshold", help="Minimum confidence to write an edge (0.0-1.0)")] = 0.75,
    batch_size: Annotated[int, typer.Option("--batch-size", help="Code entities per Vertex AI call")] = 50,
    show_preview: Annotated[int, typer.Option("--show-preview", help="Number of dry-run candidates to print (0=all)")] = 20,
    use_lightrag: Annotated[bool, typer.Option("--lightrag/--no-lightrag", help="Use LightRAG for semantic similarity (default: True)")] = True,
    lightrag_weight: Annotated[float, typer.Option("--lightrag-weight", help="Weight for LightRAG similarity in hybrid scoring (0.0-1.0, default: 0.6)")] = 0.6,
):
    """Link Code::* nodes to requirement Document nodes via LLM evaluation.

    Reads both code entities (developer persona) and business docs (business_analyst
    persona) from Neo4j for the given domain, then uses Vertex AI to evaluate which
    code implements/references/tests each requirement. Writes typed relationship edges
    back to Neo4j (idempotent — safe to re-run).

    With LightRAG enabled (default), also ingests entities into LightRAG for semantic
    embeddings and combines LightRAG similarity scores with LLM evaluation for hybrid
    confidence scoring.

    Run with --dry-run first to preview candidates before committing.

    Example:
        dva kg link --domain cwow-facility --dry-run
        dva kg link --domain cwow-facility --threshold 0.8
        dva kg link --domain cwow-facility --no-lightrag  # LLM-only mode
    """
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.linker import KGLinker

    config = KGConfig.load()
    if not config.is_neo4j_configured():
        console.print(f"[bold red]✗[/bold red] Neo4j is not configured.")
        console.print(f"  Run: {CLI_NAME} kg init --provider neo4j")
        raise typer.Exit(1)

    if not config.is_vertex_ai_configured():
        console.print(f"[bold red]✗[/bold red] Vertex AI is not configured.")
        console.print(f"  Run: {CLI_NAME} init vertex-ai")
        raise typer.Exit(1)

    mode_label = "[DRY RUN] " if dry_run else ""
    console.print(f"\n[bold]{mode_label}KG Linker — domain: [cyan]{domain}[/cyan][/bold]")
    console.print(f"  Confidence threshold: [cyan]{threshold}[/cyan]")
    console.print(f"  Batch size:           [cyan]{batch_size}[/cyan]")
    console.print(f"  LightRAG:             [cyan]{'enabled' if use_lightrag else 'disabled'}[/cyan]")
    if use_lightrag:
        console.print(f"  LightRAG weight:      [cyan]{lightrag_weight}[/cyan]")
    console.print()

    linker = KGLinker(
        domain=domain,
        config=config,
        confidence_threshold=threshold,
        batch_size=batch_size,
        use_lightrag=use_lightrag,
        lightrag_weight=lightrag_weight,
    )

    with console.status(f"[bold green]{'Evaluating (dry run)' if dry_run else 'Linking'}..."):
        try:
            result = linker.run(dry_run=dry_run)
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Linker failed: {e}")
            raise typer.Exit(1)

    # ── Print summary ─────────────────────────────────────────────────────────
    console.print(f"[bold green]✓[/bold green] Done\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="cyan")
    table.add_row("Domain", result.domain)
    table.add_row("Code entities", str(result.total_code_entities))
    table.add_row("Requirement docs", str(result.total_docs))
    table.add_row("Batches processed", str(result.batches_processed))
    table.add_row("Candidates found", str(result.candidates_found))
    table.add_row("Low confidence (skipped)", str(result.skipped_low_confidence))
    if dry_run:
        table.add_row("Edges written", "[yellow]DRY RUN — none written[/yellow]")
    else:
        table.add_row("Edges written", str(result.edges_written))
    console.print(table)

    # ── Errors ────────────────────────────────────────────────────────────────
    if result.errors:
        console.print()
        for err in result.errors:
            console.print(f"  [yellow]⚠[/yellow] {err}")

    # ── Dry-run preview ───────────────────────────────────────────────────────
    if dry_run and result.dry_run_preview:
        limit = show_preview if show_preview > 0 else len(result.dry_run_preview)
        console.print(f"\n[bold]Preview (top {min(limit, len(result.dry_run_preview))} candidates):[/bold]")
        preview_table = Table(show_header=True, box=None, padding=(0, 1))
        preview_table.add_column("Relationship", style="green", no_wrap=True)
        preview_table.add_column("Conf", style="cyan", no_wrap=True)
        preview_table.add_column("Code entity", no_wrap=True)
        preview_table.add_column("Requirement doc")
        preview_table.add_column("Evidence", overflow="fold")
        for item in result.dry_run_preview[:limit]:
            preview_table.add_row(
                item["relationship"],
                f"{item['confidence']:.2f}",
                item["code_id"][:40],
                item["doc_id"][:40],
                item["evidence"][:80],
            )
        console.print(preview_table)
        if len(result.dry_run_preview) > limit:
            console.print(f"  [dim]... and {len(result.dry_run_preview) - limit} more[/dim]")

    # ── Next steps ────────────────────────────────────────────────────────────
    if dry_run and result.candidates_found > 0:
        console.print(f"\n[dim]To write these edges:[/dim]")
        console.print(f"  {CLI_NAME} kg link --domain {domain} --threshold {threshold}")
    elif not dry_run and result.edges_written > 0:
        console.print(f"\n[dim]Query the graph:[/dim]")
        console.print(f"  {CLI_NAME} kg query \"what code implements HDF treatment requirements?\"")
        console.print(f"  {CLI_NAME} kg link --domain {domain} --dry-run  # verify idempotency")

    record_activity(
        command="kg",
        subcommand="link",
        status="success" if not result.errors else "partial",
        details={
            "domain": domain,
            "edges_written": result.edges_written,
        },
    )


@kg_app.command("refresh-links")
def refresh_links(
    path: Annotated[
        str,
        typer.Option("--path", "-p", help="Path to project directory"),
    ],
    domain: Annotated[
        str,
        typer.Option("--domain", "-d", help="Domain slug (e.g. cwow-facility)"),
    ],
) -> None:
    """Refresh code-to-requirement links for a project.

    Re-runs LLM-based linking between kg-code-context.md and KG requirements.
    Useful after code changes or requirement updates.

    Example:
        dva kg refresh-links --path ./my-project --domain cwow-facility
    """
    from pathlib import Path
    from agentic_cli.kg.context_builder import link_code_to_requirements

    project_path = Path(path).expanduser().resolve()
    if not project_path.exists():
        console.print(f"[red]✗[/red] Project path not found: {path}")
        raise typer.Exit(1)

    console.print(f"[cyan]Refreshing links for:[/cyan] {project_path.name}")
    console.print(f"[dim]Domain:[/dim] {domain}")
    console.print()

    try:
        result = link_code_to_requirements(
            project_path=project_path,
            domain_slug=domain,
        )

        if result["success"]:
            console.print(f"[green]✓[/green] Links refreshed successfully")
            console.print(f"  Links created: {result['links_created']}")
            if result.get("total_identified"):
                console.print(f"  Total identified: {result['total_identified']}")
        else:
            console.print(f"[red]✗[/red] Failed to refresh links")
            console.print(f"  Error: {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise typer.Exit(1)


@kg_app.command()
def execute(
    file: str | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to Cypher script file to execute",
    ),
    query: str | None = typer.Option(
        None,
        "--query",
        "-q",
        help="Single Cypher query to execute",
    ),
    domain: str | None = typer.Option(
        None,
        "--domain",
        help="Domain slug to tag executed nodes with domain metadata",
    ),
    source: str = typer.Option(
        "cypher_execute",
        "--source",
        help="Source name to tag with _source metadata (default: cypher_execute)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be executed without running",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="Continue execution if one query fails",
    ),
    skip_validation: bool = typer.Option(
        False,
        help="Skip connection validation",
        hidden=True,
    ),
) -> None:
    """
    Execute Cypher scripts or queries with optional domain tagging.
    
    This command allows you to execute Cypher scripts or single queries directly against Neo4j.
    You can tag executed nodes with domain and source metadata for better data management.
    
    Examples:
        # Execute Cypher script file
        {CLI_NAME} kg execute --file script.cypher
        
        # Execute with domain tagging
        {CLI_NAME} kg execute --file script.cypher --domain cwow-facility
        
        # Execute single query
        {CLI_NAME} kg execute --query "MATCH (n) RETURN n LIMIT 10"
        
        # Dry run to preview
        {CLI_NAME} kg execute --file script.cypher --dry-run
        
        # Continue on errors
        {CLI_NAME} kg execute --file script.cypher --continue-on-error
    """
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.neo4j_client import Neo4jClient
    
    # Validate that either file or query is provided
    if not file and not query:
        console.print("[bold red]✗ Error:[/bold red] Either --file or --query must be specified")
        raise typer.Exit(1)
    
    if file and query:
        console.print("[bold red]✗ Error:[/bold red] Cannot specify both --file and --query")
        raise typer.Exit(1)
    
    # Load configuration
    config = KGConfig.load()
    
    # Validate Neo4j connection
    if config.provider != "neo4j":
        console.print(f"[bold red]✗ Error:[/bold red] Execute command only supports Neo4j provider")
        console.print(f"[dim]Current provider: {config.provider}[/dim]")
        raise typer.Exit(1)
    
    if not validate_neo4j_connection(skip_check=skip_validation):
        raise typer.Exit(1)
    
    # Prepare queries
    queries = []
    if file:
        # Read Cypher script file
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[bold red]✗ Error:[/bold red] File not found: {file}")
            raise typer.Exit(1)
        
        script_content = file_path.read_text()
        
        # Better parsing: handle multi-line CREATE statements and semicolon-terminated statements
        queries = []
        current_query = []
        
        for line in script_content.split("\n"):
            stripped = line.strip()
            
            # Skip comment lines
            if stripped.startswith("//"):
                # If we have a current query, add it
                if current_query:
                    query = "\n".join(current_query).strip()
                    if query:
                        queries.append(query)
                    current_query = []
                continue
            
            # Remove inline comments
            if "//" in line:
                line = line.split("//")[0].strip()
            
            # Skip empty lines
            if not line.strip():
                continue
            
            current_query.append(line)
            
            # Check if line ends with semicolon (end of query)
            if line.strip().endswith(";"):
                query = "\n".join(current_query).strip()
                if query:
                    queries.append(query)
                current_query = []
        
        # Add any remaining query (multi-line CREATE without semicolon)
        if current_query:
            query = "\n".join(current_query).strip()
            if query:
                queries.append(query)
        
        console.print(f"[cyan]Loaded {len(queries)} queries from:[/cyan] {file}")
    else:
        queries = [query]
        console.print(f"[cyan]Executing single query[/cyan]")
    
    # Add domain metadata information
    if domain:
        console.print(f"[dim]Domain tagging:[/dim] {domain}")
    console.print(f"[dim]Source tagging:[/dim] {source}")
    
    if dry_run:
        console.print("\n[bold yellow]Dry run - queries that would be executed:[/bold yellow]\n")
        for i, q in enumerate(queries, 1):
            console.print(f"[cyan]{i}.[/cyan] {q}")
            # Show how domain metadata would be added (using same logic as execution)
            if domain:
                q_upper = q.upper()
                # Skip CONSTRAINT and INDEX statements entirely
                if "CONSTRAINT" in q_upper or "INDEX" in q_upper:
                    pass  # Don't add domain metadata to constraints/indexes
                # Skip MATCH + CREATE relationship patterns
                elif "MATCH" in q_upper and "CREATE" in q_upper:
                    pass  # Don't add domain metadata to relationship creation
                # Only apply to pure CREATE/MERGE node statements
                elif ("CREATE" in q_upper or "MERGE" in q_upper):
                    console.print(f"   [dim]Would add: SET n._source = '{source}', n.domain = '{domain}'[/dim]")
        console.print(f"\n[dim]Total queries: {len(queries)}[/dim]")
        return
    
    # Execute queries
    console.print("\n[bold]Executing queries...[/bold]\n")
    
    client = Neo4jClient(config=config)
    client.connect()
    
    success_count = 0
    error_count = 0
    
    try:
        for i, original_query in enumerate(queries, 1):
            query = original_query
            
            # Add domain metadata to CREATE/MERGE statements for nodes only
            # Skip CONSTRAINT, INDEX, and relationship creation statements
            if domain:
                query_upper = query.upper()
                # Skip CONSTRAINT and INDEX statements entirely
                if "CONSTRAINT" in query_upper or "INDEX" in query_upper:
                    pass  # Don't add domain metadata to constraints/indexes
                # Skip MATCH + CREATE relationship patterns
                elif "MATCH" in query_upper and "CREATE" in query_upper:
                    pass  # Don't add domain metadata to relationship creation
                # Only apply to pure CREATE/MERGE node statements
                elif ("CREATE" in query_upper or "MERGE" in query_upper):
                    # Skip if this creates multiple nodes (multiple CREATE statements)
                    # Count CREATE keywords - if more than 1, skip domain tagging
                    create_count = query_upper.count("CREATE")
                    if create_count > 1:
                        pass  # Skip domain tagging for multi-CREATE statements
                    # Check if this creates a node with properties (not just a label)
                    elif "(" in query and ")" in query:
                        # Insert SET clause before the semicolon, not after
                        # This works for: CREATE (n:Label {props}) SET n.domain = 'x';
                        # And for: CREATE (n:Label) SET n.domain = 'x';
                        
                        # Handle RETURN statement by inserting SET before RETURN
                        if "RETURN" in query_upper:
                            # Split on RETURN and insert SET clause before it
                            parts = query.split("RETURN", 1)
                            before_return = parts[0].strip()
                            after_return = parts[1].strip() if len(parts) > 1 else ""
                            
                            if "SET" not in before_return.upper():
                                query = f"{before_return} SET n._source = '{source}', n.domain = '{domain}' RETURN {after_return}"
                            else:
                                query = f"{before_return}, n._source = '{source}', n.domain = '{domain}' RETURN {after_return}"
                        else:
                            # No RETURN, insert SET clause before semicolon
                            if query.strip().endswith(";"):
                                # Remove semicolon, add SET, add semicolon back
                                query_without_semi = query.rstrip().rstrip(";").strip()
                                if "SET" not in query_without_semi.upper():
                                    query = f"{query_without_semi} SET n._source = '{source}', n.domain = '{domain}';"
                                else:
                                    query = f"{query_without_semi}, n._source = '{source}', n.domain = '{domain}';"
                            else:
                                # No semicolon, just append
                                if "SET" not in query_upper:
                                    query += f" SET n._source = '{source}', n.domain = '{domain}'"
                                else:
                                    query += f", n._source = '{source}', n.domain = '{domain}'"
            
            console.print(f"[cyan]{i}.[/cyan] {original_query[:100]}{'...' if len(original_query) > 100 else ''}")
            
            try:
                result = client.execute_cypher(query, parameters={})
                rows_affected = len(result) if result else 0
                console.print(f"   [green]✓[/green] Success - {rows_affected} rows affected")
                success_count += 1
            except Exception as e:
                console.print(f"   [red]✗[/red] Error: {str(e)}")
                error_count += 1
                if not continue_on_error:
                    console.print("\n[bold red]Stopping execution due to error[/bold red]")
                    console.print("[dim]Use --continue-on-error to continue on failures[/dim]")
                    break
    finally:
        client.close()
    
    # Summary
    console.print(f"\n[bold]Execution Summary:[/bold]")
    console.print(f"  Total queries: {len(queries)}")
    console.print(f"  [green]Successful:[/green] {success_count}")
    if error_count > 0:
        console.print(f"  [red]Failed:[/red] {error_count}")
    
    if error_count > 0:
        raise typer.Exit(1)

