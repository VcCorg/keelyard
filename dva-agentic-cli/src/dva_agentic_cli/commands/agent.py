"""Agent management commands for running, scheduling, and managing agents."""

import json
import os
import signal
import subprocess
import sys
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from dva_agentic_cli.commands.project_extensions import discover_agents
from dva_agentic_cli.tracker import record_activity

console = Console()
agent_app = typer.Typer(help="Run and manage agents", rich_markup_mode=None)

# State file for tracking scheduled/running agents
AGENT_STATE_DIR = Path.home() / ".dva" / "agents"


def _get_state_file() -> Path:
    """Get the agent state file path."""
    AGENT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return AGENT_STATE_DIR / "running.json"


def _load_state() -> dict:
    """Load running agent state."""
    state_file = _get_state_file()
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            return {"agents": {}}
    return {"agents": {}}


def _save_state(state: dict) -> None:
    """Save running agent state."""
    _get_state_file().write_text(json.dumps(state, indent=2))


@agent_app.command("run")
def run_agent(
    path: Annotated[
        Path,
        typer.Option(
            "--path", "-p",
            help="Path to the agent project directory",
        ),
    ] = Path("."),
    mode: Annotated[
        str,
        typer.Option(
            "--mode", "-m",
            help="Run mode: interactive, daemon, once",
        ),
    ] = "interactive",
    review_mode: Annotated[
        Optional[str],
        typer.Option(
            "--review-mode",
            help="Override review mode (pr-reviewer only): notify, review, auto-approve",
        ),
    ] = None,
    poll_interval: Annotated[
        Optional[int],
        typer.Option(
            "--poll-interval",
            help="Override poll interval in seconds (pr-reviewer only)",
        ),
    ] = None,
) -> None:
    """
    Run an agent project.

    Examples:
        dva agent run --path ./my-pr-bot
        dva agent run --path ./my-pr-bot --mode daemon
        dva agent run --path ./my-pr-bot --mode once
        dva agent run --path ./my-pr-bot --mode daemon --review-mode auto-approve
    """
    path = path.resolve()

    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)

    main_py = path / "src" / "main.py"
    if not main_py.exists():
        console.print(f"[red]✗ Error:[/red] No src/main.py found in {path}")
        raise typer.Exit(1)

    # Determine Python executable
    venv_path = path / ".venv"
    if venv_path.exists():
        python_exe = venv_path / "bin" / "python"
        if not python_exe.exists():
            python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = Path(sys.executable)

    if not python_exe.exists():
        console.print(f"[red]✗ Error:[/red] Python executable not found at {python_exe}")
        raise typer.Exit(1)

    # Build command
    cmd = [str(python_exe), str(main_py), "--mode", mode]
    if review_mode:
        cmd.extend(["--review-mode", review_mode])
    if poll_interval:
        cmd.extend(["--poll-interval", str(poll_interval)])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(path)

    console.print(Panel.fit(
        f"[bold cyan]Running Agent[/bold cyan]\n\n"
        f"[bold]Project:[/bold] {path.name}\n"
        f"[bold]Mode:[/bold] {mode}\n"
        f"[bold]Python:[/bold] {python_exe}",
        border_style="cyan",
    ))

    record_activity(
        command="agent", subcommand="run",
        args={"path": str(path), "mode": mode},
        repo_path=str(path),
    )

    try:
        result = subprocess.run(
            cmd, cwd=path, env=env, check=False,
        )
        if result.returncode not in (0, 130):
            console.print(f"\n[red]✗ Process exited with code {result.returncode}[/red]")
            raise typer.Exit(result.returncode)
        else:
            console.print("\n[green]✓ Agent finished.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user[/yellow]")


@agent_app.command("start")
def start_agent(
    path: Annotated[
        Path,
        typer.Option(
            "--path", "-p",
            help="Path to the agent project directory",
        ),
    ] = Path("."),
    review_mode: Annotated[
        Optional[str],
        typer.Option(
            "--review-mode",
            help="Override review mode: notify, review, auto-approve",
        ),
    ] = None,
    poll_interval: Annotated[
        Optional[int],
        typer.Option(
            "--poll-interval",
            help="Override poll interval in seconds",
        ),
    ] = None,
    name: Annotated[
        Optional[str],
        typer.Option(
            "--name", "-n",
            help="Name for this agent instance (default: project directory name)",
        ),
    ] = None,
) -> None:
    """
    Start an agent as a background daemon process.

    Examples:
        dva agent start --path ./my-pr-bot
        dva agent start --path ./my-pr-bot --review-mode auto-approve --name prod-reviewer
    """
    path = path.resolve()
    instance_name = name or path.name

    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)

    main_py = path / "src" / "main.py"
    if not main_py.exists():
        console.print(f"[red]✗ Error:[/red] No src/main.py found in {path}")
        raise typer.Exit(1)

    # Check if already running
    state = _load_state()
    if instance_name in state["agents"]:
        pid = state["agents"][instance_name].get("pid")
        if pid and _is_process_running(pid):
            console.print(f"[yellow]⚠ Agent '{instance_name}' is already running (PID {pid})[/yellow]")
            console.print("[dim]Use 'dva agent stop' to stop it first.[/dim]")
            raise typer.Exit(1)

    # Determine Python executable
    venv_path = path / ".venv"
    if venv_path.exists():
        python_exe = venv_path / "bin" / "python"
        if not python_exe.exists():
            python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = Path(sys.executable)

    # Build command
    cmd = [str(python_exe), str(main_py), "--mode", "daemon"]
    if review_mode:
        cmd.extend(["--review-mode", review_mode])
    if poll_interval:
        cmd.extend(["--poll-interval", str(poll_interval)])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(path)

    # Create log directory
    log_dir = path / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "agent.log"

    # Start as background process
    with open(log_file, "a") as lf:
        process = subprocess.Popen(
            cmd, cwd=path, env=env,
            stdout=lf, stderr=lf,
            start_new_session=True,
        )

    # Save state
    state["agents"][instance_name] = {
        "pid": process.pid,
        "path": str(path),
        "review_mode": review_mode or "review",
        "poll_interval": poll_interval or 60,
        "log_file": str(log_file),
        "cmd": " ".join(cmd),
    }
    _save_state(state)

    record_activity(
        command="agent", subcommand="start",
        args={"name": instance_name, "path": str(path), "review_mode": review_mode},
        details={"pid": process.pid},
        repo_path=str(path),
    )

    console.print(Panel.fit(
        f"[bold green]✓ Agent Started[/bold green]\n\n"
        f"[bold]Name:[/bold] {instance_name}\n"
        f"[bold]PID:[/bold] {process.pid}\n"
        f"[bold]Log:[/bold] {log_file}\n"
        f"[bold]Project:[/bold] {path}\n\n"
        f"[dim]Use 'dva agent status' to check or 'dva agent stop --name {instance_name}' to stop[/dim]",
        border_style="green",
    ))


@agent_app.command("stop")
def stop_agent(
    name: Annotated[
        Optional[str],
        typer.Option(
            "--name", "-n",
            help="Name of the agent instance to stop",
        ),
    ] = None,
    all_agents: Annotated[
        bool,
        typer.Option("--all", help="Stop all running agents"),
    ] = False,
) -> None:
    """
    Stop a running background agent.

    Examples:
        dva agent stop --name my-pr-bot
        dva agent stop --all
    """
    state = _load_state()

    if not state["agents"]:
        console.print("[yellow]No agents are currently tracked.[/yellow]")
        return

    if all_agents:
        for agent_name, info in list(state["agents"].items()):
            _stop_one(agent_name, info)
        state["agents"] = {}
        _save_state(state)
        console.print("[green]✓ All agents stopped.[/green]")
        return

    if not name:
        # If only one agent, stop it
        if len(state["agents"]) == 1:
            name = list(state["agents"].keys())[0]
        else:
            console.print("[red]✗ Error:[/red] Specify --name or --all")
            console.print("[dim]Running agents:[/dim]")
            for n in state["agents"]:
                console.print(f"  • {n}")
            raise typer.Exit(1)

    if name not in state["agents"]:
        console.print(f"[red]✗ Error:[/red] Agent '{name}' not found.")
        raise typer.Exit(1)

    _stop_one(name, state["agents"][name])
    del state["agents"][name]
    _save_state(state)


def _stop_one(name: str, info: dict) -> None:
    """Stop a single agent process."""
    pid = info.get("pid")
    if pid and _is_process_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            record_activity(
                command="agent", subcommand="stop",
                args={"name": name, "pid": pid},
                repo_path=info.get("path"),
            )
            console.print(f"[green]✓ Stopped agent '{name}' (PID {pid})[/green]")
        except OSError as e:
            console.print(f"[yellow]⚠ Could not stop PID {pid}: {e}[/yellow]")
    else:
        console.print(f"[dim]Agent '{name}' was not running (PID {pid}).[/dim]")


@agent_app.command("status")
def agent_status() -> None:
    """Show status of all tracked agents."""
    state = _load_state()

    if not state["agents"]:
        console.print("[dim]No agents are currently tracked.[/dim]")
        console.print("[dim]Start one with: dva agent start --path ./my-agent[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("PID")
    table.add_column("Review Mode")
    table.add_column("Poll (s)")
    table.add_column("Project Path", style="dim")

    for name, info in state["agents"].items():
        pid = info.get("pid")
        running = _is_process_running(pid) if pid else False
        status = "[green]● Running[/green]" if running else "[red]● Stopped[/red]"
        table.add_row(
            name,
            status,
            str(pid or "—"),
            info.get("review_mode", "—"),
            str(info.get("poll_interval", "—")),
            info.get("path", "—"),
        )

    console.print(Panel.fit("[bold cyan]Agent Status[/bold cyan]", border_style="cyan"))
    console.print(table)


@agent_app.command("logs")
def agent_logs(
    name: Annotated[
        Optional[str],
        typer.Option(
            "--name", "-n",
            help="Name of the agent instance",
        ),
    ] = None,
    tail: Annotated[
        int,
        typer.Option("--tail", "-t", help="Number of lines to show"),
    ] = 50,
) -> None:
    """
    Show logs for a running agent.

    Examples:
        dva agent logs --name my-pr-bot
        dva agent logs --name my-pr-bot --tail 100
    """
    state = _load_state()

    if not name:
        if len(state["agents"]) == 1:
            name = list(state["agents"].keys())[0]
        else:
            console.print("[red]✗ Error:[/red] Specify --name")
            raise typer.Exit(1)

    if name not in state["agents"]:
        console.print(f"[red]✗ Error:[/red] Agent '{name}' not found.")
        raise typer.Exit(1)

    log_file = Path(state["agents"][name].get("log_file", ""))
    if not log_file.exists():
        console.print(f"[yellow]No log file found at {log_file}[/yellow]")
        return

    lines = log_file.read_text().strip().split("\n")
    shown = lines[-tail:]
    console.print(Panel.fit(f"[bold cyan]Logs: {name}[/bold cyan] (last {len(shown)} lines)", border_style="cyan"))
    for line in shown:
        console.print(line)


@agent_app.command("list")
def list_agents(
    path: Annotated[
        Path,
        typer.Option(
            "--path", "-p",
            help="Path to the agent project directory",
        ),
    ] = Path("."),
) -> None:
    """List agents available in a project."""
    path = path.resolve()
    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)

    agents = discover_agents(path)
    if not agents:
        console.print("[yellow]No agents found in this project.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan")
    table.add_column("File", style="green")
    table.add_column("Description")

    for agent in agents:
        desc = agent["description"][:70] + "..." if len(agent["description"]) > 70 else agent["description"]
        table.add_row(agent["name"], agent["file"], desc)

    console.print(table)


@agent_app.command("add")
def add_agent(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Agent name (e.g., sprint-tracker, my-rag)"),
    ] = None,
    agent_type: Annotated[
        str,
        typer.Option(
            "--type", "-t",
            help="Agent type: basic, rag, chatbot, knowledge-graph, code-assistant, data-pipeline, pr-reviewer, scrum-master, custom",
        ),
    ] = "basic",
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project", "-P",
            help="Registered project name (looks up path and domain from tracker)",
        ),
    ] = None,
    path: Annotated[
        Optional[Path],
        typer.Option(
            "--path", "-p",
            help="Path to the existing project directory (used if --project not provided)",
        ),
    ] = None,
    domain: Annotated[
        Optional[str],
        typer.Option("--domain", "-d", help="Domain slug (overrides tracker domain if set)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing agent file"),
    ] = False,
    list_types: Annotated[
        bool,
        typer.Option("--list-types", help="List available agent types and exit"),
    ] = False,
) -> None:
    """
    Add a new agent to an existing project.

    Generates agent class, tools, and supporting modules based on the type.
    Files that already exist are skipped unless --force is used.

    Lookup project by registered name (--project) or provide explicit path (--path).
    Domain is auto-populated from tracker if using --project.

    Examples:
        dva agent add my-rag --type rag --project cwow-facility-agents-project
        dva agent add pr-bot --type pr-reviewer --path ./my-project
        dva agent add sprint-tracker --type scrum-master --project cwow-facility-agents-project
        dva agent add helper --type custom --path ./my-project
        dva agent add --list-types
    """
    from dva_agentic_cli.templates.scaffolds import (
        AGENT_TYPES,
        get_agent_tools,
        scaffold_agent,
        to_class_name,
    )
    from dva_agentic_cli.tracker import get_project, get_domain

    if list_types:
        _show_agent_types(AGENT_TYPES, get_agent_tools)
        return

    if not name:
        console.print("[red]✗ Error:[/red] Agent name is required.")
        console.print("[dim]Usage: dva agent add <name> --type <type> [--project <name> | --path <dir>][/dim]")
        raise typer.Exit(1)

    # Resolve project path and domain
    if project:
        proj = get_project(project)
        if not proj:
            console.print(f"[red]✗ Error:[/red] Project '{project}' not found in tracker.")
            console.print("[dim]Use 'dva project list' to see registered projects.[/dim]")
            raise typer.Exit(1)
        path = Path(proj["path"])
        # Auto-populate domain from tracker if not explicitly provided
        if not domain and proj.get("domain_name"):
            domain = proj["domain_name"]
    elif path:
        path = Path(path).resolve()
    else:
        path = Path(".").resolve()

    path = path.resolve()

    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)

    if not (path / "src").exists():
        console.print(f"[red]✗ Error:[/red] No src/ directory found in {path}.")
        console.print("[dim]Expected a project created via 'dva project create'.[/dim]")
        raise typer.Exit(1)

    if agent_type not in AGENT_TYPES:
        console.print(f"[red]✗ Error:[/red] Unknown agent type '{agent_type}'.")
        console.print(f"[dim]Available: {', '.join(AGENT_TYPES.keys())}[/dim]")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold cyan]Adding Agent[/bold cyan]\n\n"
        f"[bold]Name:[/bold] {name}\n"
        f"[bold]Type:[/bold] {agent_type}\n"
        f"[bold]Class:[/bold] {to_class_name(name)}\n"
        f"[bold]Project:[/bold] {path}"
        + (f"\n[bold]Domain:[/bold] {domain}" if domain else ""),
        border_style="cyan",
    ))

    try:
        result = scaffold_agent(
            path, name, agent_type, domain=domain, force=force,
        )
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    if result["created"]:
        console.print("\n[green]✓ Created:[/green]")
        for f in result["created"]:
            console.print(f"  [green]+[/green] {f}")

    if result["skipped"]:
        console.print("\n[yellow]⚠ Skipped (already exist):[/yellow]")
        for f in result["skipped"]:
            console.print(f"  [dim]• {f}[/dim]")

    record_activity(
        command="agent",
        subcommand="add",
        args={"name": name, "type": agent_type, "project": project, "path": str(path)},
        details={"created": result["created"], "class": result["agent_class"], "domain": domain},
        repo_path=str(path),
    )

    console.print(Panel.fit(
        f"[bold green]✓ Agent added![/bold green]\n\n"
        f"[bold]Class:[/bold] {result['agent_class']}\n"
        f"[bold]File:[/bold] src/agents/{result['agent_file']}\n\n"
        f"[dim]Use in main.py:[/dim]\n"
        f"  from agents.{result['agent_file'].replace('.py', '')} import {result['agent_class']}\n\n"
        f"[dim]List agents:[/dim] dva agent list --path {path}",
        border_style="green",
    ))


def _show_agent_types(agent_types: dict, get_tools_fn) -> None:
    """Display a table of available agent types."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Type", style="cyan")
    table.add_column("Description")
    table.add_column("Tools", style="dim")

    for name, info in agent_types.items():
        tools = get_tools_fn(name)
        tool_names = ", ".join(t.value for t in tools[:4])
        if len(tools) > 4:
            tool_names += f" (+{len(tools) - 4})"
        table.add_row(name, info["description"], tool_names or "—")

    console.print(Panel.fit(
        "[bold cyan]Available Agent Types[/bold cyan]",
        border_style="cyan",
    ))
    console.print(table)
    console.print(
        "\n[dim]Usage: dva agent add <name> --type <type> --path <project>[/dim]"
    )


@agent_app.command("register")
def register_agent(
    path: Annotated[
        Path,
        typer.Option(
            "--path", "-p",
            help="Path to the agent project directory",
        ),
    ] = Path("."),
    target: Annotated[
        str,
        typer.Option(
            "--target", "-t",
            help="Registration target: opencode, windsurf",
        ),
    ] = "opencode",
    include_jira: Annotated[
        bool,
        typer.Option("--jira/--no-jira", help="Include Jira MCP tool instructions"),
    ] = False,
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Agent name (default: pr-reviewer)"),
    ] = None,
) -> None:
    """
    Register an agent with an IDE tool (OpenCode, Windsurf).

    Generates agent definition files that the IDE can discover and use.
    For OpenCode, this creates a markdown agent file in the project's agent/ directory.

    Examples:
        dva agent register --path ./my-pr-bot --target opencode
        dva agent register --path ./my-pr-bot --target opencode --jira
        dva agent register --target opencode  (uses current directory)
    """
    path = path.resolve()

    if target == "opencode":
        _register_opencode_agent(path, include_jira, name)
    elif target == "windsurf":
        console.print("[yellow]Windsurf agent registration is not yet supported.[/yellow]")
        console.print("[dim]Windsurf uses workflows (.windsurf/workflows/) — support coming soon.[/dim]")
    else:
        console.print(f"[red]✗ Error:[/red] Unknown target '{target}'. Supported: opencode, windsurf")
        raise typer.Exit(1)


def _register_opencode_agent(path: Path, include_jira: bool, name: Optional[str]) -> None:
    """Generate and register an OpenCode agent definition."""
    from dva_agentic_cli.templates.files.opencode_agent import generate_opencode_agent

    agent_file = generate_opencode_agent(path, include_jira=include_jira)

    if name:
        # Rename the file to the custom name
        new_file = agent_file.parent / f"{name}.md"
        agent_file.rename(new_file)
        agent_file = new_file

    console.print(Panel.fit(
        f"[bold green]✓ Agent Registered with OpenCode[/bold green]\n\n"
        f"[bold]File:[/bold] {agent_file}\n"
        f"[bold]Jira:[/bold] {'✓ Enabled' if include_jira else '✗ Disabled'}\n\n"
        f"[dim]Usage in OpenCode:[/dim]\n"
        f"  1. Open OpenCode in this project directory\n"
        f"  2. Type /agents to see available agents\n"
        f"  3. Select '{agent_file.stem}' to use the PR reviewer\n"
        f"  4. Or type: @{agent_file.stem} review PR #123 in PROJECT/REPO\n\n"
        f"[dim]Note: Restart OpenCode if it was already running.[/dim]",
        border_style="green",
    ))


@agent_app.command("test")
def test_agent(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path to a project to analyze (uses CWD if not provided)"),
    ] = Path("."),
    step: Annotated[
        Optional[str],
        typer.Option("--step", "-s", help="Run a specific step only: deps, config, model, analyze, detect, generate"),
    ] = None,
    agent_path: Annotated[
        Optional[Path],
        typer.Option("--agent-path", help="Path to a custom onboard agent project (tests its prompts/config)"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output for each step"),
    ] = False,
) -> None:
    """
    Test the onboard agent in isolation — step by step.

    Validates each layer independently so you can diagnose exactly
    where things break without running the full onboard pipeline.

    Steps:
      1. deps    — Check Vertex AI packages are installed
      2. config  — Check GCP project/location config
      3. model   — Test model initialization + a simple prompt
      4. analyze — Run project analyzer on the target path
      5. detect  — Run AI gap detection (full round-trip)
      6. generate — Generate SKILL.md for a detected gap

    Examples:
        dva agent test --path ./my-repo
        dva agent test --path ./my-repo --step model
        dva agent test --path ./my-repo --step detect --verbose
        dva agent test --path ./my-repo --agent-path ./my-custom-agent
    """
    path = path.resolve()
    steps_to_run = [step] if step else ["deps", "config", "model", "analyze", "detect", "generate"]

    console.print(Panel.fit(
        f"[bold cyan]Onboard Agent — Isolated Test[/bold cyan]\n\n"
        f"[bold]Project:[/bold] {path}\n"
        f"[bold]Steps:[/bold] {', '.join(steps_to_run)}"
        + (f"\n[bold]Agent:[/bold] {agent_path}" if agent_path else ""),
        border_style="cyan",
    ))
    console.print()

    results = {}
    model = None
    analysis = None
    gaps = None

    # --- Step 1: Dependencies ---
    if "deps" in steps_to_run:
        console.print("[bold]Step 1: Dependencies[/bold]")
        try:
            import vertexai  # noqa: F401
            from vertexai.generative_models import GenerativeModel  # noqa: F401
            console.print("  [green]✓[/green] google-cloud-aiplatform installed")
            if verbose:
                ver = getattr(vertexai, "__version__", "unknown")
                console.print(f"  [dim]vertexai version: {ver}[/dim]")
            results["deps"] = True
        except ImportError:
            console.print("  [red]✗[/red] google-cloud-aiplatform NOT installed")
            console.print("  [dim]Fix: pip install 'dva-agentic-cli[agent]'[/dim]")
            console.print("  [dim]  or: pip install google-cloud-aiplatform[/dim]")
            results["deps"] = False
            if not step:
                console.print("\n[red]Cannot continue without Vertex AI packages.[/red]")
                _print_test_summary(results)
                raise typer.Exit(1)

    # --- Step 2: Config ---
    if "config" in steps_to_run:
        console.print("[bold]Step 2: Vertex AI Configuration[/bold]")
        try:
            from dva_agentic_cli.kg.config import KGConfig
            config = KGConfig.load()
            pid = config.google_project_id
            loc = config.google_location

            if pid and loc:
                console.print(f"  [green]✓[/green] project_id: {pid}")
                console.print(f"  [green]✓[/green] location: {loc}")
                results["config"] = True
            else:
                console.print(f"  [red]✗[/red] project_id: {pid or 'NOT SET'}")
                console.print(f"  [red]✗[/red] location: {loc or 'NOT SET'}")
                console.print("  [dim]Fix: dva init vertex-ai --project-id <GCP_PROJECT> --location <REGION>[/dim]")
                results["config"] = False
                if not step:
                    _print_test_summary(results)
                    raise typer.Exit(1)
        except Exception as e:
            console.print(f"  [red]✗[/red] Config error: {e}")
            results["config"] = False
            if not step:
                _print_test_summary(results)
                raise typer.Exit(1)

    # --- Step 3: Model ---
    if "model" in steps_to_run:
        console.print("[bold]Step 3: Model Initialization[/bold]")

        # Load custom prompts if agent_path provided
        prompts = None
        if agent_path:
            try:
                from dva_agentic_cli.agents.onboard.prompts import load_prompts_from_dir
                prompts = load_prompts_from_dir(agent_path.resolve() / "prompts")
                console.print(f"  [green]✓[/green] Custom prompts loaded from {agent_path}/prompts/")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Could not load custom prompts: {e}")

        try:
            from dva_agentic_cli.agents.onboard.models import init_model
            model = init_model()
            console.print(f"  [green]✓[/green] Model initialized: gemini-2.5-flash-lite")

            # Quick smoke test
            console.print("  [dim]Sending test prompt...[/dim]")
            response = model.generate_content("Reply with exactly: AGENT_TEST_OK")
            if "AGENT_TEST_OK" in response.text:
                console.print(f"  [green]✓[/green] Model responded correctly")
            else:
                console.print(f"  [green]✓[/green] Model responded (content: {response.text[:80]}...)")
            if verbose:
                console.print(f"  [dim]Full response: {response.text[:200]}[/dim]")
            results["model"] = True
        except Exception as e:
            console.print(f"  [red]✗[/red] Model init failed: {e}")
            results["model"] = False
            if not step:
                _print_test_summary(results)
                raise typer.Exit(1)

    # --- Step 4: Analyze ---
    if "analyze" in steps_to_run:
        console.print("[bold]Step 4: Project Analysis[/bold]")
        if not path.exists():
            console.print(f"  [red]✗[/red] Path does not exist: {path}")
            results["analyze"] = False
        else:
            try:
                from dva_agentic_cli.analyzer.detector import analyze_project
                analysis = analyze_project(path)
                console.print(f"  [green]✓[/green] Languages: {', '.join(analysis.languages) or 'none'}")
                console.print(f"  [green]✓[/green] Frameworks: {', '.join(analysis.frameworks) or 'none'}")
                console.print(f"  [green]✓[/green] Dependencies: {len(analysis.dependencies)}")
                console.print(f"  [green]✓[/green] Databases: {', '.join(analysis.databases) or 'none'}")
                if verbose:
                    console.print(f"  [dim]Build tools: {', '.join(analysis.build_tools)}[/dim]")
                    console.print(f"  [dim]Test frameworks: {', '.join(analysis.test_frameworks)}[/dim]")
                    console.print(f"  [dim]Source patterns: {', '.join(analysis.source_patterns) if analysis.source_patterns else 'none'}[/dim]")
                    console.print(f"  [dim]Top deps: {', '.join(analysis.dependencies[:10])}[/dim]")
                results["analyze"] = True
            except Exception as e:
                console.print(f"  [red]✗[/red] Analysis failed: {e}")
                results["analyze"] = False

    # --- Step 5: Detect ---
    if "detect" in steps_to_run:
        console.print("[bold]Step 5: AI Gap Detection[/bold]")
        if analysis is None:
            try:
                from dva_agentic_cli.analyzer.detector import analyze_project
                analysis = analyze_project(path)
            except Exception:
                console.print("  [red]✗[/red] Cannot detect without analysis. Run step 4 first.")
                results["detect"] = False
                _print_test_summary(results)
                raise typer.Exit(1)

        if model is None:
            try:
                from dva_agentic_cli.agents.onboard.models import init_model
                model = init_model()
            except Exception as e:
                console.print(f"  [red]✗[/red] Cannot detect without model: {e}")
                results["detect"] = False
                _print_test_summary(results)
                raise typer.Exit(1)

        try:
            from dva_agentic_cli.analyzer.matcher import load_registry, match_skills, detect_mcp_servers
            from dva_agentic_cli.agents.onboard.gap_detector import detect_skill_gaps

            # Load registry
            config_data = _load_dva_config()
            reg_path_str = config_data.get("skills_registry")
            if reg_path_str:
                reg_path = Path(reg_path_str)
            else:
                reg_path = Path.home() / ".dva" / "skills-registry"

            if (reg_path / "registry.json").exists():
                registry_data = load_registry(reg_path)
                console.print(f"  [green]✓[/green] Registry loaded: {len(registry_data.get('skills', []))} skills")
            else:
                registry_data = {"skills": []}
                console.print(f"  [yellow]⚠[/yellow] No registry found at {reg_path}")

            mcp_servers = detect_mcp_servers(path)
            matches = match_skills(analysis, registry_data, mcp_servers)
            installed = [m.name for m in matches]
            console.print(f"  [green]✓[/green] Matched skills: {', '.join(installed) or 'none'}")

            console.print("  [dim]Calling Vertex AI for gap detection...[/dim]")
            gaps = detect_skill_gaps(
                analysis, installed, registry_data,
                model=model, prompts=prompts if agent_path else None,
            )
            console.print(f"  [green]✓[/green] Gaps detected: {len(gaps)}")
            for g in gaps:
                console.print(f"    • {g['skill_name']}: {g['description']}")
                if verbose:
                    console.print(f"      [dim]Reason: {g.get('reason', '')}[/dim]")
                    console.print(f"      [dim]Tags: {', '.join(g.get('tags', []))}[/dim]")
            results["detect"] = True
        except Exception as e:
            console.print(f"  [red]✗[/red] Detection failed: {e}")
            if verbose:
                import traceback
                console.print(f"  [dim]{traceback.format_exc()}[/dim]")
            results["detect"] = False

    # --- Step 6: Generate ---
    if "generate" in steps_to_run:
        console.print("[bold]Step 6: SKILL.md Generation[/bold]")
        if gaps and len(gaps) > 0:
            gap = gaps[0]
            try:
                from dva_agentic_cli.agents.onboard.skill_generator import generate_skill_content
                console.print(f"  [dim]Generating content for '{gap['skill_name']}'...[/dim]")
                content = generate_skill_content(
                    skill_name=gap["skill_name"],
                    description=gap["description"],
                    tags=gap.get("tags", []),
                    reason=gap.get("reason", ""),
                    model=model,
                    prompts=prompts if agent_path else None,
                )
                lines = content.strip().split("\n")
                console.print(f"  [green]✓[/green] Generated {len(lines)} lines")
                if verbose:
                    console.print(f"  [dim]Preview (first 10 lines):[/dim]")
                    for line in lines[:10]:
                        console.print(f"    {line}")
                results["generate"] = True
            except Exception as e:
                console.print(f"  [red]✗[/red] Generation failed: {e}")
                results["generate"] = False
        elif gaps is not None:
            console.print("  [dim]No gaps to generate content for (0 gaps detected).[/dim]")
            results["generate"] = True
        else:
            console.print("  [yellow]⚠[/yellow] Skipped — run step 5 first.")
            results["generate"] = False

    console.print()
    _print_test_summary(results)


def _print_test_summary(results: dict) -> None:
    """Print a summary table of test results."""
    step_names = {
        "deps": "Vertex AI packages",
        "config": "GCP configuration",
        "model": "Model initialization",
        "analyze": "Project analysis",
        "detect": "AI gap detection",
        "generate": "SKILL.md generation",
    }
    table = Table(show_header=True, header_style="bold cyan", title="Test Results")
    table.add_column("Step", style="bold")
    table.add_column("Status")

    all_pass = True
    for key, label in step_names.items():
        if key in results:
            if results[key]:
                table.add_row(label, "[green]✓ PASS[/green]")
            else:
                table.add_row(label, "[red]✗ FAIL[/red]")
                all_pass = False

    console.print(table)
    if all_pass and results:
        console.print("\n[bold green]All steps passed! Agent is working correctly.[/bold green]")
    elif not all_pass:
        console.print("\n[bold red]Some steps failed. Fix the errors above and re-run.[/bold red]")
        console.print("[dim]Run a single step: dva agent test --step <step-name>[/dim]")


def _load_dva_config() -> dict:
    """Load DVA CLI config."""
    config_file = Path.home() / ".dva" / "config.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except Exception:
            return {}
    return {}


def _is_process_running(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False
