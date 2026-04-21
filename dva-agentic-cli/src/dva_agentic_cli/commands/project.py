"""Project management commands for creating and managing agentic projects."""

import json
import shutil
import typer
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from typing_extensions import Annotated

from dva_agentic_cli.commands.init import get_google_config
from dva_agentic_cli.tracker import (
    record_activity,
    register_project,
    update_project,
    get_projects,
    get_project,
    remove_project,
    validate_project,
    get_domain,
    get_domain_repos,
    get_domain_docs,
)
from dva_agentic_cli.skill_generator import (
    gather_domain_context,
    generate_skill_files,
)
from dva_agentic_cli.templates import (
    Framework,
    UseCase,
    Tool,
    TemplateConfig,
    TemplateGenerator,
    USE_CASE_TOOLS,
)
from dva_agentic_cli.registry.manager import RegistryManager

console = Console()
project_app = typer.Typer(help="Manage agentic projects", rich_markup_mode=None)

# Create subcommand for agent operations
agent_app = typer.Typer(help="Manage agents in a project", rich_markup_mode=None)
project_app.add_typer(agent_app, name="agent")


def _wire_domain_context(
    domain_name: str,
    domain_data: dict,
    target_dir: Path,
    env_file: Optional[Path] = None,
) -> bool:
    """Auto-wire domain context into a generated project.

    1. Generate persona skill files into <project>/.skills/domain/
    2. Write .domain-context.json with full domain metadata
    3. Append domain-specific env vars to .env
    """
    console.print(f"\n[cyan]Wiring domain context for [bold]{domain_name}[/bold]...[/cyan]")

    repos = get_domain_repos(domain_name)
    docs = get_domain_docs(domain_name)
    ctx = gather_domain_context(domain_data, repos, docs)

    # 1. Generate persona skills into .skills/domain/
    skills_dir = target_dir / ".skills" / "domain"
    written = generate_skill_files(ctx, skills_dir)
    for role, fpath in written.items():
        console.print(f"  [green]✓[/green] {fpath.name}")

    # 2. Write .domain-context.json (machine-readable for agents)
    context_file = target_dir / ".domain-context.json"
    context_payload = {
        "domain": domain_name,
        "product": ctx["product"],
        "description": ctx.get("description", ""),
        "jira_project": ctx.get("jira_project", ""),
        "jira_dashboard": ctx.get("jira_dashboard", ""),
        "bitbucket_project": ctx.get("bitbucket_project", ""),
        "confluence_space": ctx.get("confluence_space", ""),
        "confluence_url": ctx.get("confluence_url", ""),
        "repos": [
            {"slug": r.get("repo_slug", ""), "clone_url": r.get("clone_url", "")}
            for r in repos
        ],
        "docs": [
            {"title": d.get("title", ""), "source_space_key": d.get("source_space_key", "")}
            for d in docs
        ],
    }
    context_file.write_text(json.dumps(context_payload, indent=2))
    console.print(f"  [green]✓[/green] .domain-context.json")

    # 3. Append domain env vars to .env
    if env_file and env_file.exists():
        env_lines = ["\n# --- Domain context (auto-wired) ---"]
        env_lines.append(f"DOMAIN_NAME={domain_name}")
        if ctx.get("jira_project"):
            env_lines.append(f"JIRA_PROJECT={ctx['jira_project']}")
        if ctx.get("jira_dashboard"):
            env_lines.append(f"JIRA_DASHBOARD_URL={ctx['jira_dashboard']}")
        if ctx.get("bitbucket_project"):
            env_lines.append(f"BITBUCKET_PROJECT={ctx['bitbucket_project']}")
        if ctx.get("confluence_space"):
            env_lines.append(f"CONFLUENCE_SPACE={ctx['confluence_space']}")
        if ctx.get("confluence_url"):
            env_lines.append(f"CONFLUENCE_URL={ctx['confluence_url']}")
        env_lines.append("MCP_BITBUCKET_URL=http://localhost:8126/sse")
        env_lines.append("MCP_JIRA_URL=http://localhost:8128/sse")
        env_lines.append("MCP_CONFLUENCE_URL=http://localhost:8129/sse")
        env_lines.append("MCP_GATEWAY_URL=http://localhost:9090/sse")

        with open(env_file, "a") as f:
            f.write("\n".join(env_lines) + "\n")
        console.print(f"  [green]✓[/green] Domain env vars appended to .env")

    console.print(f"[green]✓[/green] Domain [bold]{domain_name}[/bold] wired into project")
    return True


@project_app.command("create")
def create_project(
    name: Annotated[str, typer.Argument(help="Project name")],
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Directory where project will be created (default: current directory)",
        ),
    ] = Path("."),
    framework: Annotated[
        str,
        typer.Option(
            "--framework", "-f",
            help="Agent framework (adk, langgraph)",
        ),
    ] = "adk",
    use_case: Annotated[
        str,
        typer.Option(
            "--use-case", "-u",
            help="Use case (basic, rag, knowledge-graph, multi-agent, chatbot, data-pipeline, code-assistant, pr-reviewer)",
        ),
    ] = "basic",
    extra_tools: Annotated[
        Optional[str],
        typer.Option(
            "--tools", "-t",
            help="Additional tools (comma-separated, e.g., 'web_search,api_caller')",
        ),
    ] = None,
    include_tests: Annotated[
        bool,
        typer.Option("--tests/--no-tests", help="Include test suite"),
    ] = True,
    include_examples: Annotated[
        bool,
        typer.Option("--examples/--no-examples", help="Include examples"),
    ] = True,
    include_docker: Annotated[
        bool,
        typer.Option("--docker/--no-docker", help="Include Docker files"),
    ] = False,
    include_a2a: Annotated[
        bool,
        typer.Option("--a2a/--no-a2a", help="Include A2A protocol support (multi-agent only)"),
    ] = False,
    include_kg_mcp: Annotated[
        bool,
        typer.Option("--kg-mcp/--no-kg-mcp", help="Include KG MCP server (knowledge-graph only)"),
    ] = False,
    kg_workspace: Annotated[
        Optional[str],
        typer.Option("--kg-workspace", help="Connect to existing dva kg workspace"),
    ] = None,
    include_jira_mcp: Annotated[
        bool,
        typer.Option("--jira-mcp/--no-jira-mcp", help="Include Jira MCP add-on (pr-reviewer only)"),
    ] = False,
    bitbucket_mcp_url: Annotated[
        str,
        typer.Option("--bitbucket-mcp-url", help="Bitbucket MCP SSE endpoint URL"),
    ] = "http://localhost:8126/sse",
    jira_mcp_url: Annotated[
        str,
        typer.Option("--jira-mcp-url", help="Jira MCP SSE endpoint URL"),
    ] = "http://localhost:8128/sse",
    poll_interval: Annotated[
        int,
        typer.Option("--poll-interval", help="PR polling interval in seconds (pr-reviewer only)"),
    ] = 60,
    domain: Annotated[
        Optional[str],
        typer.Option(
            "--domain", "-d",
            help="Domain slug to auto-wire (e.g. cwow-facility). Copies persona skills, sets MCP URLs, Jira/BB config.",
        ),
    ] = None,
    agent_template: Annotated[
        Optional[str],
        typer.Option(
            "--agent-template",
            help="Use external agent template from registry",
        ),
    ] = None,
    agent_tools: Annotated[
        Optional[str],
        typer.Option(
            "--agent-tools",
            help="Comma-separated list of agent tools to install from registry",
        ),
    ] = None,
    working_location: Annotated[
        Optional[str],
        typer.Option(
            "--working-location",
            help="Working directory for project (e.g., /workspace, /tmp/project-work)",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite if project already exists"),
    ] = False,
) -> None:
    """
    Create a new agentic project from embedded templates.
    
    Examples:
        dva project create my-agent
        dva project create my-rag --use-case rag
        dva project create my-kg --use-case knowledge-graph --kg-mcp
        dva project create my-kg --use-case knowledge-graph --kg-workspace my-workspace
        dva project create my-bot --use-case chatbot --tools web_search,memory
        dva project create my-pr-bot --use-case pr-reviewer
        dva project create my-pr-bot --use-case pr-reviewer --jira-mcp --docker
        dva project create my-pr-bot --use-case pr-reviewer --domain cwow-facility
    """
    # Validate domain if provided
    domain_data = None
    if domain:
        domain_data = get_domain(domain)
        if not domain_data:
            console.print(f"[red]✗ Error:[/red] Domain '{domain}' not found.")
            console.print("[dim]Use 'dva domain list' to see available domains.[/dim]")
            raise typer.Exit(1)

    # Validate framework
    try:
        fw = Framework(framework)
    except ValueError:
        console.print(f"[red]✗ Error:[/red] Invalid framework '{framework}'")
        console.print(f"[dim]Available: {', '.join(Framework.choices())}[/dim]")
        raise typer.Exit(1)
    
    # Validate use case
    try:
        uc = UseCase(use_case)
    except ValueError:
        console.print(f"[red]✗ Error:[/red] Invalid use case '{use_case}'")
        console.print(f"[dim]Available: {', '.join(UseCase.choices())}[/dim]")
        raise typer.Exit(1)
    
    # Parse extra tools
    tools: List[Tool] = []
    if extra_tools:
        for tool_name in extra_tools.split(","):
            tool_name = tool_name.strip()
            try:
                tools.append(Tool(tool_name))
            except ValueError:
                console.print(f"[yellow]⚠ Warning:[/yellow] Unknown tool '{tool_name}', skipping")
    
    # Validate A2A flag - only valid for multi-agent use case
    if include_a2a and uc != UseCase.MULTI_AGENT:
        console.print(f"[yellow]⚠ Warning:[/yellow] --a2a flag is only applicable for multi-agent use case, ignoring")
        include_a2a = False
    
    # Validate KG flags - only valid for knowledge-graph use case
    if include_kg_mcp and uc != UseCase.KNOWLEDGE_GRAPH:
        console.print(f"[yellow]⚠ Warning:[/yellow] --kg-mcp flag is only applicable for knowledge-graph use case, ignoring")
        include_kg_mcp = False
    
    if kg_workspace and uc != UseCase.KNOWLEDGE_GRAPH:
        console.print(f"[yellow]⚠ Warning:[/yellow] --kg-workspace is only applicable for knowledge-graph use case, ignoring")
        kg_workspace = None
    
    # Validate PR reviewer flags
    if include_jira_mcp and uc != UseCase.PR_REVIEWER:
        console.print(f"[yellow]⚠ Warning:[/yellow] --jira-mcp flag is only applicable for pr-reviewer use case, ignoring")
        include_jira_mcp = False
    
    # Auto-enable docker for pr-reviewer
    if uc == UseCase.PR_REVIEWER and not include_docker:
        include_docker = True
    
    # Handle external agent template
    if agent_template:
        manager = RegistryManager()
        template_registry = manager.get_default_registry("agent-templates")
        if not template_registry:
            console.print("[red]Agent template registry unavailable[/red]")
            raise typer.Exit(1)
        
        # Ensure registry is available
        if not template_registry.ensure_available():
            console.print("[red]Agent template registry unavailable[/red]")
            raise typer.Exit(1)
        
        # Get template metadata
        template_meta = template_registry.get_item(agent_template)
        if not template_meta:
            console.print(f"[red]Agent template '{agent_template}' not found[/red]")
            raise typer.Exit(1)
        
        # Override framework and use case from template
        try:
            fw = Framework(template_meta.framework)
            uc = UseCase(template_meta.use_case)
        except ValueError as e:
            console.print(f"[red]Invalid template configuration: {e}[/red]")
            raise typer.Exit(1)
        
        console.print(f"[green]Using external template: {agent_template} ({template_meta.framework}/{template_meta.use_case})[/green]")
    
    # Get Google config
    google_config = get_google_config() or {}
    
    # Create template config
    config = TemplateConfig(
        name=name,
        framework=fw,
        use_case=uc,
        tools=tools,  # Will auto-populate from use case if empty
        include_tests=include_tests,
        include_examples=include_examples,
        include_docker=include_docker,
        include_a2a=include_a2a,
        include_kg_mcp=include_kg_mcp,
        include_jira_mcp=include_jira_mcp,
        kg_workspace=kg_workspace,
        domain_name=domain,
        google_project_id=google_config.get("project_id"),
        google_location=google_config.get("location", "us-central1"),
        bitbucket_mcp_url=bitbucket_mcp_url,
        jira_mcp_url=jira_mcp_url,
        poll_interval=poll_interval,
    )
    
    # Display configuration
    tools_display = ", ".join(t.display_name for t in config.tools[:5])
    if len(config.tools) > 5:
        tools_display += f" (+{len(config.tools) - 5} more)"
    
    # Build extras display
    extras = []
    if include_a2a:
        extras.append("[bold]A2A Protocol:[/bold] ✓ Enabled")
    if include_kg_mcp:
        extras.append("[bold]KG MCP Server:[/bold] ✓ Enabled")
    if kg_workspace:
        extras.append(f"[bold]KG Workspace:[/bold] {kg_workspace}")
    if uc == UseCase.PR_REVIEWER:
        extras.append(f"[bold]Bitbucket MCP:[/bold] {bitbucket_mcp_url}")
        if include_jira_mcp:
            extras.append(f"[bold]Jira MCP:[/bold] {jira_mcp_url}")
        extras.append(f"[bold]Poll Interval:[/bold] {poll_interval}s")
    extras_display = "\n" + "\n".join(extras) if extras else ""
    
    console.print(
        Panel.fit(
            f"[bold cyan]Creating Agentic Project[/bold cyan]\n\n"
            f"[bold]Name:[/bold] {name}\n"
            f"[bold]Framework:[/bold] {fw.display_name}\n"
            f"[bold]Use Case:[/bold] {uc.display_name}\n"
            f"[bold]Tools:[/bold] {tools_display}{extras_display}",
            border_style="cyan",
        )
    )
    
    # Determine target directory
    target_dir = (path / name).resolve()
    
    # Check if target already exists
    if target_dir.exists():
        if not force:
            console.print(f"[yellow]⚠ Warning:[/yellow] Directory {target_dir} already exists.")
            if not Confirm.ask("Do you want to overwrite it?"):
                console.print("[dim]Operation cancelled.[/dim]")
                raise typer.Exit(0)
        console.print("[dim]Removing existing directory...[/dim]")
        shutil.rmtree(target_dir)
    
    # Generate project
    console.print(f"[cyan]Generating project at {target_dir}...[/cyan]")
    try:
        if agent_template:
            # Use external template
            manager = RegistryManager()
            template_registry = manager.ensure_registry_available("agent-templates")
            if not template_registry:
                console.print("[red]Agent template registry unavailable[/red]")
                raise typer.Exit(1)
            
            # Install external template
            success = template_registry.install_item(agent_template, target_dir)
            if not success:
                console.print(f"[red]Failed to install template '{agent_template}'[/red]")
                raise typer.Exit(1)
        else:
            # Use embedded template
            generator = TemplateGenerator(config)
            generator.generate(target_dir)
    except Exception as e:
        console.print(f"[red]Error generating project:[/red] {e}")
        raise typer.Exit(1)
    
    # Create .env from .env.example and populate with saved config
    env_example = target_dir / ".env.example"
    env_file = target_dir / ".env"
    if env_example.exists() and not env_file.exists():
        console.print("[dim]Creating .env file...[/dim]")
        shutil.copy(env_example, env_file)
        
        if google_config:
            console.print("[dim]Adding Google Cloud configuration to .env...[/dim]")
            env_content = env_file.read_text()
            
            if google_config.get("project_id"):
                env_content = env_content.replace(
                    "GOOGLE_PROJECT_ID=your-project-id",
                    f"GOOGLE_PROJECT_ID={google_config['project_id']}"
                )
            if google_config.get("location"):
                env_content = env_content.replace(
                    "GOOGLE_LOCATION=us-central1",
                    f"GOOGLE_LOCATION={google_config['location']}"
                )
            if google_config.get("credentials_path"):
                env_content = env_content.replace(
                    "GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json",
                    f"GOOGLE_APPLICATION_CREDENTIALS={google_config['credentials_path']}"
                )
            if google_config.get("model"):
                env_content = env_content.replace(
                    "VERTEX_AI_MODEL=gemini-2.0-flash-001",
                    f"VERTEX_AI_MODEL={google_config['model']}"
                )
            
            env_file.write_text(env_content)
            console.print("[green]Google Cloud configuration added to .env[/green]")
    
    # Install agent tools if specified
    if agent_tools:
        manager = RegistryManager()
        tool_registry = manager.ensure_registry_available("agent-tools")
        if not tool_registry:
            console.print("[red]Agent tool registry unavailable[/red]")
            raise typer.Exit(1)
        
        tools_dir = target_dir / "src" / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"[cyan]Installing agent tools...[/cyan]")
        for tool_name in agent_tools.split(","):
            tool_name = tool_name.strip()
            if tool_name:
                success = tool_registry.install_item(tool_name, tools_dir)
                if success:
                    console.print(f"[green]  Installed tool: {tool_name}[/green]")
                else:
                    console.print(f"[red]  Failed to install tool: {tool_name}[/red]")
    
    # Auto-wire domain context if --domain was provided
    domain_wired = False
    if domain and domain_data:
        domain_wired = _wire_domain_context(domain, domain_data, target_dir, env_file if env_file.exists() else None)

    # Track project creation
    register_project(
        name=name,
        path=str(target_dir),
        framework=framework,
        use_case=use_case,
        tools=[t.value for t in config.tools],
        working_location=working_location,
    )
    record_activity(
        command="project",
        subcommand="create",
        args={"name": name, "framework": framework, "use_case": use_case, "domain": domain},
        details={"path": str(target_dir), "tools": [t.value for t in config.tools]},
        repo_path=str(target_dir),
    )

    # Success message
    domain_msg = ""
    if domain_wired:
        domain_msg = f"\n[bold]Domain:[/bold] {domain} (auto-wired)\n"
    console.print(
        Panel.fit(
            f"[bold green]✓ Project created successfully![/bold green]\n\n"
            f"Location: {target_dir}{domain_msg}\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. cd {name}\n"
            f"  2. Edit .env file with your API keys\n"
            f"  3. uv venv && source .venv/bin/activate\n"
            f"  4. uv pip install -e '.[dev]'\n"
            f"  5. python src/main.py\n\n"
            f"[dim]Or use: make install-dev && make run[/dim]",
            title="Success",
            border_style="green",
        )
    )


@project_app.command("list")
def list_projects() -> None:
    """List all registered agent projects."""
    projects = get_projects()
    if not projects:
        console.print("[yellow]No projects registered yet.[/yellow]")
        console.print("[dim]Create one with: dva project create <name>[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Use Case")
    table.add_column("Framework")
    table.add_column("Path", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Created")

    for p in projects:
        v = validate_project(p["path"], p.get("use_case"))
        score_str = f"{v['score']}/{v['total']}"
        pct = (v["score"] / v["total"] * 100) if v["total"] else 0
        score_color = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"
        created = p.get("created_at", "—")
        if created and len(created) > 10:
            created = created[:10]
        table.add_row(
            p["name"],
            p.get("use_case") or "—",
            p.get("framework") or "—",
            p.get("path", "—"),
            f"[{score_color}]{score_str}[/{score_color}]",
            created,
        )

    console.print(Panel.fit(f"[bold]{len(projects)}[/bold] registered project(s)", border_style="cyan"))
    console.print(table)

    record_activity("project", "list")


@project_app.command("show")
def show_project(
    name: Annotated[str, typer.Argument(help="Project name")],
) -> None:
    """Show details for a registered project."""
    p = get_project(name)
    if not p:
        console.print(f"[red]✗ Project '{name}' not found.[/red]")
        console.print("[dim]Run 'dva project list' to see registered projects.[/dim]")
        raise typer.Exit(1)

    tools = p.get("tools") or []
    if isinstance(tools, str):
        tools = json.loads(tools)
    tools_str = ", ".join(tools) if tools else "—"
    
    # Get domain from tracker config first, then fall back to .domain-context.json
    domain_name = p.get("domain_name") or "—"
    if domain_name == "—":
        domain_ctx = Path(p["path"]) / ".domain-context.json"
        if domain_ctx.exists():
            try:
                domain_name = json.loads(domain_ctx.read_text()).get("domain", "—")
            except (json.JSONDecodeError, OSError):
                pass

    working_loc = p.get("working_location") or "—"
    gcp_proj = p.get("google_project_id") or "—"
    gcp_loc = p.get("google_location") or "—"
    vertex_model = p.get("vertex_ai_model") or "—"

    console.print(Panel.fit(
        f"[bold]Name:[/bold] {p['name']}\n"
        f"[bold]Path:[/bold] {p['path']}\n"
        f"[bold]Framework:[/bold] {p.get('framework') or '—'}\n"
        f"[bold]Use Case:[/bold] {p.get('use_case') or '—'}\n"
        f"[bold]Tools:[/bold] {tools_str}\n"
        f"[bold]Domain:[/bold] {domain_name}\n"
        f"[bold]Working Location:[/bold] {working_loc}\n"
        f"[bold]GCP Project:[/bold] {gcp_proj}\n"
        f"[bold]GCP Location:[/bold] {gcp_loc}\n"
        f"[bold]Vertex AI Model:[/bold] {vertex_model}\n"
        f"[bold]Created:[/bold] {p.get('created_at') or '—'}",
        title=f"Project: {p['name']}",
        border_style="cyan",
    ))

    # Validation
    v = validate_project(p["path"], p.get("use_case"))
    console.print(f"\n[bold]Validation:[/bold] {v['score']}/{v['total']} checks passed")
    for key, val in v.items():
        if key in ("score", "total"):
            continue
        icon = "[green]✓[/green]" if val else "[red]✗[/red]"
        label = key.replace("has_", "").replace("_", " ")
        console.print(f"  {icon} {label}")

    record_activity("project", "show", args={"name": name})


@project_app.command("configure")
def configure_project(
    name: Annotated[str, typer.Argument(help="Project name")],
    working_location: Annotated[
        Optional[str],
        typer.Option("--working-location", help="Working directory for project (e.g., /workspace)"),
    ] = None,
    gcp_project: Annotated[
        Optional[str],
        typer.Option("--gcp-project", help="GCP project ID"),
    ] = None,
    gcp_location: Annotated[
        Optional[str],
        typer.Option("--gcp-location", help="GCP location (e.g., us-central1)"),
    ] = None,
    vertex_ai_model: Annotated[
        Optional[str],
        typer.Option("--vertex-ai-model", help="Vertex AI model name (e.g., gemini-2.0-flash-001)"),
    ] = None,
    gcp_credentials: Annotated[
        Optional[str],
        typer.Option("--gcp-credentials", help="Path to GCP service account key file"),
    ] = None,
    domain: Annotated[
        Optional[str],
        typer.Option("--domain", "-d", help="Domain slug (e.g., cwow-facility)"),
    ] = None,
    show: Annotated[
        bool,
        typer.Option("--show", help="Show current configuration and exit"),
    ] = False,
) -> None:
    """
    Configure project settings (GCP, domain, etc).

    Settings are stored in the tracker database and auto-populated in agent .env files.

    Examples:
        dva project configure my-project --gcp-project my-gcp-proj --gcp-location us-central1
        dva project configure my-project --vertex-ai-model gemini-2.0-flash-001
        dva project configure my-project --domain cwow-facility
        dva project configure my-project --show
    """
    p = get_project(name)
    if not p:
        console.print(f"[red]✗ Project '{name}' not found.[/red]")
        console.print("[dim]Run 'dva project list' to see registered projects.[/dim]")
        raise typer.Exit(1)

    if show:
        _show_project_config(p)
        return

    if not any([working_location, gcp_project, gcp_location, vertex_ai_model, gcp_credentials, domain]):
        console.print("[yellow]⚠ No configuration options provided.[/yellow]")
        console.print("[dim]Use --show to view current config, or provide options to update.[/dim]")
        raise typer.Exit(1)

    # Update project config
    success = update_project(
        name,
        working_location=working_location,
        google_project_id=gcp_project,
        google_location=gcp_location,
        vertex_ai_model=vertex_ai_model,
        google_credentials_path=gcp_credentials,
        domain_name=domain,
    )

    if not success:
        console.print(f"[red]✗ Failed to update project '{name}'.[/red]")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold green]✓ Project configured![/bold green]\n\n"
        f"[bold]Project:[/bold] {name}",
        border_style="green",
    ))

    # Show updated config
    p_updated = get_project(name)
    _show_project_config(p_updated)

    record_activity(
        "project",
        "configure",
        args={"name": name, "gcp_project": gcp_project, "domain": domain},
        details={
            "gcp_project_id": gcp_project,
            "gcp_location": gcp_location,
            "vertex_ai_model": vertex_ai_model,
            "domain_name": domain,
        },
    )


def _show_project_config(project: dict) -> None:
    """Display project configuration."""
    working_loc = project.get("working_location") or "—"
    gcp_proj = project.get("google_project_id") or "—"
    gcp_loc = project.get("google_location") or "—"
    vertex_model = project.get("vertex_ai_model") or "—"
    gcp_creds = project.get("google_credentials_path") or "—"
    domain = project.get("domain_name") or "—"

    console.print("\n[bold cyan]Project Configuration[/bold cyan]")
    console.print(Panel.fit(
        f"[bold]Working Location:[/bold] {working_loc}\n"
        f"[bold]GCP Project ID:[/bold] {gcp_proj}\n"
        f"[bold]GCP Location:[/bold] {gcp_loc}\n"
        f"[bold]Vertex AI Model:[/bold] {vertex_model}\n"
        f"[bold]GCP Credentials:[/bold] {gcp_creds}\n"
        f"[bold]Domain:[/bold] {domain}",
        border_style="cyan",
    ))


@project_app.command("validate")
def validate_project_cmd(
    name: Annotated[str, typer.Argument(help="Project name")],
) -> None:
    """Run validation checks on a registered project."""
    p = get_project(name)
    if not p:
        console.print(f"[red]✗ Project '{name}' not found.[/red]")
        raise typer.Exit(1)

    v = validate_project(p["path"], p.get("use_case"))
    pct = (v["score"] / v["total"] * 100) if v["total"] else 0
    color = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check")
    table.add_column("Status", justify="center")

    for key, val in v.items():
        if key in ("score", "total"):
            continue
        icon = "[green]✓ pass[/green]" if val else "[red]✗ fail[/red]"
        label = key.replace("has_", "").replace("_", " ").title()
        table.add_row(label, icon)

    console.print(Panel.fit(
        f"[bold]Project:[/bold] {p['name']}\n"
        f"[bold]Path:[/bold] {p['path']}\n"
        f"[bold]Score:[/bold] [{color}]{v['score']}/{v['total']} ({pct:.0f}%)[/{color}]",
        title="Validation Results",
        border_style=color,
    ))
    console.print(table)

    record_activity("project", "validate", args={"name": name, "score": v["score"], "total": v["total"]})


@project_app.command("remove")
def remove_project_cmd(
    name: Annotated[str, typer.Argument(help="Project name to remove from registry")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Remove a project from the registry (does NOT delete files)."""
    p = get_project(name)
    if not p:
        console.print(f"[red]✗ Project '{name}' not found.[/red]")
        raise typer.Exit(1)

    if not yes:
        if not Confirm.ask(f"Remove project '{name}' from registry? (files are NOT deleted)"):
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    remove_project(name)
    console.print(f"[green]✓[/green] Project '{name}' removed from registry.")
    record_activity("project", "remove", args={"name": name})


@project_app.command("list-templates")
def list_templates() -> None:
    """List available frameworks, use cases, and tools."""
    # Frameworks
    console.print(Panel.fit("[bold cyan]Available Frameworks[/bold cyan]", border_style="cyan"))
    
    fw_table = Table(show_header=True, header_style="bold magenta")
    fw_table.add_column("Framework", style="cyan")
    fw_table.add_column("Description")
    fw_table.add_column("Status", style="green")
    
    for fw in Framework:
        status = "[green]✓ Available[/green]"
        fw_table.add_row(fw.value, fw.display_name, status)
    
    console.print(fw_table)
    
    # Use Cases
    console.print("\n")
    console.print(Panel.fit("[bold cyan]Available Use Cases[/bold cyan]", border_style="cyan"))
    
    uc_table = Table(show_header=True, header_style="bold magenta")
    uc_table.add_column("Use Case", style="cyan")
    uc_table.add_column("Description")
    uc_table.add_column("Default Tools")
    
    for uc in UseCase:
        tools = USE_CASE_TOOLS.get(uc, [])
        tools_str = ", ".join(t.value for t in tools[:3])
        if len(tools) > 3:
            tools_str += f" (+{len(tools) - 3})"
        uc_table.add_row(uc.value, uc.description, tools_str)
    
    console.print(uc_table)
    
    # Tools
    console.print("\n")
    console.print(Panel.fit("[bold cyan]Available Tools[/bold cyan]", border_style="cyan"))
    
    tool_table = Table(show_header=True, header_style="bold magenta")
    tool_table.add_column("Tool", style="cyan")
    tool_table.add_column("Description")
    
    for tool in Tool:
        tool_table.add_row(tool.value, tool.display_name)
    
    console.print(tool_table)
    
    console.print("\n[dim]Usage: dva project create <name> --framework <fw> --use-case <uc> --tools <tool1,tool2>[/dim]")


@project_app.command("info")
def project_info(
    path: Annotated[
        Path,
        typer.Argument(help="Path to project directory"),
    ] = Path("."),
) -> None:
    """Show information about an agentic project."""
    path = path.resolve()
    
    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)
    
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        console.print(f"[red]✗ Error:[/red] Not a valid project (no pyproject.toml found).")
        raise typer.Exit(1)
    
    # Read project info
    content = pyproject_path.read_text()
    
    # Extract basic info (simple parsing)
    name = "Unknown"
    version = "Unknown"
    description = "No description"
    
    for line in content.split("\n"):
        if line.startswith("name ="):
            name = line.split("=")[1].strip().strip('"')
        elif line.startswith("version ="):
            version = line.split("=")[1].strip().strip('"')
        elif line.startswith("description ="):
            description = line.split("=")[1].strip().strip('"')
    
    # Check for key directories
    has_agents = (path / "src" / "agents").exists()
    has_tools = (path / "src" / "tools").exists()
    has_workflows = (path / "src" / "workflows").exists()
    has_tests = (path / "tests").exists()
    has_venv = (path / ".venv").exists()
    
    console.print(
        Panel.fit(
            f"[bold cyan]Project Information[/bold cyan]\n\n"
            f"[bold]Name:[/bold] {name}\n"
            f"[bold]Version:[/bold] {version}\n"
            f"[bold]Description:[/bold] {description}\n"
            f"[bold]Location:[/bold] {path}\n\n"
            f"[bold]Structure:[/bold]\n"
            f"  {'✓' if has_agents else '✗'} Agents\n"
            f"  {'✓' if has_tools else '✗'} Tools\n"
            f"  {'✓' if has_workflows else '✗'} Workflows\n"
            f"  {'✓' if has_tests else '✗'} Tests\n"
            f"  {'✓' if has_venv else '✗'} Virtual Environment",
            border_style="cyan",
        )
    )


# Import extension commands
from dva_agentic_cli.commands.project_extensions import (
    run_project_command,
    list_agents_command,
    agent_info_command,
)


@project_app.command("run")
def run(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Path to project directory (default: current directory)",
        ),
    ] = Path("."),
    agent: Annotated[
        str,
        typer.Option(
            "--agent",
            help="Specific agent to run (default: run main.py)",
        ),
    ] = "",
    script: Annotated[
        str,
        typer.Option(
            "--script",
            help="Custom script to run (e.g., examples/kg_agent_demo.py)",
        ),
    ] = "",
) -> None:
    """
    Run agents in a project.
    
    Examples:
        dva project run                          # Run main.py
        dva project run --agent KnowledgeGraphAgent  # Run specific agent
        dva project run --script examples/kg_agent_demo.py  # Run custom script
    """
    run_project_command(path, agent or None, script or None)


@agent_app.command("list")
def agent_list(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Path to project directory (default: current directory)",
        ),
    ] = Path("."),
) -> None:
    """List all agents in a project."""
    list_agents_command(path)


@agent_app.command("info")
def agent_info(
    agent_name: Annotated[str, typer.Argument(help="Agent name")],
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Path to project directory (default: current directory)",
        ),
    ] = Path("."),
) -> None:
    """Show detailed information about a specific agent."""
    agent_info_command(agent_name, path)
