"""MCP (Model Context Protocol) server management commands."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli.mcp.config import (
    MCPServer,
    MCPServerType,
    MCPTransport,
    MCPRegistry,
    MCPProjectConfig,
    DockerConfig,
    load_registry,
    save_registry,
    load_project_config,
    save_project_config,
    get_merged_servers,
    validate_server_config,
    PROJECT_MCP_DIR,
)

from agentic_cli.config import CLI_NAME
from agentic_cli.tracker import record_activity

console = Console()
mcp_app = typer.Typer(help="Manage MCP (Model Context Protocol) servers", rich_markup_mode=None)


@mcp_app.command("init")
def init_mcp(
    workspace: Annotated[
        Optional[Path],
        typer.Option("--workspace", "-w", help="Workspace path (default: current directory)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing configuration"),
    ] = False,
) -> None:
    """Initialize MCP configuration in the current workspace."""
    base = workspace or Path.cwd()
    mcp_dir = base / PROJECT_MCP_DIR
    config_file = mcp_dir / "mcp.json"
    
    if config_file.exists() and not force:
        console.print(f"[yellow]MCP configuration already exists at {config_file}[/yellow]")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)
    
    # Create default project config
    config = MCPProjectConfig(
        version="1.0",
        inherit_global=True,
        servers={},
    )
    
    config_path = save_project_config(config, base)

    console.print(Panel(
        f"[green]✓[/green] Initialized MCP configuration at [cyan]{config_path}[/cyan]\n\n"
        "Next steps:\n"
        f"  1. Add servers: [cyan]{CLI_NAME} mcp add <name> --type <type> ...[/cyan]\n"
        f"  2. List servers: [cyan]{CLI_NAME} mcp list[/cyan]\n"
        f"  3. Sync to IDE: [cyan]{CLI_NAME} mcp sync --ide windsurf[/cyan]",
        title="MCP Initialized",
    ))


@mcp_app.command("add")
def add_server(
    name: Annotated[str, typer.Argument(help="Unique server identifier")],
    server_type: Annotated[
        MCPServerType,
        typer.Option("--type", "-t", help="Server type"),
    ] = MCPServerType.STDIO,
    display_name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Display name"),
    ] = None,
    command: Annotated[
        Optional[str],
        typer.Option("--command", "-c", help="Command for stdio servers"),
    ] = None,
    args: Annotated[
        Optional[str],
        typer.Option("--args", "-a", help="Command arguments (comma-separated or space-separated)"),
    ] = None,
    url: Annotated[
        Optional[str],
        typer.Option("--url", "-u", help="URL for HTTP/SSE servers"),
    ] = None,
    compose: Annotated[
        Optional[Path],
        typer.Option("--compose", help="Docker compose file path"),
    ] = None,
    service: Annotated[
        Optional[str],
        typer.Option("--service", help="Docker service name"),
    ] = None,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port for Docker servers"),
    ] = 8125,
    env: Annotated[
        Optional[list[str]],
        typer.Option("--env", "-e", help="Environment variables (KEY=VALUE)"),
    ] = None,
    tools: Annotated[
        Optional[str],
        typer.Option("--tools", help="Available tools (comma-separated)"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Server description"),
    ] = None,
    project: Annotated[
        bool,
        typer.Option("--project", help="Add to project config instead of global"),
    ] = False,
) -> None:
    """Add a new MCP server configuration."""
    # Parse arguments
    args_list = []
    if args:
        # Support both comma and space separation
        if "," in args:
            args_list = [a.strip() for a in args.split(",")]
        else:
            args_list = args.split()
    
    # Parse environment variables
    env_dict = {}
    if env:
        for e in env:
            if "=" in e:
                key, value = e.split("=", 1)
                env_dict[key] = value
    
    # Parse tools
    tools_list = []
    if tools:
        tools_list = [t.strip() for t in tools.split(",")]
    
    # Build server config
    now = datetime.now(timezone.utc).isoformat()
    server = MCPServer(
        name=display_name or name,
        type=server_type,
        enabled=True,
        command=command,
        args=args_list,
        url=url,
        env=env_dict,
        tools=tools_list,
        description=description,
        created_at=now,
        updated_at=now,
    )
    
    # Add Docker config if applicable
    if server_type == MCPServerType.DOCKER:
        if not compose:
            console.print("[red]Error:[/red] Docker servers require --compose")
            raise typer.Exit(1)
        
        compose_path = compose.expanduser().resolve()
        server.docker = DockerConfig(
            compose_file=str(compose_path),
            service=service,
            port=port,
        )
        server.url = url or f"http://localhost:{port}"
        server.transport = MCPTransport.HTTP
    
    elif server_type == MCPServerType.STDIO:
        if not command:
            console.print("[red]Error:[/red] STDIO servers require --command")
            raise typer.Exit(1)
        server.transport = MCPTransport.STDIO
    
    elif server_type in (MCPServerType.HTTP, MCPServerType.SSE):
        if not url:
            console.print("[red]Error:[/red] HTTP/SSE servers require --url")
            raise typer.Exit(1)
        server.transport = MCPTransport.HTTP if server_type == MCPServerType.HTTP else MCPTransport.SSE
    
    # Validate
    valid, msg = validate_server_config(server)
    if not valid:
        console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(1)
    
    if project:
        # Add to project config
        config = load_project_config() or MCPProjectConfig()
        if name in config.servers:
            console.print(f"[yellow]Warning:[/yellow] Server '{name}' already exists, updating...")
        config.servers[name] = server.model_dump(exclude_none=True)
        save_project_config(config)
        console.print(f"[green]✓[/green] Added server '{name}' to project configuration")
    else:
        # Add to global registry
        registry = load_registry()
        if name in registry.servers:
            console.print(f"[yellow]Warning:[/yellow] Server '{name}' already exists, updating...")
        registry.servers[name] = server
        save_registry(registry)
        console.print(f"[green]✓[/green] Added server '{name}' to global registry")

    record_activity(
        command="mcp", subcommand="add",
        args={"name": name, "type": server_type, "project": project},
    )
    
    # Show server details
    _show_server_details(name, server)


@mcp_app.command("remove")
def remove_server(
    name: Annotated[str, typer.Argument(help="Server identifier to remove")],
    project: Annotated[
        bool,
        typer.Option("--project", help="Remove from project config instead of global"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation"),
    ] = False,
) -> None:
    """Remove an MCP server configuration."""
    if project:
        config = load_project_config()
        if not config or name not in config.servers:
            console.print(f"[red]Error:[/red] Server '{name}' not found in project configuration")
            raise typer.Exit(1)
        
        if not yes:
            confirm = typer.confirm(f"Remove server '{name}' from project configuration?")
            if not confirm:
                raise typer.Abort()
        
        del config.servers[name]
        save_project_config(config)
        record_activity(command="mcp", subcommand="remove", args={"name": name, "project": True})
        console.print(f"[green]✓[/green] Removed server '{name}' from project configuration")
    else:
        registry = load_registry()
        if name not in registry.servers:
            console.print(f"[red]Error:[/red] Server '{name}' not found in global registry")
            raise typer.Exit(1)
        
        if not yes:
            confirm = typer.confirm(f"Remove server '{name}' from global registry?")
            if not confirm:
                raise typer.Abort()
        
        del registry.servers[name]
        save_registry(registry)
        record_activity(command="mcp", subcommand="remove", args={"name": name, "project": False})
        console.print(f"[green]✓[/green] Removed server '{name}' from global registry")


@mcp_app.command("list")
def list_servers(
    all_servers: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all servers including disabled"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """List all configured MCP servers."""
    servers = get_merged_servers()
    
    if not all_servers:
        servers = {k: v for k, v in servers.items() if v.enabled}
    
    if not servers:
        console.print("[yellow]No MCP servers configured[/yellow]")
        console.print(f"Add a server with: [cyan]{CLI_NAME} mcp add <name> --type <type> ...[/cyan]")
        return
    
    if json_output:
        import json
        data = {k: v.model_dump(exclude_none=True) for k, v in servers.items()}
        console.print(json.dumps(data, indent=2))
        return
    
    table = Table(title="MCP Servers")
    table.add_column("Key", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Endpoint", style="dim")
    
    for key, server in servers.items():
        status = "[green]✓[/green]" if server.enabled else "[red]✗[/red]"
        
        if server.type == MCPServerType.STDIO:
            endpoint = f"{server.command} {' '.join(server.args[:2])}..."[:40]
        elif server.type == MCPServerType.DOCKER:
            endpoint = f"docker:{server.docker.port}" if server.docker else "docker"
        else:
            endpoint = server.url or "-"
        
        table.add_row(
            key,
            server.name,
            server.type.value,
            status,
            endpoint[:50],
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(servers)} server(s)[/dim]")


@mcp_app.command("show")
def show_server(
    name: Annotated[str, typer.Argument(help="Server identifier")],
) -> None:
    """Show detailed information about an MCP server."""
    servers = get_merged_servers()
    
    if name not in servers:
        # Check global registry
        registry = load_registry()
        if name in registry.servers:
            server = registry.servers[name]
        else:
            console.print(f"[red]Error:[/red] Server '{name}' not found")
            raise typer.Exit(1)
    else:
        server = servers[name]
    
    _show_server_details(name, server)


def _show_server_details(key: str, server: MCPServer) -> None:
    """Display server details in a panel."""
    lines = [
        f"[bold]Name:[/bold] {server.name}",
        f"[bold]Type:[/bold] {server.type.value}",
        f"[bold]Enabled:[/bold] {'Yes' if server.enabled else 'No'}",
        f"[bold]Transport:[/bold] {server.transport.value}",
    ]
    
    if server.type == MCPServerType.STDIO:
        lines.append(f"[bold]Command:[/bold] {server.command}")
        if server.args:
            lines.append(f"[bold]Args:[/bold] {' '.join(server.args)}")
    
    elif server.type in (MCPServerType.HTTP, MCPServerType.SSE):
        lines.append(f"[bold]URL:[/bold] {server.url}")
    
    elif server.type == MCPServerType.DOCKER:
        if server.docker:
            lines.append(f"[bold]Compose:[/bold] {server.docker.compose_file}")
            if server.docker.service:
                lines.append(f"[bold]Service:[/bold] {server.docker.service}")
            lines.append(f"[bold]Port:[/bold] {server.docker.port}")
        if server.url:
            lines.append(f"[bold]URL:[/bold] {server.url}")
    
    if server.env:
        env_str = ", ".join(f"{k}=***" if "TOKEN" in k or "KEY" in k or "PASSWORD" in k else f"{k}={v}" 
                           for k, v in server.env.items())
        lines.append(f"[bold]Env:[/bold] {env_str}")
    
    if server.tools:
        lines.append(f"[bold]Tools:[/bold] {', '.join(server.tools)}")
    
    if server.description:
        lines.append(f"[bold]Description:[/bold] {server.description}")
    
    if server.created_at:
        lines.append(f"[bold]Created:[/bold] {server.created_at}")
    
    console.print(Panel("\n".join(lines), title=f"Server: {key}"))


@mcp_app.command("start")
def start_servers(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Server to start (all Docker servers if not specified)"),
    ] = None,
) -> None:
    """Start Docker-based MCP server(s)."""
    from agentic_cli.mcp.docker import (
        check_docker_running,
        start_server,
        start_all_docker_servers,
        get_docker_servers,
    )
    
    # Check Docker
    docker_ok, docker_msg = check_docker_running()
    if not docker_ok:
        console.print(f"[red]Error:[/red] {docker_msg}")
        console.print("Please ensure Docker is installed and running")
        raise typer.Exit(1)
    
    if name:
        servers = get_merged_servers()
        if name not in servers:
            console.print(f"[red]Error:[/red] Server '{name}' not found")
            raise typer.Exit(1)
        
        server = servers[name]
        if server.type != MCPServerType.DOCKER:
            console.print(f"[yellow]Warning:[/yellow] Server '{name}' is not a Docker server (type: {server.type.value})")
            console.print("Only Docker servers can be started with this command")
            raise typer.Exit(1)
        
        console.print(f"Starting server '{name}'...")
        success, msg = start_server(server)
        if success:
            console.print(f"[green]✓[/green] {msg}")
        else:
            console.print(f"[red]✗[/red] {msg}")
            raise typer.Exit(1)
    else:
        # Start all Docker servers
        docker_servers = get_docker_servers()
        if not docker_servers:
            console.print("[yellow]No Docker-based MCP servers configured[/yellow]")
            return
        
        console.print(f"Starting {len(docker_servers)} Docker server(s)...")
        results = start_all_docker_servers()
        
        for key, (success, msg) in results.items():
            if success:
                console.print(f"  [green]✓[/green] {key}: {msg}")
            else:
                console.print(f"  [red]✗[/red] {key}: {msg}")


@mcp_app.command("stop")
def stop_servers(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Server to stop (all Docker servers if not specified)"),
    ] = None,
) -> None:
    """Stop Docker-based MCP server(s)."""
    from agentic_cli.mcp.docker import (
        stop_server,
        stop_all_docker_servers,
        get_docker_servers,
    )
    
    if name:
        servers = get_merged_servers()
        if name not in servers:
            console.print(f"[red]Error:[/red] Server '{name}' not found")
            raise typer.Exit(1)
        
        server = servers[name]
        if server.type != MCPServerType.DOCKER:
            console.print(f"[yellow]Warning:[/yellow] Server '{name}' is not a Docker server")
            raise typer.Exit(1)
        
        console.print(f"Stopping server '{name}'...")
        success, msg = stop_server(server)
        if success:
            console.print(f"[green]✓[/green] {msg}")
        else:
            console.print(f"[red]✗[/red] {msg}")
            raise typer.Exit(1)
    else:
        docker_servers = get_docker_servers()
        if not docker_servers:
            console.print("[yellow]No Docker-based MCP servers configured[/yellow]")
            return
        
        console.print(f"Stopping {len(docker_servers)} Docker server(s)...")
        results = stop_all_docker_servers()
        
        for key, (success, msg) in results.items():
            if success:
                console.print(f"  [green]✓[/green] {key}: {msg}")
            else:
                console.print(f"  [red]✗[/red] {key}: {msg}")


@mcp_app.command("health")
def check_health(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Server to check (all servers if not specified)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """Check health of MCP server(s)."""
    from agentic_cli.mcp.health import check_server_health, get_health_summary
    
    if name:
        servers = get_merged_servers()
        if name not in servers:
            console.print(f"[red]Error:[/red] Server '{name}' not found")
            raise typer.Exit(1)
        
        server = servers[name]
        result = check_server_health(server)
        result["key"] = name
        
        if json_output:
            import json
            console.print(json.dumps(result, indent=2))
        else:
            _display_health_result(result)
    else:
        summary = get_health_summary()
        
        if json_output:
            import json
            console.print(json.dumps(summary, indent=2))
            return
        
        table = Table(title="MCP Server Health")
        table.add_column("Server", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="white")
        table.add_column("Health", style="white")
        table.add_column("Message", style="dim")
        
        for result in summary["servers"]:
            health_icon = "[green]✓[/green]" if result["healthy"] else "[red]✗[/red]"
            if result["status"] == "disabled":
                health_icon = "[dim]-[/dim]"
            
            table.add_row(
                result.get("key", result["name"]),
                result["type"],
                result["status"],
                health_icon,
                result["message"][:50],
            )
        
        console.print(table)
        console.print(f"\n[dim]Healthy: {summary['healthy']}/{summary['total']} | "
                     f"Unhealthy: {summary['unhealthy']} | Disabled: {summary['disabled']}[/dim]")


def _display_health_result(result: dict) -> None:
    """Display a single health check result."""
    health_icon = "[green]✓ Healthy[/green]" if result["healthy"] else "[red]✗ Unhealthy[/red]"
    if result["status"] == "disabled":
        health_icon = "[dim]- Disabled[/dim]"
    
    lines = [
        f"[bold]Server:[/bold] {result.get('key', result['name'])}",
        f"[bold]Type:[/bold] {result['type']}",
        f"[bold]Status:[/bold] {result['status']}",
        f"[bold]Health:[/bold] {health_icon}",
        f"[bold]Message:[/bold] {result['message']}",
    ]
    
    if result.get("details"):
        lines.append("[bold]Details:[/bold]")
        for key, value in result["details"].items():
            lines.append(f"  {key}: {value}")
    
    console.print(Panel("\n".join(lines), title="Health Check"))


@mcp_app.command("sync")
def sync_ide(
    ide: Annotated[
        Optional[str],
        typer.Option("--ide", "-i", help="IDE to sync (windsurf, claude, vscode, cursor)"),
    ] = None,
    all_ides: Annotated[
        bool,
        typer.Option("--all", "-a", help="Sync to all supported IDEs"),
    ] = False,
    global_config: Annotated[
        bool,
        typer.Option("--global", "-g", help="Write to global IDE config instead of workspace"),
    ] = False,
    workspace: Annotated[
        Optional[Path],
        typer.Option("--workspace", "-w", help="Workspace path"),
    ] = None,
) -> None:
    """Sync MCP configuration to IDE-specific format."""
    from agentic_cli.mcp.sync import sync_to_ide, sync_all_ides, IDE_GENERATORS
    
    if not ide and not all_ides:
        console.print("[yellow]Please specify --ide or --all[/yellow]")
        console.print(f"Supported IDEs: {', '.join(IDE_GENERATORS.keys())}")
        raise typer.Exit(1)
    
    if all_ides:
        console.print("Syncing to all IDEs...")
        results = sync_all_ides(workspace)
        for ide_name, path in results.items():
            if path:
                console.print(f"  [green]✓[/green] {ide_name}: {path}")
            else:
                console.print(f"  [red]✗[/red] {ide_name}: Failed")
    else:
        try:
            path = sync_to_ide(ide, workspace, global_config)
            console.print(f"[green]✓[/green] Synced to {ide}: {path}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to sync: {e}")
            raise typer.Exit(1)


# CLI `.env` key → MCP-stack `.env` key. Same name unless the MCP server reads
# a differently-named variable (e.g. Glean's base URL is GLEAN_DOMAIN, not
# GLEAN_API_URL). Grouped by integration for the --only filter.
_MCP_ENV_MAP: dict[str, list[tuple[str, str]]] = {
    "bitbucket": [
        ("BITBUCKET_SERVER_URL", "BITBUCKET_SERVER_URL"),
        ("BITBUCKET_PERSONAL_ACCESS_TOKEN", "BITBUCKET_PERSONAL_ACCESS_TOKEN"),
        ("BITBUCKET_DEFAULT_PROJECT", "BITBUCKET_DEFAULT_PROJECT"),
    ],
    "jira": [
        ("JIRA_SERVER_URL", "JIRA_SERVER_URL"),
        ("JIRA_PERSONAL_ACCESS_TOKEN", "JIRA_PERSONAL_ACCESS_TOKEN"),
        ("JIRA_DEFAULT_PROJECT", "JIRA_DEFAULT_PROJECT"),
    ],
    "confluence": [
        ("CONFLUENCE_SERVER_URL", "CONFLUENCE_SERVER_URL"),
        ("CONFLUENCE_PERSONAL_ACCESS_TOKEN", "CONFLUENCE_PERSONAL_ACCESS_TOKEN"),
        ("CONFLUENCE_DEFAULT_SPACE", "CONFLUENCE_DEFAULT_SPACE"),
    ],
    "glean": [
        ("GLEAN_API_TOKEN", "GLEAN_API_TOKEN"),
        ("GLEAN_API_URL", "GLEAN_DOMAIN"),  # CLI base-URL var → MCP base-URL var
        # SSO/OAuth client-credentials — the MCP now supports these too, so the
        # CLI and the Dockerized MCP authenticate to Glean the same way.
        ("GLEAN_AUTH_MODE", "GLEAN_AUTH_MODE"),
        ("GLEAN_OAUTH_ISSUER", "GLEAN_OAUTH_ISSUER"),
        ("GLEAN_OAUTH_CLIENT_ID", "GLEAN_OAUTH_CLIENT_ID"),
        ("GLEAN_OAUTH_CLIENT_SECRET", "GLEAN_OAUTH_CLIENT_SECRET"),
        ("GLEAN_OAUTH_SCOPE", "GLEAN_OAUTH_SCOPE"),
        ("GLEAN_OAUTH_TOKEN_URL", "GLEAN_OAUTH_TOKEN_URL"),
    ],
}

_SECRET_HINTS = ("TOKEN", "SECRET", "KEY", "PASSWORD")


def _find_mcp_dir(explicit: Optional[Path]) -> Optional[Path]:
    """Locate the MCP stack dir (holding docker-compose.yml + .env)."""
    if explicit:
        return explicit.expanduser().resolve()
    cur = Path.cwd().resolve()
    for directory in [cur, *cur.parents]:
        candidate = directory / "mcp-servers"
        if (candidate / "docker-compose.yml").is_file():
            return candidate
    return None


@mcp_app.command("sync-env")
def sync_env(
    only: Annotated[
        Optional[str],
        typer.Option("--only", "-o", help="Comma-separated integrations to sync (glean,jira,confluence,bitbucket)"),
    ] = None,
    mcp_dir: Annotated[
        Optional[Path],
        typer.Option("--mcp-dir", help="Path to the mcp-servers directory (auto-detected by default)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be written without modifying the file"),
    ] = False,
) -> None:
    """Copy integration credentials from the CLI env into the MCP stack's .env.

    Reads the CLI's resolved config (``~/.keel/.env`` then project ``./.env``)
    and writes the matching variables into ``mcp-servers/.env`` so the Dockerized
    MCP servers authenticate with the same credentials configured via
    ``keel init``. Glean's ``GLEAN_API_URL`` is remapped to the MCP's
    ``GLEAN_DOMAIN``.
    """
    import os

    from agentic_cli.env import load_env, mask, set_env_vars

    # Ensure the CLI .env files are loaded into the environment.
    load_env()

    target_dir = _find_mcp_dir(mcp_dir)
    if not target_dir:
        console.print("[red]✗[/red] Could not find an [cyan]mcp-servers/[/cyan] directory "
                      "(with docker-compose.yml). Pass [cyan]--mcp-dir[/cyan].")
        raise typer.Exit(1)
    env_path = target_dir / ".env"

    groups = list(_MCP_ENV_MAP.keys())
    if only:
        requested = {g.strip().lower() for g in only.split(",") if g.strip()}
        unknown = requested - set(groups)
        if unknown:
            console.print(f"[red]✗[/red] Unknown integration(s): {', '.join(sorted(unknown))}. "
                          f"Valid: {', '.join(groups)}")
            raise typer.Exit(1)
        groups = [g for g in groups if g in requested]

    updates: dict[str, str] = {}
    skipped_empty: list[str] = []
    for group in groups:
        for cli_key, mcp_key in _MCP_ENV_MAP[group]:
            val = (os.environ.get(cli_key) or "").strip()
            if val:
                updates[mcp_key] = val
            else:
                skipped_empty.append(cli_key)

    # Glean MCP now supports SSO (OAuth client-credentials) as well as a static
    # token. Warn only if neither a token nor usable OAuth client-credentials are
    # present, since then the MCP has nothing to authenticate with.
    if "glean" in groups:
        mode = (os.environ.get("GLEAN_AUTH_MODE", "token").strip() or "token").lower()
        has_token = bool((os.environ.get("GLEAN_API_TOKEN") or "").strip())
        has_cc = bool((os.environ.get("GLEAN_OAUTH_CLIENT_ID") or "").strip()
                      and (os.environ.get("GLEAN_OAUTH_CLIENT_SECRET") or "").strip())
        if mode == "sso" and not has_cc:
            console.print("[yellow]![/yellow] CLI Glean is in [bold]SSO[/bold] mode but "
                          "GLEAN_OAUTH_CLIENT_ID/SECRET are not both set. The Glean MCP's SSO "
                          "path needs a static OAuth client (keel init glean --sso --client-id <> "
                          "--client-secret <>).")
        elif mode != "sso" and not has_token:
            console.print("[yellow]![/yellow] CLI Glean is in token mode but GLEAN_API_TOKEN is "
                          "empty. Set a token (keel init glean --token <>) or switch to --sso.")

    if not updates:
        console.print("[yellow]Nothing to sync[/yellow] — no matching non-empty variables found in the CLI env.")
        if skipped_empty:
            console.print(f"[dim]Empty in CLI env: {', '.join(sorted(set(skipped_empty)))}[/dim]")
        raise typer.Exit(1)

    table = Table(title=f"Sync → {env_path}")
    table.add_column("MCP variable", style="cyan")
    table.add_column("Value", style="white")
    for key in sorted(updates):
        shown = mask(updates[key]) if any(h in key for h in _SECRET_HINTS) else updates[key]
        table.add_row(key, shown)
    console.print(table)

    if dry_run:
        console.print("[dim]--dry-run: no changes written.[/dim]")
        return

    if not env_path.exists():
        console.print(f"[dim]Creating {env_path} (chmod 600)…[/dim]")
    set_env_vars(updates, path=env_path)
    console.print(f"[green]✓[/green] Wrote {len(updates)} variable(s) to [cyan]{env_path}[/cyan]")
    console.print("[dim]Recreate the affected containers to pick up changes, e.g.:[/dim]")
    console.print(f"[dim]  docker compose -f {target_dir / 'docker-compose.yml'} up -d --force-recreate[/dim]")

    record_activity(command="mcp", subcommand="sync-env",
                    args={"groups": groups, "count": len(updates)})


@mcp_app.command("import")
def import_config(
    source: Annotated[
        Path,
        typer.Option("--from", "-f", help="Source config file path"),
    ],
    ide: Annotated[
        str,
        typer.Option("--ide", "-i", help="Source IDE format (windsurf, claude, vscode, cursor)"),
    ] = "windsurf",
    merge: Annotated[
        bool,
        typer.Option("--merge", "-m", help="Merge with existing servers instead of replacing"),
    ] = True,
) -> None:
    """Import MCP servers from an existing IDE configuration."""
    from agentic_cli.mcp.sync import import_from_ide
    
    if not source.exists():
        console.print(f"[red]Error:[/red] Source file not found: {source}")
        raise typer.Exit(1)
    
    try:
        imported = import_from_ide(ide, source)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to import: {e}")
        raise typer.Exit(1)
    
    if not imported:
        console.print("[yellow]No servers found in source configuration[/yellow]")
        return
    
    registry = load_registry()
    
    added = 0
    updated = 0
    for key, server in imported.items():
        if key in registry.servers:
            if merge:
                updated += 1
            else:
                continue
        else:
            added += 1
        registry.servers[key] = server
    
    save_registry(registry)
    
    console.print(f"[green]✓[/green] Imported {len(imported)} server(s)")
    console.print(f"  Added: {added}, Updated: {updated}")
    
    # Show imported servers
    table = Table(title="Imported Servers")
    table.add_column("Key", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="magenta")
    
    for key, server in imported.items():
        table.add_row(key, server.name, server.type.value)
    
    console.print(table)


@mcp_app.command("logs")
def show_logs(
    name: Annotated[str, typer.Argument(help="Docker server to show logs for")],
    lines: Annotated[
        int,
        typer.Option("--lines", "-n", help="Number of lines to show"),
    ] = 50,
    follow: Annotated[
        bool,
        typer.Option("--follow", "-f", help="Follow log output"),
    ] = False,
) -> None:
    """Show logs from a Docker-based MCP server."""
    from agentic_cli.mcp.docker import get_server_logs
    
    servers = get_merged_servers()
    if name not in servers:
        console.print(f"[red]Error:[/red] Server '{name}' not found")
        raise typer.Exit(1)
    
    server = servers[name]
    if server.type != MCPServerType.DOCKER:
        console.print(f"[yellow]Warning:[/yellow] Server '{name}' is not a Docker server")
        raise typer.Exit(1)
    
    success, output = get_server_logs(server, lines, follow)
    if success:
        if output:
            console.print(output)
    else:
        console.print(f"[red]Error:[/red] {output}")
        raise typer.Exit(1)
