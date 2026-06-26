"""Code onboarding commands — analyze repos and install context skills for AI code assistants."""

import json
import shutil
import subprocess
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from typing_extensions import Annotated

from agentic_cli.analyzer.detector import analyze_project, ProjectAnalysis
from agentic_cli.analyzer.matcher import (
    load_registry,
    match_skills,
    get_suggested_skills,
    detect_mcp_servers,
    SkillMatch,
    SkillProposal,
    save_proposals,
    load_proposals,
    accept_proposal,
    remove_proposal,
)
from agentic_cli.analyzer.project_context_skill import (
    generate_project_context_skill,
    generate_project_context_skill_content,
)
from agentic_cli.tracker import ActivityTimer, record_activity, register_repo, get_repos, remove_repo, get_domain
from agentic_cli.config import CLI_NAME

console = Console()
code_app = typer.Typer(help="Onboard repos with AI code assist skills", rich_markup_mode=None)

# Default skills registry location
DEFAULT_REGISTRY = Path.home() / ".dva" / "skills-registry"
AGENT_CONFIG_DIR = Path.home() / ".agent-cli-agentic"
AGENT_CONFIG_FILE = AGENT_CONFIG_DIR / "config.json"


def _get_config() -> dict:
    """Load CLI global config."""
    if AGENT_CONFIG_FILE.exists():
        try:
            return json.loads(AGENT_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(config: dict) -> None:
    """Save CLI global config."""
    AGENT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _get_registry_path() -> Path:
    """Get the configured skills registry path."""
    config = _get_config()
    registry = config.get("skills_registry")
    if registry:
        return Path(registry)
    return DEFAULT_REGISTRY


def _ensure_registry(registry_override: Optional[str] = None) -> Path:
    """Ensure the skills registry is available. Clone if needed."""
    if registry_override:
        reg_path = Path(registry_override).resolve()
        if not reg_path.exists():
            console.print(f"[red]✗ Registry not found at {reg_path}[/red]")
            raise typer.Exit(1)
        return reg_path

    reg_path = _get_registry_path()

    if reg_path.exists() and (reg_path / "registry.json").exists():
        return reg_path

    # Try to find local skills in the workspace
    workspace_registry = Path.cwd().parent / "skills"
    if workspace_registry.exists() and (workspace_registry / "registry.json").exists():
        return workspace_registry

    # Check if registry URL is configured
    config = _get_config()
    registry_url = config.get("skills_registry_url")
    if registry_url:
        console.print(f"[dim]Cloning skills registry from {registry_url}...[/dim]")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", registry_url, str(reg_path)],
                capture_output=True, check=True,
            )
            return reg_path
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Failed to clone registry: {e.stderr.decode() if e.stderr else str(e)}[/red]")
            raise typer.Exit(1)

    console.print("[red]✗ Skills registry not found.[/red]")
    console.print(f"[dim]Set registry path: {CLI_NAME} code config --registry <path-or-url>[/dim]")
    raise typer.Exit(1)


def _get_skills_dir(project_path: Path, code_assist_tool: str) -> Path:
    """Get the skills directory based on the code assist tool."""
    if code_assist_tool == "windsurf":
        return project_path / ".windsurf" / "workflows"
    elif code_assist_tool == "cursor":
        return project_path / ".cursorrules"
    else:
        return project_path / ".skills"


def _generate_project_context_skill(
    project_path: Path,
    analysis: ProjectAnalysis,
    code_assist_tool: str = "generic",
    domain: Optional[str] = None,
    product: Optional[str] = None,
) -> None:
    """Generate a unified project context skill with MCP fallback chain.

    This creates a single root skill that provides access to:
    - graphify: Code structure queries
    - dva-kg-mcp: Requirements and release context
    - anchor mcp: Jira, Bitbucket, Confluence
    - glean: Fallback for general knowledge

    Args:
        project_path: Path to the project repository
        analysis: Project analysis results
        code_assist_tool: Code assist tool being used
        domain: Optional domain name (e.g., "cwow-facility")
        product: Optional product name (e.g., "CWOW")
    """
    skills_dir = _get_skills_dir(project_path, code_assist_tool)
    skill_dir = skills_dir / "project-context"
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Generate skill content using the new module
    content = generate_project_context_skill_content(
        project_path=project_path,
        analysis=analysis,
        domain=domain,
        product=product,
    )

    (skill_dir / "SKILL.md").write_text(content)


def _install_skill_from_registry(skill_name: str, registry_path: Path, target_path: Path, code_assist_tool: str = "generic") -> bool:
    """Copy a skill from the registry to the project's skills directory."""
    source = registry_path / "skills" / skill_name
    if not source.exists() or not (source / "SKILL.md").exists():
        return False

    skills_dir = _get_skills_dir(target_path, code_assist_tool)
    dest = skills_dir / skill_name
    if dest.exists():
        shutil.rmtree(dest)

    shutil.copytree(source, dest)
    return True


def _save_onboard_manifest(project_path: Path, analysis: ProjectAnalysis, installed: list[str], suggested: list[str], code_assist_tool: str = "generic") -> None:
    """Save onboard.json manifest for validate/skills commands."""
    skills_dir = _get_skills_dir(project_path, code_assist_tool)
    manifest = {
        "version": "1.0",
        "project": project_path.name,
        "analysis": analysis.to_dict(),
        "installed_skills": installed,
        "suggested_skills": suggested,
        "code_assist_tool": code_assist_tool,
    }
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "onboard.json").write_text(json.dumps(manifest, indent=2))


def _run_graphify_update(project_path: Path, code_assist_tool: str = "generic") -> bool:
    """Run graphify update command to generate code structure graph.

    Args:
        project_path: Path to the project directory
        code_assist_tool: Code assist tool being used (windsurf, cursor, or generic)

    Returns:
        True if successful, False otherwise
    """
    console.print("[cyan]Running graphify update to generate code structure graph...[/cyan]")
    
    # Check if graphify is available
    try:
        subprocess.run(
            ["graphify", "--help"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[yellow]⚠ graphify not found. Install with: pip install graphifyy[/yellow]")
        return False
    
    try:
        # Run graphify update from project directory so graphify-out is created inside the project
        result = subprocess.run(
            ["graphify", "update", ".", "--force"],
            capture_output=True,
            text=True,
            cwd=str(project_path),
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ graphify update completed[/green]")
            if result.stdout:
                # Show summary output
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:  # Show last 5 lines
                    console.print(f"[dim]{line}[/dim]")
            
            # Install graphify workflow for Windsurf
            if code_assist_tool == "windsurf":
                _install_graphify_windsurf_workflow(project_path)
            
            return True
        else:
            console.print(f"[yellow]⚠ graphify update failed with code {result.returncode}[/yellow]")
            if result.stderr:
                console.print(f"[dim]{result.stderr[:500]}[/dim]")
            return False
            
    except Exception as e:
        console.print(f"[yellow]⚠ graphify update failed: {e}[/yellow]")
        return False


def _install_graphify_windsurf_workflow(project_path: Path) -> None:
    """Install graphify workflow for Windsurf."""
    windsurf_workflows_dir = project_path / ".windsurf" / "workflows"
    windsurf_workflows_dir.mkdir(parents=True, exist_ok=True)
    
    graphify_workflow = windsurf_workflows_dir / "graphify.md"
    
    workflow_content = """---
description: Use graphify knowledge graph for codebase questions and architecture context
---

# Graphify Knowledge Graph Workflow

This project has a graphify knowledge graph at `graphify-out/`.

## When to Use Graphify

For codebase or architecture questions, when `graphify-out/graph.json` exists:

1. **First try graphify queries** - These return a scoped subgraph, usually much smaller than raw grep output:
   - `graphify query "<question>"` - BFS traversal of the graph for a question
   - `graphify path "<A>" "<B>"` - Shortest path between two nodes
   - `graphify explain "<concept>"` - Plain-language explanation of a node and its neighbors

2. **Check the wiki** - If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files

3. **Read the report** - Use `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context

## Keeping the Graph Current

After modifying code files in this session, run:
```bash
graphify update .
```

This updates the graph using AST-only extraction (no API cost).

## Graphify Commands Reference

- `graphify update <path> --force` - Re-extract code files and update the graph
- `graphify query "<question>"` - BFS traversal of graph.json for a question
- `graphify path "A" "B"` - Shortest path between two nodes in graph.json
- `graphify explain "X"` - Plain-language explanation of a node and its neighbors
- `graphify tree` - Emit a D3 v7 collapsible-tree HTML for graph.json

## Output Files

- `graphify-out/graph.json` - The code structure graph
- `graphify-out/GRAPH_REPORT.md` - Broad architecture report
- `graphify-out/wiki/index.md` - Navigable wiki (if generated)
- `graphify-out/manifest.json` - File metadata and hashes
"""
    
    graphify_workflow.write_text(workflow_content)
    console.print(f"[green]✓ Graphify workflow installed for Windsurf[/green]")


def _run_agent(
    agent_path: Optional[Path],
    registry_path: Path,
    analysis: ProjectAnalysis,
    installed_names: list[str],
    registry_data: dict,
    project_path: Path,
    enrich: bool,
) -> dict:
    """Run the onboard agent — external project or built-in library.

    If agent_path is provided, runs the external agent as a subprocess.
    Otherwise, uses the built-in pipeline from agentic_cli.agents.onboard.
    """
    if agent_path:
        # --- External agent project ---
        agent_dir = agent_path.resolve()
        main_py = agent_dir / "src" / "main.py"
        if not main_py.exists():
            console.print(f"[red]✗ Agent project not found: {main_py}[/red]")
            console.print("[dim]Expected structure: <agent-path>/src/main.py[/dim]")
            raise typer.Exit(1)

        console.print(f"[cyan]Running external onboard agent: {agent_dir.name}...[/cyan]")

        import tempfile
        output_file = Path(tempfile.mktemp(suffix=".json"))

        cmd = [
            "python", str(main_py),
            "--project-path", str(project_path),
            "--registry-path", str(registry_path),
            "--output", str(output_file),
        ]
        if enrich:
            cmd.append("--enrich")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(agent_dir))
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if not line.startswith("{") and not line.startswith("["):
                        console.print(f"  [dim]{line}[/dim]")

            if result.returncode != 0:
                console.print(f"[yellow]⚠ Agent exited with code {result.returncode}[/yellow]")
                if result.stderr:
                    console.print(f"[dim]{result.stderr[:500]}[/dim]")
                return {"proposals": [], "enriched": [], "errors": [f"Agent exit code: {result.returncode}"]}

            if output_file.exists():
                import json as _json
                data = _json.loads(output_file.read_text())
                return {
                    "proposals": data.get("proposals", []),
                    "enriched": [{"skill_name": s, "content": ""} for s in data.get("enriched", [])],
                    "errors": data.get("errors", []),
                }
            else:
                return {"proposals": [], "enriched": [], "errors": ["No output file generated"]}

        except FileNotFoundError:
            console.print("[red]✗ Python not found. Ensure the agent's venv is activated.[/red]")
            return {"proposals": [], "enriched": [], "errors": ["Python not found"]}
        finally:
            if output_file.exists():
                output_file.unlink()
    else:
        # --- Built-in library ---
        console.print("[cyan]Running onboard agent (AI skill gap detection)...[/cyan]")
        from agentic_cli.agents.onboard.pipeline import run_onboard_pipeline

        # Check for default agent prompts in skills registry
        prompts = None
        default_agent_dir = registry_path / "agents" / "onboard"
        if default_agent_dir.is_dir():
            from agentic_cli.agents.onboard.prompts import load_prompts_from_dir
            prompts = load_prompts_from_dir(default_agent_dir / "prompts")
            console.print(f"[dim]Using prompts from {default_agent_dir}[/dim]")

        return run_onboard_pipeline(
            analysis=analysis,
            installed_skills=installed_names,
            registry=registry_data,
            registry_path=registry_path,
            project_path=project_path,
            enrich=enrich,
            prompts=prompts,
        )


# --- Commands ---


@code_app.command("init")
def init_workspace(
    workspace: Annotated[
        Path,
        typer.Argument(help="Local folder where repos will be cloned and onboarded"),
    ],
) -> None:
    """
    Set a default workspace folder for cloning and onboarding repos.

    All repos cloned via {CLI_NAME} code onboard --repo <url> will land here
    unless --target is explicitly provided.

    Examples:
        {CLI_NAME} code init ~/{CLI_NAME}-workspace
        {CLI_NAME} code init /opt/repos
    """.format(CLI_NAME=CLI_NAME)
    ws = workspace.expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)

    config = _get_config()
    config["code_workspace"] = str(ws)
    _save_config(config)

    record_activity(
        command="code", subcommand="init",
        args={"workspace": str(ws)},
    )

    console.print(Panel.fit(
        f"[bold green]✓ Code workspace configured[/bold green]\n\n"
        f"[bold]Workspace:[/bold] {ws}\n\n"
        f"[dim]Repos cloned via {CLI_NAME} code onboard --repo <url> will\n"
        f"be placed in this folder by default.[/dim]",
        border_style="green",
    ))


@code_app.command("onboard")
def onboard(
    repo: Annotated[
        Optional[str],
        typer.Option("--repo", "-r", help="Git repo URL to clone and onboard"),
    ] = None,
    repo_slug: Annotated[
        Optional[str],
        typer.Option("--repo-slug", help="Repo slug from domain's linked repos (requires --domain)"),
    ] = None,
    path: Annotated[
        Optional[Path],
        typer.Option("--path", "-p", help="Local project path to onboard"),
    ] = None,
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target directory for cloning (with --repo)"),
    ] = None,
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", help="Override skills registry path or URL"),
    ] = None,
    agent: Annotated[
        bool,
        typer.Option("--agent/--no-agent", help="Use AI agent for skill gap detection and proposal generation"),
    ] = False,
    agent_path: Annotated[
        Optional[Path],
        typer.Option("--agent-path", help="Path to a custom onboard agent project (overrides default)"),
    ] = None,
    enrich: Annotated[
        bool,
        typer.Option("--enrich/--no-enrich", help="Enrich installed skills with project-specific context (requires --agent)"),
    ] = False,
    kg: Annotated[
        bool,
        typer.Option("--kg/--no-kg", help="Generate kg-code-context.md and ingest into configured KG provider"),
    ] = False,
    extract_entities: Annotated[
        bool,
        typer.Option("--extract-entities/--no-extract-entities", help="Full KG ingestion with entity extraction (requires --kg)"),
    ] = False,
    domain: Annotated[
        Optional[str],
        typer.Option("--domain", "-d", help="Domain slug to attach domain KG context (e.g. cwow-facility)"),
    ] = None,
    domain_context_repo: Annotated[
        Optional[str],
        typer.Option("--domain-context-repo", help="Git URL of central domain context repo to add as submodule"),
    ] = None,
    use_domain_skills: Annotated[
        bool,
        typer.Option("--use-domain-skills/--no-domain-skills", help="Install domain-validated skills from domain-context repo (requires --domain)"),
    ] = False,
    link_kg: Annotated[
        bool,
        typer.Option("--link-kg/--no-link-kg", help="Link code context to KG requirements using LLM (requires --domain and --kg)"),
    ] = False,
    graphify: Annotated[
        bool,
        typer.Option("--graphify/--no-graphify", help="Run graphify update to generate code structure graph"),
    ] = False,
    all_skills: Annotated[
        bool,
        typer.Option("--all-skills", help="Install all dependency-based skills (may be deprecated in future)"),
    ] = False,
    code_assist_tool: Annotated[
        str,
        typer.Option("--code-assist-tool", help="Code assist tool (windsurf, cursor, or generic). Determines where skills are installed."),
    ] = "generic",
    link_meta_repo: Annotated[
        bool,
        typer.Option("--link-meta-repo/--no-link-meta-repo", help="Detect and link domain meta-repo as submodule (requires --domain)"),
    ] = False,
    okf_enrich: Annotated[
        bool,
        typer.Option("--okf-enrich/--no-okf-enrich", help="Generate/enrich an OKF knowledge bundle using the enrichment agent (requires --domain, Vertex AI)"),
    ] = False,
    okf_model: Annotated[
        Optional[str],
        typer.Option("--okf-model", help="Vertex AI model for OKF enrichment (default: gemini-2.5-flash-lite)"),
    ] = None,
    okf_no_confluence: Annotated[
        bool,
        typer.Option("--okf-no-confluence", help="Skip the Confluence enrichment pass during OKF enrichment"),
    ] = False,
) -> None:
    """
    Onboard a repository for AI code assist.

    Clones the repo (if URL provided), analyzes the project, and installs
    the project-context skill with MCP fallback chain by default.

    Examples:
        {CLI_NAME} code onboard --path ./my-repo
        {CLI_NAME} code onboard --repo https://bitbucket.example.com/scm/PROJ/my-repo.git
        {CLI_NAME} code onboard --repo <url> --target ./workspace
        {CLI_NAME} code onboard --path ./my-repo --registry /path/to/skills
        {CLI_NAME} code onboard --path ./my-repo --kg
        {CLI_NAME} code onboard --path ./my-repo --kg --extract-entities
        {CLI_NAME} code onboard --path ./my-repo --domain cwow-facility --kg
        {CLI_NAME} code onboard --path ./my-repo --domain cwow-facility --domain-context-repo https://github.com/company/facility-domain-context.git
        {CLI_NAME} code onboard --path ./my-repo --domain cwow-facility --use-domain-skills
        {CLI_NAME} code onboard --domain cwow-facility --repo-slug cwow-facility-watercheck --kg
        {CLI_NAME} code onboard --domain cwow-facility --repo-slug cwow-facility-watercheck --kg --link-kg
        {CLI_NAME} code onboard --path ./my-repo --graphify
        {CLI_NAME} code onboard --path ./my-repo --all-skills  # Install all dependency-based skills (may be deprecated)
    """.format(CLI_NAME=CLI_NAME)
    
    # Validate link_kg flag
    if link_kg and not domain:
        console.print("[red]--link-kg requires --domain[/red]")
        raise typer.Exit(1)
    if link_kg and not kg:
        console.print("[red]--link-kg requires --kg[/red]")
        raise typer.Exit(1)
    if okf_enrich and not domain:
        console.print("[red]--okf-enrich requires --domain[/red]")
        raise typer.Exit(1)
    # Handle repo-slug option
    if repo_slug:
        if not domain:
            console.print("[red]--repo-slug requires --domain[/red]")
            raise typer.Exit(1)
        from agentic_cli.tracker import get_domain_repos
        repos = get_domain_repos(domain)
        matched_repo = None
        for r in repos:
            if r["repo_slug"] == repo_slug:
                matched_repo = r
                break
        if not matched_repo:
            console.print(f"[red]Repo slug '{repo_slug}' not found in domain '{domain}' linked repos[/red]")
            console.print(f"[dim]Available repos: {', '.join(r['repo_slug'] for r in repos)}[/dim]")
            raise typer.Exit(1)
        repo = matched_repo["clone_url"]
        console.print(f"[cyan]Using repo from linked repos: {repo}[/cyan]")

    if not repo and not path:
        console.print("[red]Provide --repo (URL), --repo-slug (with --domain), or --path (local directory)[/red]")
        raise typer.Exit(1)

    if use_domain_skills and not domain:
        console.print("[red]--use-domain-skills requires --domain[/red]")
        raise typer.Exit(1)

    # Step 1: Clone if repo URL provided
    if repo:
        if target:
            project_path = target.resolve()
        else:
            # Use configured workspace, fall back to CWD
            config = _get_config()
            workspace_dir = config.get("code_workspace")
            if workspace_dir:
                base = Path(workspace_dir)
                # Ensure workspace directory exists
                if not base.exists():
                    console.print(f"[yellow]Workspace directory does not exist: {base}[/yellow]")
                    console.print(f"[dim]Creating workspace directory...[/dim]")
                    try:
                        base.mkdir(parents=True, exist_ok=True)
                        console.print(f"[green]✓[/green] Created: {base}")
                    except Exception as e:
                        console.print(f"[red]✗ Failed to create workspace: {e}[/red]")
                        raise typer.Exit(1)

                # If using --repo-slug with --domain, clone into domain folder
                if repo_slug and domain:
                    domain_folder = base / domain
                    if not domain_folder.exists():
                        try:
                            domain_folder.mkdir(parents=True, exist_ok=True)
                            console.print(f"[green]✓[/green] Created domain folder: {domain_folder}")
                        except Exception as e:
                            console.print(f"[red]✗ Failed to create domain folder: {e}[/red]")
                            raise typer.Exit(1)
                    base = domain_folder
            else:
                base = Path.cwd()
            repo_name = repo.rstrip("/").split("/")[-1].replace(".git", "")
            project_path = base / repo_name

        if project_path.exists():
            console.print(f"[yellow]Directory {project_path} already exists.[/yellow]")
            overwrite = typer.confirm("Use existing directory?", default=True)
            if not overwrite:
                raise typer.Exit(0)
        else:
            console.print(f"[dim]Cloning {repo}...[/dim]")
            try:
                subprocess.run(
                    ["git", "clone", repo, str(project_path)],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                console.print(f"[red]✗ Clone failed: {e}[/red]")
                raise typer.Exit(1)
    else:
        project_path = path.resolve()
        if not project_path.exists():
            console.print(f"[red]✗ Path does not exist: {project_path}[/red]")
            raise typer.Exit(1)

    # Step 2: Ensure registry
    registry_path = _ensure_registry(registry)

    # Step 3: Analyze project
    console.print(f"[cyan]Analyzing {project_path.name}...[/cyan]")
    analysis = analyze_project(project_path)

    # Step 3b: Run graphify update (optional)
    graphify_result = None
    if graphify:
        console.print()
        graphify_result = _run_graphify_update(project_path, code_assist_tool)

    # Step 4: Detect configured MCP servers
    mcp_servers = detect_mcp_servers(project_path)

    # Step 5: Match skills from registry (skip by default, use --all-skills to enable)
    registry_data = load_registry(registry_path)
    matches = []
    if all_skills:
        matches = match_skills(analysis, registry_data, mcp_servers)
        console.print("[cyan]Installing all dependency-based skills (--all-skills)[/cyan]")
    else:
        console.print("[dim]Skipping dependency-based skill matching (default: project-context only)[/dim]")
        console.print("[dim]Use --all-skills to install all skills (may be deprecated in future)[/dim]")

    # Step 6: Generate project-context skill (always)
    # Fetch product from domain config if domain is provided
    product_from_domain = None
    if domain:
        domain_info = get_domain(domain)
        if domain_info:
            product_from_domain = domain_info.get("product")
            if product_from_domain:
                console.print(f"[dim]Product from domain config: {product_from_domain}[/dim]")

    _generate_project_context_skill(project_path, analysis, code_assist_tool, domain, product_from_domain)
    installed_names = ["project-context"]

    # Step 6b: Install default skills (only if --all-skills)
    if all_skills:
        default_skills = [s for s in registry_data.get("skills", []) if s.get("default")]
        for skill in default_skills:
            skill_name = skill["name"]
            install_path = skill.get("install_path")
            source = skill.get("source")

            if source == "system" and install_path:
                # System skill - copy from system path
                source_path = Path(install_path).expanduser()
                if source_path.exists():
                    skills_dir = _get_skills_dir(project_path, code_assist_tool)
                    dest = skills_dir / skill_name
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.copy(source_path, dest / "SKILL.md")
                    installed_names.append(skill_name)
                    console.print(f"[dim]Installed default skill: {skill_name}[/dim]")
            else:
                # Registry skill - install from registry
                if _install_skill_from_registry(skill_name, registry_path, project_path, code_assist_tool):
                    installed_names.append(skill_name)
                    console.print(f"[dim]Installed default skill: {skill_name}[/dim]")

    # Step 7: Install matched skills (only if --all-skills)
    if all_skills:
        for match in matches:
            if match.name not in installed_names:  # Don't install if already installed as default
                if _install_skill_from_registry(match.name, registry_path, project_path, code_assist_tool):
                    installed_names.append(match.name)

    # Step 7b: Install domain-validated skills (optional)
    domain_skills_installed = []
    if use_domain_skills and domain:
        console.print(f"[cyan]Loading domain-validated skills for '{domain}'...[/cyan]")
        try:
            from agentic_cli.kg.domain_skills import load_domain_skills, install_domain_skill
            from agentic_cli.commands.domain import _resolve_domain_context_dir

            ctx_dir = None
            # Try domain-context-repo submodule first
            sub_path = project_path / ".domain-context"
            if sub_path.exists() and (sub_path / ".domain").exists():
                ctx_dir = sub_path
            else:
                try:
                    ctx_dir = _resolve_domain_context_dir(domain)
                except (SystemExit, Exception):
                    ctx_dir = None

            if ctx_dir:
                domain_skill_map = load_domain_skills(ctx_dir)
                # Priority: validated first, then customized, then injected
                priority_order = []
                for sname, sinfo in domain_skill_map.items():
                    if sinfo.get("validated"):
                        priority_order.insert(0, (sname, sinfo))  # front
                    elif sinfo.get("customized"):
                        priority_order.append((sname, sinfo))  # middle
                    else:
                        priority_order.append((sname, sinfo))  # end

                for sname, sinfo in priority_order:
                    if sname not in installed_names:
                        if install_domain_skill(sname, sinfo["path"], project_path):
                            installed_names.append(sname)
                            domain_skills_installed.append(sname)
                            status_tag = "validated" if sinfo.get("validated") else "injected"
                            console.print(f"  [green]✓[/green] {sname} [dim]({status_tag})[/dim]")

                if domain_skills_installed:
                    console.print(f"[green]✓ {len(domain_skills_installed)} domain skills installed[/green]")
                else:
                    console.print("[dim]No additional domain skills to install[/dim]")
            else:
                console.print("[yellow]⚠ Domain context repo not found — skipping domain skills[/yellow]")
                console.print(f"[dim]Use --domain-context-repo or run: dva domain init-context {domain}[/dim]")

        except Exception as e:
            console.print(f"[yellow]⚠ Domain skills loading failed: {e}[/yellow]")

    # Step 8: Get suggestions
    suggestions = get_suggested_skills(analysis, registry_data, installed_names, mcp_servers)
    suggested_names = [s.name for s in suggestions]

    # Step 9: Save manifest
    _save_onboard_manifest(project_path, analysis, installed_names, suggested_names, code_assist_tool)

    # Step 9a: Agent-powered skill gap detection (optional)
    agent_result = None
    if agent or agent_path:
        console.print()
        try:
            agent_result = _run_agent(
                agent_path=agent_path,
                registry_path=registry_path,
                analysis=analysis,
                installed_names=installed_names,
                registry_data=registry_data,
                project_path=project_path,
                enrich=enrich,
            )

            # Show errors first so they aren't hidden
            if agent_result.get("errors"):
                for err in agent_result["errors"]:
                    console.print(f"[yellow]⚠ {err}[/yellow]")
                console.print(f"[dim]Test agent in isolation: {CLI_NAME} agent test --path <project>[/dim]")

            if agent_result["proposals"]:
                # Save proposals for later review
                proposals = [
                    SkillProposal(
                        skill_name=p["skill_name"],
                        description=p["description"],
                        tags=p.get("tags", []),
                        reason=p.get("reason", ""),
                        auto_detect=p.get("auto_detect", {}),
                        content=p.get("content", ""),
                        project=project_path.name,
                    )
                    for p in agent_result["proposals"]
                ]
                proposals_path = save_proposals(proposals, project_path.name)
                console.print(f"[green]✓ {len(proposals)} skill proposals generated[/green]")
                console.print(f"[dim]Review with: {CLI_NAME} code skills propose[/dim]")
            elif not agent_result.get("errors"):
                console.print("[dim]No skill gaps detected by agent.[/dim]")

            if agent_result.get("enriched"):
                skills_dir = _get_skills_dir(project_path, code_assist_tool)
                for enriched in agent_result["enriched"]:
                    skill_md = skills_dir / enriched["skill_name"] / "SKILL.md"
                    if skill_md.exists():
                        skill_md.write_text(enriched["content"])
                console.print(f"[green]✓ {len(agent_result['enriched'])} skills enriched with project context[/green]")

        except ImportError as e:
            console.print(f"[yellow]⚠ Agent requires Vertex AI: {e}[/yellow]")
            console.print("[dim]Install with: pip install google-cloud-aiplatform[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ Agent failed: {e}[/yellow]")

    # Step 9b: Register repo centrally for tracking
    register_repo(
        name=project_path.name,
        path=str(project_path),
        repo_url=repo,
        languages=analysis.languages,
        frameworks=analysis.frameworks,
        build_tools=analysis.build_tools,
        test_frameworks=analysis.test_frameworks,
        databases=analysis.databases,
        dependencies=len(analysis.dependencies),
        skills_installed=installed_names,
        has_docker=analysis.has_docker,
    )

    # Step 9c: Domain context pipeline (optional — runs before KG pipeline)
    domain_result = None
    if domain:
        console.print()
        console.print(f"[cyan]Attaching domain context for '{domain}'...[/cyan]")
        try:
            from agentic_cli.kg.domain_context import (
                query_domain_kg,
                build_domain_skill_md,
                build_domain_metadata,
            )

            # Look up domain registration
            domain_data = get_domain(domain)
            domain_repos = get_domain_repos(domain) if domain_data else []

            # Query KG for domain business context
            console.print("[dim]Querying Knowledge Graph for domain context...[/dim]")
            kg_domain_ctx = query_domain_kg(domain)
            has_kg = any(kg_domain_ctx.values())

            if has_kg:
                console.print(f"[green]\u2713 KG domain context retrieved ({sum(1 for v in kg_domain_ctx.values() if v)}/6 aspects)[/green]")
            else:
                # Get the configured KG provider for the warning message
                try:
                    from agentic_cli.kg.config import KGConfig
                    kg_config = KGConfig.load()
                    provider = kg_config.provider
                    console.print(f"[yellow]\u26a0 No domain context found in KG ({provider} may not be running or domain not ingested)[/yellow]")
                except Exception:
                    console.print("[yellow]\u26a0 No domain context found in KG (provider may not be running or domain not ingested)[/yellow]")

            # Generate domain-context skill
            skills_dir = _get_skills_dir(project_path, code_assist_tool)
            skill_dir = skills_dir / "domain-context"
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_content = build_domain_skill_md(
                domain, domain_data, kg_domain_ctx,
                repo_type=project_path.name.rsplit("-", 1)[-1] if "-" in project_path.name else "",
            )
            (skill_dir / "SKILL.md").write_text(skill_content)
            installed_names.append("domain-context")
            console.print(f"[green]\u2713 Domain context skill installed:[/green] {skill_dir}/SKILL.md")

            # Write .domain-context.json metadata
            meta = build_domain_metadata(
                domain, domain_data, domain_repos, domain_context_repo,
            )
            meta_path = project_path / ".domain-context.json"
            meta_path.write_text(json.dumps(meta, indent=2))
            console.print(f"[green]\u2713 Domain metadata written:[/green] .domain-context.json")

            # Add git submodule reference if --domain-context-repo provided.
            # Branch is auto-detected (host-agnostic: bitbucket/gitlab/github).
            if domain_context_repo:
                console.print(f"[dim]Adding domain context repo as git submodule...[/dim]")
                try:
                    from agentic_cli.meta_repo.git_utils import add_submodule
                    submodule_path = project_path / ".domain-context"
                    if not submodule_path.exists():
                        used_branch = add_submodule(
                            project_path, domain_context_repo, ".domain-context",
                        )
                        branch_note = f" (branch: {used_branch})" if used_branch else ""
                        console.print(f"[green]\u2713 Git submodule added:[/green] .domain-context -> {domain_context_repo}{branch_note}")
                    else:
                        console.print(f"[yellow]\u26a0 .domain-context/ already exists, skipping submodule add[/yellow]")
                except subprocess.CalledProcessError as e:
                    stderr = e.stderr.decode() if e.stderr else str(e)
                    console.print(f"[yellow]\u26a0 Git submodule add failed: {stderr}[/yellow]")
                    console.print("[dim]You can add it manually later: git submodule add <url> .domain-context[/dim]")

            # Mark repo as onboarded in domain tracker
            if domain_data:
                try:
                    from agentic_cli.tracker import mark_domain_repo_onboarded
                    mark_domain_repo_onboarded(domain, project_path.name)
                except Exception:
                    pass  # non-critical

            domain_result = {
                "domain": domain,
                "kg_aspects_found": sum(1 for v in kg_domain_ctx.values() if v),
                "domain_context_repo": domain_context_repo,
                "skill_installed": True,
                "metadata_written": True,
            }

        except Exception as e:
            console.print(f"[yellow]\u26a0 Domain context attachment failed: {e}[/yellow]")
            console.print("[dim]Onboarding will continue without domain context.[/dim]")

    # Step 9c-meta: Domain meta-repo detection and linking (optional)
    meta_repo_result = None
    if link_meta_repo and domain:
        console.print()
        console.print(f"[cyan]Detecting domain meta-repo for '{domain}'...[/cyan]")
        try:
            from agentic_cli.meta_repo import detect_domain_meta_repo

            meta_repo_path = detect_domain_meta_repo(domain)
            if meta_repo_path:
                console.print(f"[green]✓ Found domain meta-repo:[/green] {meta_repo_path}")

                # Add as git submodule. The meta-repo is typically a local path,
                # so the branch is auto-detected (works for local paths too).
                try:
                    from agentic_cli.meta_repo.git_utils import add_submodule
                    submodule_path = project_path / ".domain-meta"
                    if not submodule_path.exists():
                        used_branch = add_submodule(
                            project_path, str(meta_repo_path), ".domain-meta",
                        )
                        branch_note = f" (branch: {used_branch})" if used_branch else ""
                        console.print(f"[green]✓ Git submodule added:[/green] .domain-meta -> {meta_repo_path}{branch_note}")
                    else:
                        console.print(f"[yellow]⚠ .domain-meta/ already exists, skipping submodule add[/yellow]")
                except subprocess.CalledProcessError as e:
                    stderr = e.stderr.decode() if e.stderr else str(e)
                    console.print(f"[yellow]⚠ Git submodule add failed: {stderr}[/yellow]")

                meta_repo_result = {
                    "detected": True,
                    "path": str(meta_repo_path),
                }
            else:
                console.print(f"[yellow]⚠ Domain meta-repo not found for '{domain}'[/yellow]")
                console.print(f"[dim]Create one with: dva domain init-meta {domain}[/dim]")
                meta_repo_result = {
                    "detected": False,
                }

        except Exception as e:
            console.print(f"[yellow]⚠ Meta-repo detection failed: {e}[/yellow]")

    # Step 9c-okf: OKF knowledge bundle enrichment (optional)
    okf_result = None
    if okf_enrich and domain:
        console.print()
        console.print(f"[cyan]Generating OKF knowledge bundle for '{domain}'...[/cyan]")
        try:
            from agentic_cli.kg.okf.enrichment.domain_paths import (
                resolve_domain_enrichment_context,
            )
            from agentic_cli.kg.okf.enrichment.runner import EnrichmentRunner
            from agentic_cli.kg.okf.enrichment.sources.code import CodebaseSource
            from agentic_cli.kg.okf.enrichment.sources.confluence import ConfluenceSource
            from agentic_cli.kg.okf.schema import OKFSchema

            okf_ctx = resolve_domain_enrichment_context(domain)
            bundle_dir = okf_ctx.bundle_dir

            # Use the repo being onboarded as the structural source.
            code_src = CodebaseSource(project_path, analysis)
            confluence_src = None
            if not okf_no_confluence and okf_ctx.confluence_docs:
                confluence_src = ConfluenceSource.from_domain_docs(okf_ctx.confluence_docs)

            # Ensure the bundle carries a canonical schema.
            schema_path = bundle_dir / "okf.schema.yaml"
            if not schema_path.exists():
                bundle_dir.mkdir(parents=True, exist_ok=True)
                OKFSchema.canonical(domain=domain, product=okf_ctx.product).dump(schema_path)

            runner = EnrichmentRunner(
                source=code_src,
                bundle_root=bundle_dir,
                model_name=okf_model,
                confluence_source=confluence_src,
            )
            res = runner.enrich_all()
            console.print(
                f"[green]✓ OKF bundle:[/green] {res.concepts_written} written, "
                f"{res.concepts_enriched} enriched, {res.pages_processed} Confluence page(s) "
                f"-> {bundle_dir}"
            )
            if res.errors:
                console.print(f"[yellow]⚠ {len(res.errors)} enrichment warning(s)[/yellow]")
            okf_result = {
                "bundle_dir": str(bundle_dir),
                "written": res.concepts_written,
                "enriched": res.concepts_enriched,
                "pages": res.pages_processed,
            }
        except Exception as e:
            console.print(f"[yellow]⚠ OKF enrichment failed: {e}[/yellow]")
            console.print("[dim]Onboarding will continue without the OKF bundle.[/dim]")

    # Step 9d: KG context pipeline (optional)
    kg_result = None
    if kg:
        console.print()
        console.print("[cyan]Preparing project context for Knowledge Graph...[/cyan]")
        try:
            from agentic_cli.kg.context_builder import run_kg_context_pipeline

            kg_result = run_kg_context_pipeline(
                project_path=project_path,
                analysis=analysis,
                installed_skills=installed_names,
                suggested_skills=suggested_names,
                ingest=not extract_entities,  # light mode: ingest directly
            )

            if kg_result["context_path"]:
                console.print(f"[green]\u2713 KG context saved:[/green] {kg_result['context_path']}")
            if kg_result["source"]:
                console.print(f"[green]\u2713 Registered data source:[/green] {kg_result['source']['name']}")
            if kg_result["skill_patched"]:
                console.print(f"[green]\u2713 SKILL.md updated with context-first workflow instructions[/green]")
            if kg_result["ingested"]:
                provider = kg_result.get("provider", "unknown")
                console.print(f"[green]\u2713 Context ingested into {provider}[/green]")

            # Link code to KG requirements if --link-kg is set
            if link_kg and domain:
                console.print()
                console.print("[cyan]Linking code to KG requirements...[/cyan]")
                try:
                    from agentic_cli.kg.context_builder import link_code_to_requirements

                    link_result = link_code_to_requirements(
                        project_path=project_path,
                        domain_slug=domain,
                    )

                    if link_result["success"]:
                        console.print(f"[green]\u2713 Created {link_result['links_created']} code-requirement links[/green]")
                    else:
                        console.print(f"[yellow]\u26a0 Linking failed: {link_result.get('error', 'Unknown error')}[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]\u26a0 Linking error: {e}[/yellow]")

            # Full mode: use {CLI_NAME} kg ingest pipeline with entity extraction
            if extract_entities and kg_result["source"]:
                console.print("[cyan]Running full KG ingestion with entity extraction...[/cyan]")
                try:
                    from agentic_cli.kg.config import KGConfig
                    from agentic_cli.kg.ingest import ingest_data

                    ingest_result = ingest_data(
                        source=kg_result["source"]["location"],
                        format="directory",
                        extract_entities=True,
                        build_relationships=True,
                    )
                    console.print(
                        f"[green]\u2713 Full KG ingestion complete:[/green] "
                        f"{ingest_result['entities_count']} entities, "
                        f"{ingest_result['relationships_count']} relationships"
                    )
                except Exception as e:
                    console.print(f"[yellow]\u26a0 Full KG ingestion failed: {e}[/yellow]")
                    console.print(f"[dim]Context was still saved and registered. Retry with: {CLI_NAME} kg ingest submit --source "
                                  f"onboard-{project_path.name}[/dim]")

            for err in kg_result.get("errors", []):
                console.print(f"[yellow]\u26a0 {err}[/yellow]")

        except Exception as e:
            console.print(f"[yellow]\u26a0 KG context preparation failed: {e}[/yellow]")
            console.print("[dim]Onboarding completed without KG integration.[/dim]")

    # Step 9e: Record activity
    record_activity(
        command="code",
        subcommand="onboard",
        args={"repo": repo, "path": str(project_path)},
        details={
            "name": project_path.name,
            "languages": analysis.languages,
            "frameworks": analysis.frameworks,
            "skills_installed": installed_names,
            "dependencies": len(analysis.dependencies),
            "kg": kg,
            "kg_ingested": bool(kg_result and kg_result.get("ingested")),
            "domain": domain,
            "domain_context_attached": bool(domain_result),
            "domain_context_repo": domain_context_repo,
            "okf_enriched": bool(okf_result),
            "okf": okf_result,
        },
        repo_path=str(project_path),
    )

    # Step 10: Display results
    langs = ", ".join(analysis.languages) if analysis.languages else "Unknown"
    frameworks = ", ".join(analysis.frameworks) if analysis.frameworks else "—"

    console.print()
    console.print(Panel.fit(
        f"[bold green]✓ Project Onboarded[/bold green]\n\n"
        f"[bold]Project:[/bold] {project_path.name}\n"
        f"[bold]Language:[/bold] {langs}\n"
        f"[bold]Framework:[/bold] {frameworks}\n"
        f"[bold]Dependencies:[/bold] {len(analysis.dependencies)} found\n"
        f"[bold]Skills Installed:[/bold] {len(installed_names)}"
        + (f"\n[bold]KG Context:[/bold] Prepared" if kg_result and kg_result.get("context_path") else "")
        + (f"\n[bold]KG Ingested:[/bold] {kg_result.get('provider', 'unknown') if kg_result and kg_result.get('ingested') else ''}" if kg_result and kg_result.get("ingested") else "")
        + (f"\n[bold]Domain:[/bold] {domain}" if domain_result else "")
        + (f"\n[bold]Domain KG Context:[/bold] {domain_result['kg_aspects_found']}/6 aspects" if domain_result else "")
        + (f"\n[bold]Domain Context Repo:[/bold] Submodule linked" if domain_result and domain_context_repo else "")
        + (f"\n[bold]OKF Bundle:[/bold] {okf_result['written']} concept(s) -> {okf_result['bundle_dir']}" if okf_result else ""),
        border_style="green",
    ))

    # Show installed skills
    table = Table(show_header=True, header_style="bold cyan", title="Installed Skills")
    table.add_column("Skill", style="green")
    table.add_column("Reason")

    # Track matched and default skill names for lookup
    matched_names = {match.name: match.reason for match in matches}
    default_skills = {s["name"] for s in registry_data.get("skills", []) if s.get("default")}
    
    # Show all installed skills
    for skill_name in installed_names:
        if skill_name == "project-context":
            reason = "Auto-generated (project-specific)"
        elif skill_name in default_skills:
            reason = "Default skill (AI assistant)"
        elif skill_name in matched_names:
            reason = matched_names[skill_name]
        elif skill_name in domain_skills_installed:
            reason = "Domain-validated skill"
        else:
            reason = "Installed from registry"
        table.add_row(skill_name, reason)

    console.print(table)

    # Show suggestions
    if suggestions:
        console.print()
        sug_table = Table(show_header=True, header_style="bold yellow", title="Suggested Skills (not installed)")
        sug_table.add_column("Skill", style="yellow")
        sug_table.add_column("Why")
        for s in suggestions[:8]:
            sug_table.add_row(s.name, s.reason)
        console.print(sug_table)
        console.print(f"[dim]Install with: {CLI_NAME} code skills add <name> --path " + str(project_path) + "[/dim]")

    # Show agent proposals if any
    if agent_result and agent_result.get("proposals"):
        console.print()
        prop_table = Table(show_header=True, header_style="bold magenta", title="Proposed Skills (AI-detected gaps)")
        prop_table.add_column("Skill", style="magenta")
        prop_table.add_column("Description")
        prop_table.add_column("Reason", style="dim")
        for p in agent_result["proposals"]:
            prop_table.add_row(p["skill_name"], p["description"][:55], p.get("reason", "")[:50])
        console.print(prop_table)
        console.print(f"[dim]Accept + push to registry: {CLI_NAME} code skills propose --accept-all --push[/dim]")
        console.print(f"[dim]Review one:               {CLI_NAME} code skills propose --show <name>[/dim]")

    console.print()
    console.print(f"[dim]Validate with: {CLI_NAME} code validate --path " + str(project_path) + "[/dim]")
    if not kg:
        console.print(f"[dim]Prepare KG context: {CLI_NAME} code onboard --path " + str(project_path) + " --kg[/dim]")
    if not domain:
        console.print(f"[dim]Attach domain context: {CLI_NAME} code onboard --path " + str(project_path) + " --domain <slug> --kg[/dim]")


@code_app.command("list")
def list_projects(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Filter by project name (substring match)"),
    ] = None,
    show_missing: Annotated[
        bool,
        typer.Option("--show-missing", help="Show projects that no longer exist on disk"),
    ] = False,
) -> None:
    """
    List all onboarded projects.

    Shows a summary of every project that has been onboarded via f'{CLI_NAME} code onboard',
    including tech stack, skills installed, and last updated time.

    Examples:
        {CLI_NAME} code list
        {CLI_NAME} code list cwow
        {CLI_NAME} code list --show-missing
    """.format(CLI_NAME=CLI_NAME)
    repos = get_repos(name=name, check_exists=True)

    if not repos:
        if name:
            console.print(f"[yellow]No onboarded projects matching '{name}'.[/yellow]")
        else:
            console.print("[yellow]No onboarded projects found.[/yellow]")
        console.print(f"[dim]Onboard a project: {CLI_NAME} code onboard --path <dir>[/dim]")
        return

    # Filter repos based on show_missing flag
    if show_missing:
        repos = [r for r in repos if not r.get("exists", True)]
        if not repos:
            console.print("[green]✓ All onboarded projects exist on disk.[/green]")
            return
        console.print(f"[yellow]Found {len(repos)} projects that no longer exist on disk:[/yellow]\n")
    else:
        # Show all, but mark missing ones
        missing_count = sum(1 for r in repos if not r.get("exists", True))
        if missing_count > 0:
            console.print(f"[yellow]⚠ {missing_count} project(s) missing from disk. Use --show-missing to view them or 'dva code cleanup' to remove them.[/yellow]\n")

    table = Table(
        show_header=True,
        header_style="bold cyan",
        title=f"Onboarded Projects ({len(repos)})",
    )
    table.add_column("Status", justify="center", width=8)
    table.add_column("Project", style="green")
    table.add_column("Language")
    table.add_column("Framework")
    table.add_column("Database")
    table.add_column("Docker", justify="center")
    table.add_column("Skills", justify="right")
    table.add_column("Deps", justify="right", style="dim")
    table.add_column("Path", style="dim")

    for repo in repos:
        exists = repo.get("exists", True)
        status = "✓" if exists else "[red]✗[/red]"
        project_name = repo["name"]
        if not exists:
            project_name = f"[dim]{project_name}[/dim]"

        langs = ", ".join(repo.get("languages") or []) or "—"
        fws = ", ".join(repo.get("frameworks") or []) or "—"
        dbs = ", ".join(repo.get("databases") or []) or "—"
        docker = "✓" if repo.get("has_docker") else "—"
        skills = repo.get("skills_installed") or []
        skills_count = str(len(skills))
        deps = str(repo.get("dependencies", 0))

        table.add_row(
            status,
            project_name,
            langs,
            fws,
            dbs,
            docker,
            skills_count,
            deps,
            repo["path"],
        )

    console.print(table)


@code_app.command("skills")
def skills_cmd(
    action: Annotated[
        str,
        typer.Argument(help="Action: list, available, add, remove, update, propose"),
    ] = "list",
    name: Annotated[
        Optional[str],
        typer.Argument(help="Skill name (for add/remove)"),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project directory"),
    ] = Path("."),
    tag: Annotated[
        Optional[str],
        typer.Option("--tag", help="Filter available skills by tag"),
    ] = None,
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", help="Override skills registry path"),
    ] = None,
    accept_all: Annotated[
        bool,
        typer.Option("--accept-all", help="Accept all pending proposals (for propose action)"),
    ] = False,
    show_content: Annotated[
        Optional[str],
        typer.Option("--show", help="Show full SKILL.md content for a proposal"),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", help="Filter proposals by project name"),
    ] = None,
    push: Annotated[
        bool,
        typer.Option("--push/--no-push", help="Push accepted skills to the registry git repo (for propose action)"),
    ] = False,
) -> None:
    """
    Manage skills for an onboarded project.

    Examples:
        {CLI_NAME} code skills list --path ./my-repo
        {CLI_NAME} code skills available
        {CLI_NAME} code skills available --tag database
        {CLI_NAME} code skills add jira --path ./my-repo
        {CLI_NAME} code skills remove testing-junit --path ./my-repo
        {CLI_NAME} code skills update --path ./my-repo
        {CLI_NAME} code skills propose
        {CLI_NAME} code skills propose --show spring-cloud-gcp
        {CLI_NAME} code skills propose --accept-all
        {CLI_NAME} code skills propose --accept-all --push  (accept + push to {CLI_NAME}-skills repo)
        {CLI_NAME} code skills propose spring-cloud-gcp --push  (accept one + push)
    """.format(CLI_NAME=CLI_NAME)
    path = path.resolve()

    if action == "list":
        _skills_list(path)
    elif action == "available":
        _skills_available(registry, tag)
    elif action == "add":
        if not name:
            console.print(f"[red]✗ Specify skill name: {CLI_NAME} code skills add <name>[/red]")
            raise typer.Exit(1)
        _skills_add(name, path, registry)
    elif action == "remove":
        if not name:
            console.print(f"[red]✗ Specify skill name: {CLI_NAME} code skills remove <name>[/red]")
            raise typer.Exit(1)
        _skills_remove(name, path)
    elif action == "update":
        _skills_update(path, registry)
    elif action == "propose":
        _skills_propose(name, registry, accept_all, show_content, project, push)
    else:
        console.print(f"[red]✗ Unknown action '{action}'. Use: list, available, add, remove, update, propose[/red]")
        raise typer.Exit(1)


def _skills_propose(
    name: Optional[str],
    registry_override: Optional[str],
    accept_all: bool,
    show_content: Optional[str],
    project_filter: Optional[str],
    push: bool = False,
) -> None:
    """Review, accept, or reject AI-generated skill proposals."""
    proposals = load_proposals(project_name=project_filter)

    if not proposals:
        console.print("[dim]No pending skill proposals.[/dim]")
        console.print(f"[dim]Generate proposals: {CLI_NAME} code onboard --path <repo> --agent[/dim]")
        return

    # Show full content for a specific proposal
    if show_content:
        matches = [p for p in proposals if p.skill_name == show_content]
        if not matches:
            console.print(f"[red]\u2717 Proposal '{show_content}' not found.[/red]")
            return
        p = matches[0]
        console.print(Panel.fit(
            f"[bold cyan]Proposal: {p.skill_name}[/bold cyan]\n\n"
            f"[bold]Description:[/bold] {p.description}\n"
            f"[bold]Tags:[/bold] {', '.join(p.tags)}\n"
            f"[bold]Reason:[/bold] {p.reason}\n"
            f"[bold]Project:[/bold] {p.project}\n"
            f"[bold]Auto-detect:[/bold] {json.dumps(p.auto_detect, indent=2)}\n\n"
            f"[bold]--- SKILL.md Preview ---[/bold]\n\n{p.content[:2000]}",
            border_style="magenta",
        ))
        return

    # Accept a single proposal by name
    if name and not accept_all:
        matches = [p for p in proposals if p.skill_name == name]
        if not matches:
            console.print(f"[red]\u2717 Proposal '{name}' not found.[/red]")
            return
        registry_path = _ensure_registry(registry_override)
        p = matches[0]
        if accept_proposal(p, registry_path):
            remove_proposal(p.project, p.skill_name)
            console.print(f"[green]\u2713 Accepted '{p.skill_name}' \u2014 added to registry + skills/{p.skill_name}/SKILL.md[/green]")
            if push:
                _push_registry(registry_path, [p.skill_name], p.project)
            else:
                console.print(f"[dim]Push to registry repo: {CLI_NAME} code skills propose {p.skill_name} --push[/dim]")
        else:
            console.print(f"[yellow]\u26a0 Could not accept '{p.skill_name}' (duplicate or registry error)[/yellow]")
        return

    # Accept all proposals
    if accept_all:
        registry_path = _ensure_registry(registry_override)
        accepted = 0
        accepted_names = []
        failed = 0
        source_project = None
        for p in proposals:
            if accept_proposal(p, registry_path):
                remove_proposal(p.project, p.skill_name)
                console.print(f"  [green]\u2713[/green] {p.skill_name}")
                accepted += 1
                accepted_names.append(p.skill_name)
                source_project = source_project or p.project
            else:
                console.print(f"  [yellow]\u26a0[/yellow] {p.skill_name} (skipped \u2014 duplicate or error)")
                failed += 1
        console.print(f"\n[green]\u2713 Accepted {accepted} proposals[/green]" + (f" [dim]({failed} skipped)[/dim]" if failed else ""))
        if accepted_names:
            if push:
                _push_registry(registry_path, accepted_names, source_project or "unknown")
            else:
                console.print(f"[dim]Push to registry repo: {CLI_NAME} code skills propose --accept-all --push[/dim]")
        return

    # Default: list all proposals
    table = Table(show_header=True, header_style="bold magenta", title=f"Pending Skill Proposals ({len(proposals)})")
    table.add_column("Skill", style="magenta")
    table.add_column("Description")
    table.add_column("Tags", style="dim")
    table.add_column("Project", style="cyan")
    table.add_column("Reason", style="dim")

    for p in proposals:
        table.add_row(
            p.skill_name,
            p.description[:50] + ("..." if len(p.description) > 50 else ""),
            ", ".join(p.tags[:3]),
            p.project,
            p.reason[:40] + ("..." if len(p.reason) > 40 else ""),
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Accept one:  {CLI_NAME} code skills propose <skill-name>[/dim]")
    console.print(f"[dim]Accept all:  {CLI_NAME} code skills propose --accept-all[/dim]")
    console.print(f"[dim]Accept+push: {CLI_NAME} code skills propose --accept-all --push[/dim]")
    console.print(f"[dim]Preview:     {CLI_NAME} code skills propose --show <skill-name>[/dim]")


def _push_registry(registry_path: Path, skill_names: list[str], source_project: str) -> None:
    """Commit and push accepted skills to the registry git repo.

    This enables a feedback loop: agent-discovered skills get pushed
    back to agent-cli-skills so future onboarding picks them up automatically.
    """
    # Check if registry is a git repo
    git_dir = registry_path / ".git"
    if not git_dir.exists():
        console.print("[yellow]⚠ Registry is not a git repo — skipping push.[/yellow]")
        console.print(f"[dim]Skills were added locally at {registry_path}[/dim]")
        return

    skills_str = ", ".join(skill_names)
    commit_msg = f"feat: add {len(skill_names)} agent-discovered skills from {source_project}\n\nSkills: {skills_str}"

    try:
        # Stage registry.json + new skill dirs
        files_to_add = ["registry.json"]
        for sn in skill_names:
            skill_dir = registry_path / "skills" / sn
            if skill_dir.exists():
                files_to_add.append(f"skills/{sn}")

        subprocess.run(
            ["git", "add"] + files_to_add,
            cwd=str(registry_path), capture_output=True, check=True,
        )

        # Check if there are staged changes
        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(registry_path), capture_output=True,
        )
        if status.returncode == 0:
            console.print("[dim]No changes to commit (skills may already be in the repo).[/dim]")
            return

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(registry_path), capture_output=True, check=True,
        )
        console.print(f"[green]✓ Committed {len(skill_names)} skills to registry[/green]")

        # Push
        result = subprocess.run(
            ["git", "push"],
            cwd=str(registry_path), capture_output=True, text=True,
        )
        if result.returncode == 0:
            console.print(f"[green]✓ Pushed to remote — skills available for all future onboarding[/green]")
        else:
            console.print(f"[yellow]⚠ Commit saved locally but push failed:[/yellow]")
            console.print(f"[dim]{result.stderr.strip()[:200]}[/dim]")
            console.print(f"[dim]Push manually: cd {registry_path} && git push[/dim]")

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        console.print(f"[yellow]⚠ Git operation failed: {stderr[:200]}[/yellow]")
        console.print(f"[dim]Skills were added locally. Push manually: cd {registry_path} && git add -A && git push[/dim]")


def _skills_list(project_path: Path) -> None:
    """List installed skills in a project."""
    # Try to read code_assist_tool from manifest
    manifest_path = project_path / ".skills" / "onboard.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            code_assist_tool = manifest.get("code_assist_tool", "generic")
        except:
            code_assist_tool = "generic"
    else:
        # Check windsurf location
        windsurf_manifest = project_path / ".windsurf" / "workflows" / "onboard.json"
        if windsurf_manifest.exists():
            code_assist_tool = "windsurf"
        else:
            code_assist_tool = "generic"
    
    skills_dir = _get_skills_dir(project_path, code_assist_tool)
    if not skills_dir.exists():
        console.print(f"[yellow]No skills installed. Run: {CLI_NAME} code onboard --path " + str(project_path) + "[/yellow]")
        return

    skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill_md = skill_dir / "SKILL.md"
            desc = _parse_skill_description(skill_md)
            size = sum(f.stat().st_size for f in skill_dir.rglob("*") if f.is_file())
            skills.append((skill_dir.name, desc, size))

    if not skills:
        console.print("[yellow]No skills found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", title=f"Installed Skills — {project_path.name}")
    table.add_column("Skill", style="cyan")
    table.add_column("Description")
    table.add_column("Size", justify="right", style="dim")

    for name, desc, size in skills:
        desc_short = desc[:65] + "..." if len(desc) > 65 else desc
        table.add_row(name, desc_short, f"{size / 1024:.1f} KB")

    console.print(table)


def _skills_available(registry_override: Optional[str], tag: Optional[str]) -> None:
    """Show all available skills from the registry."""
    registry_path = _ensure_registry(registry_override)
    registry_data = load_registry(registry_path)

    skills = registry_data.get("skills", [])
    if tag:
        skills = [s for s in skills if tag.lower() in [t.lower() for t in s.get("tags", [])]]

    if not skills:
        console.print(f"[yellow]No skills found{' with tag ' + tag if tag else ''}.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Available Skills" + (f" (tag: {tag})" if tag else ""))
    table.add_column("Skill", style="cyan")
    table.add_column("Description")
    table.add_column("Tags", style="dim")
    table.add_column("MCP", style="yellow")

    for skill in skills:
        desc = skill.get("description", "")
        desc_short = desc[:55] + "..." if len(desc) > 55 else desc
        tags_str = ", ".join(skill.get("tags", [])[:4])
        mcp = skill.get("mcp", {}).get("server", "") if skill.get("mcp") else ""
        table.add_row(skill["name"], desc_short, tags_str, mcp)

    console.print(table)


def _skills_add(name: str, project_path: Path, registry_override: Optional[str]) -> None:
    """Add a skill to the project."""
    registry_path = _ensure_registry(registry_override)

    # Try to read code_assist_tool from manifest
    manifest_path = project_path / ".skills" / "onboard.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            code_assist_tool = manifest.get("code_assist_tool", "generic")
        except:
            code_assist_tool = "generic"
    else:
        code_assist_tool = "generic"

    if _install_skill_from_registry(name, registry_path, project_path, code_assist_tool):
        # Update manifest if exists
        _update_manifest_installed(project_path, name)
        skills_dir = _get_skills_dir(project_path, code_assist_tool)
        console.print(f"[green]✓ Skill '{name}' installed to {skills_dir / name}[/green]")
    else:
        console.print(f"[red]✗ Skill '{name}' not found in registry[/red]")
        console.print(f"[dim]Run '{CLI_NAME} code skills available' to see options[/dim]")
        raise typer.Exit(1)


def _skills_remove(name: str, project_path: Path) -> None:
    """Remove a skill from the project."""
    # Try to read code_assist_tool from manifest
    manifest_path = project_path / ".skills" / "onboard.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            code_assist_tool = manifest.get("code_assist_tool", "generic")
        except:
            code_assist_tool = "generic"
    else:
        code_assist_tool = "generic"

    skills_dir = _get_skills_dir(project_path, code_assist_tool)
    skill_dir = skills_dir / name
    if not skill_dir.exists():
        console.print(f"[red]✗ Skill '{name}' is not installed[/red]")
        raise typer.Exit(1)

    shutil.rmtree(skill_dir)
    _update_manifest_removed(project_path, name)
    console.print(f"[green]✓ Skill '{name}' removed[/green]")


def _skills_update(project_path: Path, registry_override: Optional[str]) -> None:
    """Update all installed skills from the latest registry."""
    registry_path = _ensure_registry(registry_override)

    # Try to read code_assist_tool from manifest
    manifest_path = project_path / ".skills" / "onboard.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            code_assist_tool = manifest.get("code_assist_tool", "generic")
        except:
            code_assist_tool = "generic"
    else:
        code_assist_tool = "generic"

    skills_dir = _get_skills_dir(project_path, code_assist_tool)

    if not skills_dir.exists():
        console.print("[yellow]No skills installed.[/yellow]")
        return

    updated = 0
    skipped = 0
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in ("project-context",) or not (skill_dir / "SKILL.md").exists():
            continue

        source = registry_path / "skills" / skill_dir.name
        if source.exists() and (source / "SKILL.md").exists():
            shutil.rmtree(skill_dir)
            shutil.copytree(source, skill_dir)
            updated += 1
        else:
            skipped += 1

    console.print(f"[green]✓ Updated {updated} skills[/green]" + (f" [dim]({skipped} not in registry)[/dim]" if skipped else ""))


def _update_manifest_installed(project_path: Path, name: str) -> None:
    """Add a skill to the onboard manifest."""
    # Try to find manifest in either location
    manifest_path = project_path / ".skills" / "onboard.json"
    if not manifest_path.exists():
        manifest_path = project_path / ".windsurf" / "workflows" / "onboard.json"
    
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text())
            installed = data.get("installed_skills", [])
            if name not in installed:
                installed.append(name)
                data["installed_skills"] = installed
            suggested = data.get("suggested_skills", [])
            if name in suggested:
                suggested.remove(name)
                data["suggested_skills"] = suggested
            manifest_path.write_text(json.dumps(data, indent=2))
        except (json.JSONDecodeError, OSError):
            pass


def _update_manifest_removed(project_path: Path, name: str) -> None:
    """Remove a skill from the onboard manifest."""
    # Try to find manifest in either location
    manifest_path = project_path / ".skills" / "onboard.json"
    if not manifest_path.exists():
        manifest_path = project_path / ".windsurf" / "workflows" / "onboard.json"
    
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text())
            installed = data.get("installed_skills", [])
            if name in installed:
                installed.remove(name)
                data["installed_skills"] = installed
            manifest_path.write_text(json.dumps(data, indent=2))
        except (json.JSONDecodeError, OSError):
            pass


@code_app.command("validate")
def validate(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project directory to validate"),
    ] = Path("."),
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", help="Override skills registry path"),
    ] = None,
) -> None:
    """
    Validate onboarding and show a summary report.

    Examples:
        {CLI_NAME} code validate --path ./my-repo
    """.format(CLI_NAME=CLI_NAME)
    path = path.resolve()

    # Check if onboarded - try both locations
    manifest_path = path / ".skills" / "onboard.json"
    if not manifest_path.exists():
        manifest_path = path / ".windsurf" / "workflows" / "onboard.json"
    
    if not manifest_path.exists():
        console.print("[yellow]Project not onboarded yet.[/yellow]")
        console.print(f"[dim]Run: {CLI_NAME} code onboard --path {path}[/dim]")
        raise typer.Exit(1)

    manifest = json.loads(manifest_path.read_text())
    analysis_data = manifest.get("analysis", {})
    installed = manifest.get("installed_skills", [])
    suggested = manifest.get("suggested_skills", [])
    code_assist_tool = manifest.get("code_assist_tool", "generic")

    # Re-detect MCP servers (may have changed since onboard)
    mcp_servers = detect_mcp_servers(path)

    # Build summary
    langs = ", ".join(analysis_data.get("languages", [])) or "Unknown"
    frameworks = ", ".join(analysis_data.get("frameworks", [])) or "—"
    build_tools = ", ".join(analysis_data.get("build_tools", [])) or "—"
    test_fws = ", ".join(analysis_data.get("test_frameworks", [])) or "—"
    databases = ", ".join(analysis_data.get("databases", [])) or "—"
    api_types = ", ".join(analysis_data.get("api_types", [])) or "—"
    ci_cd = ", ".join(analysis_data.get("ci_cd", [])) or "—"
    dep_count = len(analysis_data.get("dependencies", []))
    docker = "Yes" if analysis_data.get("has_docker") else "No"

    # Count skill sizes
    skills_dir = _get_skills_dir(path, code_assist_tool)
    skill_details = []
    for skill_name in installed:
        sd = skills_dir / skill_name
        if sd.exists():
            size = sum(f.stat().st_size for f in sd.rglob("*") if f.is_file())
            skill_details.append((skill_name, size))

    # Build panel
    summary_lines = [
        f"[bold green]✓ Onboarding Summary[/bold green]\n",
        f"[bold]Project:[/bold] {manifest.get('project', path.name)}",
        f"[bold]Language:[/bold] {langs}",
        f"[bold]Framework:[/bold] {frameworks}",
        f"[bold]Build:[/bold] {build_tools}",
        f"[bold]Test:[/bold] {test_fws}",
        f"[bold]Database:[/bold] {databases}",
        f"[bold]API:[/bold] {api_types}",
        f"[bold]CI/CD:[/bold] {ci_cd}",
        f"[bold]Docker:[/bold] {docker}",
        f"[bold]Dependencies:[/bold] {dep_count}",
        f"[bold]MCP Servers:[/bold] {', '.join(mcp_servers) if mcp_servers else '—'}",
        "",
        f"[bold]Skills Installed ({len(skill_details)}):[/bold]",
    ]
    for name, size in skill_details:
        summary_lines.append(f"  [green]✓[/green] {name} [dim]({size / 1024:.1f} KB)[/dim]")

    if suggested:
        summary_lines.append("")
        summary_lines.append(f"[bold]Suggested Skills ({len(suggested)}):[/bold]")
        for s in suggested[:6]:
            summary_lines.append(f"  [yellow]○[/yellow] {s}")

    # Check readiness
    readiness = len(skill_details) >= 2  # project-context + at least one tech skill
    summary_lines.append("")
    if readiness:
        summary_lines.append("[bold green]Readiness: ✓ Ready for AI-assisted development[/bold green]")
    else:
        summary_lines.append("[bold yellow]Readiness: ⚠ Consider adding more skills[/bold yellow]")

    console.print(Panel.fit("\n".join(summary_lines), border_style="cyan"))


@code_app.command("config")
def config_cmd(
    registry: Annotated[
        Optional[str],
        typer.Option("--registry", help="Set default skills registry (local path or git URL)"),
    ] = None,
    show: Annotated[
        bool,
        typer.Option("--show", help="Show current config"),
    ] = False,
) -> None:
    """
    Configure {CLI_NAME} code settings.

    Examples:
        {CLI_NAME} code config --registry /path/to/{CLI_NAME}-skills
        {CLI_NAME} code config --registry https://bitbucket.example.com/scm/DVA/{CLI_NAME}-skills.git
        {CLI_NAME} code config --show
    """.format(CLI_NAME=CLI_NAME)
    config = _get_config()

    if registry:
        reg_path = Path(registry)
        if reg_path.exists():
            config["skills_registry"] = str(reg_path.resolve())
            console.print(f"[green]✓ Registry set to local path: {reg_path.resolve()}[/green]")
        elif registry.startswith("http") or registry.startswith("git@"):
            config["skills_registry_url"] = registry
            console.print(f"[green]✓ Registry URL set: {registry}[/green]")
            console.print("[dim]Registry will be cloned on first use.[/dim]")
        else:
            console.print(f"[red]✗ Path does not exist and doesn't look like a URL: {registry}[/red]")
            raise typer.Exit(1)
        _save_config(config)
        return

    if show or not registry:
        if not config:
            console.print("[dim]No configuration set.[/dim]")
            console.print(f"[dim]Set workspace: {CLI_NAME} code init <folder>[/dim]")
            console.print(f"[dim]Set registry:  {CLI_NAME} code config --registry <path-or-url>[/dim]")
            return

        display = {
            "code_workspace": config.get("code_workspace", "(not set — using CWD)"),
            **{k: v for k, v in config.items() if k != "code_workspace"},
        }
        console.print(Panel.fit(
            f"[bold cyan]{CLI_NAME.upper()} Code Config[/bold cyan]\n\n" +
            "\n".join(f"[bold]{k}:[/bold] {v}" for k, v in display.items()),
            border_style="cyan",
        ))


@code_app.command("cleanup")
def cleanup_stale_repos(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be removed without actually removing"),
    ] = False,
) -> None:
    """
    Remove stale project entries that no longer exist on disk.

    This command checks all onboarded projects in the tracker database and removes
    entries for projects that have been deleted from disk.

    Examples:
        {CLI_NAME} code cleanup
        {CLI_NAME} code cleanup --dry-run
    """.format(CLI_NAME=CLI_NAME)
    console.print("[cyan]Checking for stale project entries...[/cyan]")

    repos = get_repos(check_exists=True)
    stale_repos = [r for r in repos if not r.get("exists", True)]

    if not stale_repos:
        console.print("[green]✓ No stale entries found. All projects exist on disk.[/green]")
        return

    console.print(f"[yellow]Found {len(stale_repos)} stale project(s):[/yellow]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Project", style="green")
    table.add_column("Path", style="dim")
    table.add_column("Onboarded", style="dim")

    for repo in stale_repos:
        table.add_row(
            repo["name"],
            repo["path"],
            repo["onboarded_at"][:10] if repo.get("onboarded_at") else "—",
        )

    console.print(table)

    if dry_run:
        console.print("\n[dim]Dry run mode - no changes made.[/dim]")
        return

    # Confirm removal
    from rich.prompt import Confirm
    if not Confirm.ask(f"Remove {len(stale_repos)} stale project(s) from tracker?", default=False):
        console.print("[dim]Cleanup cancelled.[/dim]")
        return

    # Remove stale repos
    removed_count = 0
    for repo in stale_repos:
        if remove_repo(repo["path"]):
            console.print(f"  [dim]Removed: {repo['name']}[/dim]")
            removed_count += 1

    console.print(f"\n[green]✓ Removed {removed_count} stale project(s) from tracker[/green]")
    record_activity(
        command="code", subcommand="cleanup",
        args={"dry_run": dry_run, "removed": removed_count},
    )


@code_app.command("remove")
def remove_repo_cmd(
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Project name to remove from tracker (substring match)"),
    ] = None,
    path: Annotated[
        Optional[Path],
        typer.Option("--path", "-p", help="Project path to remove from tracker"),
    ] = None,
    all: Annotated[
        bool,
        typer.Option("--all", help="Remove all onboarded projects from tracker"),
    ] = False,
    keep_code: Annotated[
        bool,
        typer.Option("--keep-code", help="Keep local code files, only remove tracker entry"),
    ] = False,
) -> None:
    """
    Remove project(s) from tracker and delete local code.

    By default, this removes both the tracker entry and the local project files.
    Use --keep-code to preserve the local files and only remove the tracker entry.

    Examples:
        {CLI_NAME} code remove --name cwow-facility
        {CLI_NAME} code remove --path ./my-repo
        {CLI_NAME} code remove --all
        {CLI_NAME} code remove --name cwow-facility --keep-code
    """.format(CLI_NAME=CLI_NAME)
    if all:
        repos = get_repos()
        if not repos:
            console.print("[yellow]No onboarded projects found.[/yellow]")
            return

        action = "remove from tracker" if keep_code else "remove from tracker and delete"
        console.print(f"[yellow]This will {action} {len(repos)} project(s):[/yellow]\n")
        for repo in repos:
            console.print(f"  [dim]- {repo['name']} ({repo['path']})[/dim]")

        from rich.prompt import Confirm
        if not Confirm.ask(f"{action.capitalize()} all projects?", default=False):
            console.print("[dim]Removal cancelled.[/dim]")
            return

        removed_count = 0
        for repo in repos:
            if remove_repo(repo["path"]):
                if not keep_code:
                    repo_path = Path(repo["path"])
                    if repo_path.exists():
                        shutil.rmtree(repo_path)
                        console.print(f"  [dim]Deleted: {repo['name']}[/dim]")
                else:
                    console.print(f"  [dim]Removed from tracker: {repo['name']}[/dim]")
                removed_count += 1

        console.print(f"\n[green]✓ Removed {removed_count} project(s)[/green]")
        record_activity(
            command="code", subcommand="remove",
            args={"all": True, "keep_code": keep_code, "removed": removed_count},
        )
        return

    # Remove by name or path
    if not name and not path:
        console.print("[yellow]Please specify --name or --path[/yellow]")
        return

    repos = get_repos()
    repo = None

    if name:
        # Search by name (substring match)
        matches = [r for r in repos if name.lower() in r["name"].lower()]
        if len(matches) == 0:
            console.print(f"[yellow]No projects found matching '{name}'[/yellow]")
            return
        elif len(matches) > 1:
            console.print(f"[yellow]Multiple projects match '{name}':[/yellow]")
            for m in matches:
                console.print(f"  [dim]- {m['name']} ({m['path']})[/dim]")
            console.print("[dim]Use --path to specify exact project.[/dim]")
            return
        repo = matches[0]
    elif path:
        # Search by exact path
        path = path.resolve()
        repo = next((r for r in repos if r["path"] == str(path)), None)
        if not repo:
            console.print(f"[yellow]Project not found in tracker: {path}[/yellow]")
            return

    action = "remove from tracker" if keep_code else "remove from tracker and delete"
    console.print(f"[yellow]This will {action}:[/yellow]")
    console.print(f"  [dim]Name: {repo['name']}[/dim]")
    console.print(f"  [dim]Path: {repo['path']}[/dim]")

    from rich.prompt import Confirm
    if not Confirm.ask(f"{action.capitalize()}?", default=False):
        console.print("[dim]Removal cancelled.[/dim]")
        return

    if remove_repo(repo["path"]):
        if not keep_code:
            repo_path = Path(repo["path"])
            if repo_path.exists():
                shutil.rmtree(repo_path)
                console.print(f"\n[green]✓ Removed {repo['name']} from tracker and deleted local code[/green]")
            else:
                console.print(f"\n[green]✓ Removed {repo['name']} from tracker (local code already deleted)[/green]")
        else:
            console.print(f"\n[green]✓ Removed {repo['name']} from tracker (kept local code)[/green]")
        record_activity(
            command="code", subcommand="remove",
            args={"name": name, "path": repo["path"], "keep_code": keep_code, "removed": 1},
        )
    else:
        console.print("[red]✗ Failed to remove project from tracker[/red]")


def _parse_skill_description(skill_md: Path) -> str:
    """Parse the description from a SKILL.md frontmatter."""
    try:
        content = skill_md.read_text()
        if not content.startswith("---"):
            return "No description"
        end = content.index("---", 3)
        frontmatter = content[3:end]
        for line in frontmatter.split("\n"):
            line = line.strip()
            if line.startswith("description:"):
                desc = line[len("description:"):].strip()
                if desc.startswith(">-") or desc.startswith(">"):
                    lines = frontmatter.split("\n")
                    desc_lines = []
                    capture = False
                    for fl in lines:
                        if fl.strip().startswith("description:"):
                            capture = True
                            continue
                        if capture:
                            stripped = fl.strip()
                            if stripped and not stripped.endswith(":") and not stripped.startswith("---"):
                                desc_lines.append(stripped)
                            else:
                                break
                    return " ".join(desc_lines) if desc_lines else "No description"
                return desc
    except (ValueError, OSError):
        pass
    return "No description"
