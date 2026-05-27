"""Data source configuration commands."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_cli.tracker import record_activity
from agentic_cli.config import CLI_NAME

console = Console()
data_app = typer.Typer(help="Manage data source configurations", rich_markup_mode=None)

# Configuration file location (shared with init.py)
CONFIG_DIR = Path.home() / ".agent-cli-agentic"
CONFIG_FILE = CONFIG_DIR / "config.json"


def ensure_config_dir():
    """Ensure configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict):
    """Save configuration to file."""
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def ensure_data_config(config: dict) -> dict:
    """Ensure data section exists in config."""
    if "data" not in config:
        config["data"] = {
            "globals": {
                "gcs": {},
                "confluence": {}
            },
            "sources": []
        }
    if "globals" not in config["data"]:
        config["data"]["globals"] = {
            "gcs": {},
            "confluence": {}
        }
    if "gcs" not in config["data"]["globals"]:
        config["data"]["globals"]["gcs"] = {}
    if "confluence" not in config["data"]["globals"]:
        config["data"]["globals"]["confluence"] = {}
    if "sources" not in config["data"]:
        config["data"]["sources"] = []
    return config


def validate_source_location(source_type: str, location: str) -> tuple[bool, str]:
    """
    Validate source location based on type.
    
    Returns:
        (is_valid, message)
    """
    if source_type == "doc":
        # Check if it's a GCS path
        if location.startswith("gs://"):
            # Basic GCS path validation
            if len(location) <= 5:  # Just "gs://"
                return False, "GCS path must include bucket name"
            return True, "Valid GCS path format"
        else:
            # Local path - check if it exists (warning only)
            path = Path(location).expanduser().resolve()
            if not path.exists():
                return True, f"Warning: Local path does not exist: {path}"
            if not path.is_dir():
                return True, f"Warning: Path is not a directory: {path}"
            return True, "Valid local path"
    
    elif source_type == "confluence":
        # Basic URL validation
        if not location.startswith("http://") and not location.startswith("https://"):
            return False, "Confluence location must be a valid URL (http:// or https://)"
        return True, "Valid Confluence URL format"
    
    elif source_type == "git":
        # Git repository URL validation
        # Support https://, git://, git@, and ssh:// formats
        valid_prefixes = ("https://", "http://", "git://", "git@", "ssh://")
        if not any(location.startswith(prefix) for prefix in valid_prefixes):
            return False, "Git location must be a valid repository URL (https://, git://, git@, or ssh://)"
        
        # Basic validation for git@ format (e.g., git@github.com:user/repo.git)
        if location.startswith("git@"):
            if ":" not in location:
                return False, "Git SSH URL must include ':' separator (e.g., git@github.com:user/repo.git)"
        
        return True, "Valid Git repository URL format"
    
    return False, f"Unknown source type: {source_type}"


@data_app.command("init")
def init_data_config(
    gcs_project_id: Annotated[
        str,
        typer.Option(
            "--gcs-project-id",
            help="Google Cloud Project ID for GCS",
        ),
    ] = "",
    gcs_bucket: Annotated[
        str,
        typer.Option(
            "--gcs-bucket",
            help="Default GCS bucket name",
        ),
    ] = "",
    gcs_prefix: Annotated[
        str,
        typer.Option(
            "--gcs-prefix",
            help="Default GCS prefix/folder",
        ),
    ] = "",
    gcs_credentials_path: Annotated[
        str,
        typer.Option(
            "--gcs-credentials-path",
            help="Path to GCS service account credentials JSON file",
        ),
    ] = "",
    confluence_url: Annotated[
        str,
        typer.Option(
            "--confluence-url",
            help="Confluence base URL (e.g., https://your-domain/wiki)",
        ),
    ] = "",
    confluence_username: Annotated[
        str,
        typer.Option(
            "--confluence-username",
            help="Confluence username/email",
        ),
    ] = "",
    confluence_api_token_env: Annotated[
        str,
        typer.Option(
            "--confluence-api-token-env",
            help="Environment variable name for Confluence API token",
        ),
    ] = "CONFLUENCE_API_TOKEN",
) -> None:
    """
    Initialize global data configuration settings.
    
    Configure default settings for GCS and Confluence that will be used
    when creating data sources.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Data Configuration[/bold cyan]",
            border_style="cyan",
        )
    )
    
    # Load existing config
    config = load_config()
    config = ensure_data_config(config)
    
    # Track what was updated
    updated = []
    
    # Update GCS configuration
    if gcs_project_id:
        config["data"]["globals"]["gcs"]["project_id"] = gcs_project_id
        updated.append(f"GCS Project ID: {gcs_project_id}")
    
    if gcs_bucket:
        config["data"]["globals"]["gcs"]["default_bucket"] = gcs_bucket
        updated.append(f"GCS Bucket: {gcs_bucket}")
    
    if gcs_prefix:
        config["data"]["globals"]["gcs"]["default_prefix"] = gcs_prefix
        updated.append(f"GCS Prefix: {gcs_prefix}")
    
    if gcs_credentials_path:
        # Validate credentials file exists
        creds_path = Path(gcs_credentials_path).expanduser().resolve()
        if not creds_path.exists():
            console.print(
                f"[yellow]⚠ Warning:[/yellow] Credentials file not found: {creds_path}"
            )
        else:
            console.print(f"[green]✓[/green] Credentials file found: {creds_path}")
        config["data"]["globals"]["gcs"]["credentials_path"] = str(creds_path)
        updated.append(f"GCS Credentials: {creds_path}")
    
    # Update Confluence configuration
    if confluence_url:
        config["data"]["globals"]["confluence"]["base_url"] = confluence_url
        updated.append(f"Confluence URL: {confluence_url}")
    
    if confluence_username:
        config["data"]["globals"]["confluence"]["username"] = confluence_username
        updated.append(f"Confluence Username: {confluence_username}")
    
    if confluence_api_token_env:
        config["data"]["globals"]["confluence"]["api_token_env"] = confluence_api_token_env
        updated.append(f"Confluence Token Env: {confluence_api_token_env}")
    
    if not updated:
        console.print("[yellow]No configuration options provided.[/yellow]")
        console.print("[dim]Use --help to see available options.[/dim]")
        raise typer.Exit(0)
    
    # Save configuration
    save_config(config)
    
    console.print(
        Panel.fit(
            f"[bold green]✓ Configuration saved![/bold green]\n\n"
            f"[bold]Updated Settings:[/bold]\n" +
            "\n".join(f"  • {item}" for item in updated) +
            f"\n\n[dim]Config saved to: {CONFIG_FILE}[/dim]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  • Create data sources: {CLI_NAME} data create --name my-source ...\n"
            f"  • List sources: {CLI_NAME} data list (coming soon)",
            title="Success",
            border_style="green",
        )
    )


@data_app.command("create")
def create_data_source(
    name: Annotated[
        str,
        typer.Option(
            "--name",
            help="Unique name for this data source",
            prompt="Enter a unique name for this data source",
        ),
    ],
    source_type: Annotated[
        str,
        typer.Option(
            "--source-type",
            help="Type of data source (doc, confluence, git)",
            prompt="Enter source type (doc, confluence, git)",
        ),
    ],
    source_location: Annotated[
        str,
        typer.Option(
            "--source-location",
            help="Location of the data source (local path, gs:// URL, Confluence URL, or Git repository URL)",
            prompt="Enter source location",
        ),
    ],
    description: Annotated[
        str,
        typer.Option(
            "--description",
            help="Description of this data source",
        ),
    ] = "",
    tags: Annotated[
        str,
        typer.Option(
            "--tags",
            help="Comma-separated tags for this source",
        ),
    ] = "",
    git_branch: Annotated[
        str,
        typer.Option(
            "--git-branch",
            help="Git branch name (for git source type only)",
        ),
    ] = "",
    git_tag: Annotated[
        str,
        typer.Option(
            "--git-tag",
            help="Git tag name (for git source type only)",
        ),
    ] = "",
    project: Annotated[
        str,
        typer.Option(
            "--project",
            help="Project this source belongs to (e.g., cwow-patient). Used for KG workspace scoping.",
        ),
    ] = "",
    confluence_space: Annotated[
        str,
        typer.Option(
            "--confluence-space",
            help="Confluence space key (for confluence source type, e.g., CWOW)",
        ),
    ] = "",
) -> None:
    """
    Create a new data source configuration.
    
    Register a data source that can be used for ingestion into knowledge graphs
    or other data processing pipelines.
    
    Examples:
        {CLI_NAME} data create --name local-docs --source-type doc --source-location /path/to/docs
        {CLI_NAME} data create --name gcs-data --source-type doc --source-location gs://bucket/prefix
        {CLI_NAME} data create --name wiki --source-type confluence --source-location https://wiki.example.com/space
        {CLI_NAME} data create --name my-repo --source-type git --source-location https://github.com/user/repo.git --git-branch main
        {CLI_NAME} data create --name my-repo --source-type git --source-location git@github.com:user/repo.git --git-tag v1.0.0
    """.format(CLI_NAME=CLI_NAME)
    console.print(
        Panel.fit(
            f"[bold cyan]Creating Data Source[/bold cyan]\n"
            f"Name: {name}\n"
            f"Type: {source_type}",
            border_style="cyan",
        )
    )
    
    # Validate source type
    valid_types = ["doc", "confluence", "git"]
    if source_type not in valid_types:
        console.print(
            f"[red]✗ Error:[/red] Invalid source type '{source_type}'. "
            f"Must be one of: {', '.join(valid_types)}"
        )
        raise typer.Exit(1)
    
    # Validate source location
    is_valid, message = validate_source_location(source_type, source_location)
    if not is_valid:
        console.print(f"[red]✗ Error:[/red] {message}")
        raise typer.Exit(1)
    
    if "Warning" in message:
        console.print(f"[yellow]⚠[/yellow] {message}")
    else:
        console.print(f"[green]✓[/green] {message}")
    
    # Validate git-specific parameters
    if source_type == "git":
        if git_branch and git_tag:
            console.print(
                "[red]✗ Error:[/red] Cannot specify both --git-branch and --git-tag. "
                "Please use only one."
            )
            raise typer.Exit(1)
        
        if git_branch:
            console.print(f"[cyan]→[/cyan] Git branch: {git_branch}")
        elif git_tag:
            console.print(f"[cyan]→[/cyan] Git tag: {git_tag}")
        else:
            console.print("[dim]No branch or tag specified, will use default branch[/dim]")
    else:
        # Warn if git parameters are provided for non-git sources
        if git_branch or git_tag:
            console.print(
                f"[yellow]⚠ Warning:[/yellow] --git-branch and --git-tag are only applicable "
                f"for git source type (ignored for {source_type})"
            )
    
    # Load existing config
    config = load_config()
    config = ensure_data_config(config)
    
    # Check for duplicate name
    existing_names = [source["name"] for source in config["data"]["sources"]]
    if name in existing_names:
        console.print(
            f"[red]✗ Error:[/red] Data source with name '{name}' already exists."
        )
        console.print("[dim]Use a different name or delete the existing source first.[/dim]")
        raise typer.Exit(1)
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Validate confluence-specific parameters
    if source_type == "confluence" and not confluence_space:
        console.print(
            "[yellow]⚠ Warning:[/yellow] No --confluence-space provided. "
            "This is required for KG ingestion from Confluence."
        )
    elif source_type != "confluence" and confluence_space:
        console.print(
            f"[yellow]⚠ Warning:[/yellow] --confluence-space is only applicable "
            f"for confluence source type (ignored for {source_type})"
        )
    
    # Create new source entry
    new_source = {
        "name": name,
        "type": source_type,
        "location": source_location,
        "description": description,
        "tags": tag_list,
        "project": project,
        "kg_status": "registered",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    # Add confluence-specific metadata
    if source_type == "confluence" and confluence_space:
        new_source["confluence_space"] = confluence_space
    
    # Add git-specific metadata
    if source_type == "git":
        git_metadata = {}
        if git_branch:
            git_metadata["branch"] = git_branch
        if git_tag:
            git_metadata["tag"] = git_tag
        if git_metadata:
            new_source["git"] = git_metadata
    
    # Add to sources list
    config["data"]["sources"].append(new_source)
    
    # Save configuration
    save_config(config)

    record_activity(
        command="data", subcommand="create",
        args={"name": name, "type": source_type, "location": source_location},
    )
    
    # Display success message with table
    table = Table(title=f"Data Source: {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Name", name)
    table.add_row("Type", source_type)
    table.add_row("Location", source_location)
    if description:
        table.add_row("Description", description)
    if project:
        table.add_row("Project", project)
    if tag_list:
        table.add_row("Tags", ", ".join(tag_list))
    
    # Add git-specific fields to table
    if source_type == "git" and "git" in new_source:
        if "branch" in new_source["git"]:
            table.add_row("Git Branch", new_source["git"]["branch"])
        if "tag" in new_source["git"]:
            table.add_row("Git Tag", new_source["git"]["tag"])
    
    # Add confluence-specific fields
    if source_type == "confluence" and confluence_space:
        table.add_row("Confluence Space", confluence_space)
    
    table.add_row("KG Status", new_source["kg_status"])
    table.add_row("Created", new_source["created_at"])
    
    console.print()
    console.print(table)
    console.print()
    
    console.print(
        Panel.fit(
            f"[bold green]✓ Data source created successfully![/bold green]\n\n"
            f"[dim]Config saved to: {CONFIG_FILE}[/dim]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  • List all sources: {CLI_NAME} data list (coming soon)\n"
            f"  • Use in KG ingestion: {CLI_NAME} kg ingest --source {name} (future)",
            title="Success",
            border_style="green",
        )
    )


@data_app.command("list")
def list_data_sources() -> None:
    """
    List all configured data sources.
    """
    config = load_config()
    
    if "data" not in config or not config["data"].get("sources"):
        console.print("[yellow]No data sources configured.[/yellow]")
        console.print(f"[dim]Create one with: {CLI_NAME} data create[/dim]")
        return
    
    sources = config["data"]["sources"]
    
    table = Table(title=f"Data Sources ({len(sources)} total)")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Project", style="blue")
    table.add_column("Location", style="green")
    table.add_column("KG Status", style="yellow")
    table.add_column("Tags", style="dim")
    
    for source in sources:
        tags_str = ", ".join(source.get("tags", [])) if source.get("tags") else "-"
        location = source["location"]
        # Truncate long locations
        if len(location) > 40:
            location = location[:37] + "..."
        
        table.add_row(
            source["name"],
            source["type"],
            source.get("project", "-") or "-",
            location,
            source.get("kg_status", "-") or "-",
            tags_str
        )
    
    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Config file: {CONFIG_FILE}[/dim]")


@data_app.command("show")
def show_data_source(
    name: Annotated[str, typer.Argument(help="Name of the data source to show")],
) -> None:
    """
    Show detailed information about a specific data source.
    """
    config = load_config()
    
    if "data" not in config or not config["data"].get("sources"):
        console.print("[yellow]No data sources configured.[/yellow]")
        raise typer.Exit(1)
    
    # Find the source
    source = None
    for s in config["data"]["sources"]:
        if s["name"] == name:
            source = s
            break
    
    if not source:
        console.print(f"[red]✗ Error:[/red] Data source '{name}' not found.")
        console.print("[dim]Use f'{CLI_NAME} data list' to see all sources.[/dim]")
        raise typer.Exit(1)
    
    # Display detailed information
    table = Table(title=f"Data Source: {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Name", source["name"])
    table.add_row("Type", source["type"])
    table.add_row("Location", source["location"])
    table.add_row("Description", source.get("description", "-"))
    table.add_row("Project", source.get("project", "-") or "-")
    table.add_row("Tags", ", ".join(source.get("tags", [])) if source.get("tags") else "-")
    table.add_row("KG Status", source.get("kg_status", "-") or "-")
    
    # Add git-specific fields if present
    if source["type"] == "git" and "git" in source:
        if "branch" in source["git"]:
            table.add_row("Git Branch", source["git"]["branch"])
        if "tag" in source["git"]:
            table.add_row("Git Tag", source["git"]["tag"])
    
    # Add confluence-specific fields if present
    if source["type"] == "confluence" and source.get("confluence_space"):
        table.add_row("Confluence Space", source["confluence_space"])
    
    table.add_row("Created", source.get("created_at", "Unknown"))
    
    console.print()
    console.print(table)


@data_app.command("delete")
def delete_data_source(
    name: Annotated[str, typer.Argument(help="Name of the data source to delete")],
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            help="Skip confirmation prompt",
        ),
    ] = False,
) -> None:
    """
    Delete a data source configuration.
    """
    config = load_config()
    
    if "data" not in config or not config["data"].get("sources"):
        console.print("[yellow]No data sources configured.[/yellow]")
        raise typer.Exit(1)
    
    # Find the source
    source_index = None
    for i, s in enumerate(config["data"]["sources"]):
        if s["name"] == name:
            source_index = i
            break
    
    if source_index is None:
        console.print(f"[red]✗ Error:[/red] Data source '{name}' not found.")
        raise typer.Exit(1)
    
    # Confirm deletion
    if not yes:
        from rich.prompt import Confirm
        if not Confirm.ask(f"Are you sure you want to delete data source '{name}'?"):
            console.print("[dim]Operation cancelled.[/dim]")
            raise typer.Exit(0)
    
    # Remove the source
    config["data"]["sources"].pop(source_index)
    save_config(config)

    record_activity(command="data", subcommand="delete", args={"name": name})
    
    console.print(f"[bold green]\u2713[/bold green] Data source '{name}' deleted successfully")


@data_app.command("update")
def update_data_source(
    name: Annotated[str, typer.Argument(help="Name of the data source to update")],
    source_location: Annotated[
        str,
        typer.Option(
            "--source-location",
            help="New location for the data source",
        ),
    ] = "",
    description: Annotated[
        str,
        typer.Option(
            "--description",
            help="New description",
        ),
    ] = "",
    tags: Annotated[
        str,
        typer.Option(
            "--tags",
            help="New comma-separated tags (replaces existing)",
        ),
    ] = "",
) -> None:
    """
    Update an existing data source configuration.
    """
    config = load_config()
    
    if "data" not in config or not config["data"].get("sources"):
        console.print("[yellow]No data sources configured.[/yellow]")
        raise typer.Exit(1)
    
    # Find the source
    source = None
    for s in config["data"]["sources"]:
        if s["name"] == name:
            source = s
            break
    
    if not source:
        console.print(f"[red]\u2717[/red] Data source '{name}' not found.")
        raise typer.Exit(1)
    
    # Track updates
    updated = []
    
    if source_location:
        # Validate new location
        is_valid, message = validate_source_location(source["type"], source_location)
        if not is_valid:
            console.print(f"[red]\u2717[/red] {message}")
            raise typer.Exit(1)
        
        source["location"] = source_location
        updated.append(f"Location: {source_location}")
    
    if description:
        source["description"] = description
        updated.append(f"Description: {description}")
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        source["tags"] = tag_list
        updated.append(f"Tags: {', '.join(tag_list)}")
    
    if not updated:
        console.print("[yellow]No updates provided.[/yellow]")
        console.print("[dim]Use --help to see available options.[/dim]")
        raise typer.Exit(0)
    
    # Save configuration
    save_config(config)

    record_activity(command="data", subcommand="update", args={"name": name, "updates": updated})
    
    console.print(f"[bold green]\u2713[/bold green] Data source '{name}' updated successfully")
    for item in updated:
        console.print(f"  • {item}")
