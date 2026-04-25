"""Skill management commands for creating, listing, and installing Agent Skills."""

import json
import os
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

from agentic_cli.tracker import record_activity

console = Console()
skill_app = typer.Typer(help="Create, list, and install Agent Skills (agentskills.io format)", rich_markup_mode=None)


SKILL_TEMPLATE = '''---
name: {name}
description: >-
  {description}
---

# {title}

## Instructions

Add your skill instructions here. The agent will follow these when the skill is activated.

## Available Tools

List the MCP tools or capabilities this skill uses.

## Workflow

1. Step one
2. Step two
3. Step three
'''


@skill_app.command("create")
def create_skill(
    name: Annotated[
        str,
        typer.Argument(help="Skill name (e.g., pr-reviewer, code-analyzer)"),
    ],
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project directory to create skill in"),
    ] = Path("."),
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Short description of the skill"),
    ] = "A custom agent skill",
    template: Annotated[
        Optional[str],
        typer.Option("--template", "-t", help="Use a built-in template: pr-reviewer"),
    ] = None,
    jira: Annotated[
        bool,
        typer.Option("--jira/--no-jira", help="Include Jira MCP integration (pr-reviewer template)"),
    ] = False,
) -> None:
    """
    Create a new Agent Skill in the project.

    Agent Skills (agentskills.io) are a portable, open format for giving AI agents
    new capabilities. Skills work across Claude Code, OpenCode, VS Code, and more.

    Examples:
        dva skill create pr-reviewer --template pr-reviewer
        dva skill create code-analyzer --description "Analyze code quality"
        dva skill create pr-reviewer --template pr-reviewer --jira
    """
    path = path.resolve()

    if template == "pr-reviewer":
        _create_pr_reviewer_skill(path, jira)
        return

    # Generic skill creation
    skill_dir = path / ".skills" / name
    if skill_dir.exists():
        console.print(f"[red]✗ Skill '{name}' already exists at {skill_dir}[/red]")
        raise typer.Exit(1)

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "scripts").mkdir(exist_ok=True)
    (skill_dir / "reference").mkdir(exist_ok=True)

    title = name.replace("-", " ").replace("_", " ").title()
    content = SKILL_TEMPLATE.format(name=name, description=description, title=title)
    (skill_dir / "SKILL.md").write_text(content)

    record_activity(
        command="skill", subcommand="create",
        args={"name": name, "path": str(path)},
        repo_path=str(path),
    )

    console.print(Panel.fit(
        f"[bold green]✓ Skill Created[/bold green]\n\n"
        f"[bold]Name:[/bold] {name}\n"
        f"[bold]Location:[/bold] {skill_dir}\n"
        f"[bold]Format:[/bold] Agent Skills (agentskills.io)\n\n"
        f"[dim]Files:[/dim]\n"
        f"  {skill_dir}/SKILL.md\n"
        f"  {skill_dir}/scripts/\n"
        f"  {skill_dir}/reference/\n\n"
        f"[dim]Edit SKILL.md to add your skill instructions.[/dim]",
        border_style="green",
    ))


def _create_pr_reviewer_skill(path: Path, include_jira: bool) -> None:
    """Create a PR reviewer skill using the built-in template."""
    from agentic_cli.templates.files.skill import generate_skill

    skill_file = generate_skill(path, include_jira=include_jira)

    console.print(Panel.fit(
        f"[bold green]✓ PR Reviewer Skill Created[/bold green]\n\n"
        f"[bold]Name:[/bold] pr-reviewer\n"
        f"[bold]Location:[/bold] {skill_file.parent}\n"
        f"[bold]Jira:[/bold] {'✓ Enabled' if include_jira else '✗ Disabled'}\n"
        f"[bold]Format:[/bold] Agent Skills (agentskills.io)\n\n"
        f"[dim]This skill works in:[/dim]\n"
        f"  • Claude Code (auto-discovered from .skills/)\n"
        f"  • OpenCode (@pr-reviewer or /skill)\n"
        f"  • VS Code Copilot (skills-compatible agents)\n"
        f"  • Any agentskills.io-compatible tool",
        border_style="green",
    ))


@skill_app.command("list")
def list_skills(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project directory to list skills from"),
    ] = Path("."),
) -> None:
    """
    List all Agent Skills installed in a project.

    Searches for SKILL.md files in .skills/, skills/, and .claude/skills/ directories.
    """
    path = path.resolve()

    # Search multiple possible skill locations
    search_dirs = [
        path / ".skills",
        path / "skills",
        path / ".claude" / "skills",
    ]

    skills = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for skill_md in search_dir.rglob("SKILL.md"):
            skill_dir = skill_md.parent
            name = skill_dir.name
            description = _parse_skill_description(skill_md)
            rel_path = skill_dir.relative_to(path)
            skills.append({
                "name": name,
                "description": description,
                "path": str(rel_path),
                "full_path": str(skill_dir),
            })

    if not skills:
        console.print("[yellow]No Agent Skills found in this project.[/yellow]")
        console.print("[dim]Create one with: dva skill create <name>[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Agent Skills")
    table.add_column("Skill", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Description")

    for skill in skills:
        desc = skill["description"][:70] + "..." if len(skill["description"]) > 70 else skill["description"]
        table.add_row(skill["name"], skill["path"], desc)

    console.print(table)


@skill_app.command("install")
def install_skill(
    source: Annotated[
        str,
        typer.Argument(help="GitHub repo URL or org/repo/path (e.g., anthropics/skills/skills/mcp-builder)"),
    ],
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project directory to install into"),
    ] = Path("."),
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Override skill name (default: derived from source)"),
    ] = None,
) -> None:
    """
    Install an Agent Skill from a GitHub repository.

    Clones the skill into the project's .skills/ directory.

    Examples:
        dva skill install anthropics/skills/skills/mcp-builder
        dva skill install https://github.com/anthropics/skills --name mcp-builder
        dva skill install anthropics/skills/skills/pdf --path ./my-project
    """
    path = path.resolve()

    # Parse source
    if source.startswith("https://github.com/"):
        # Full URL
        parts = source.replace("https://github.com/", "").split("/")
        org = parts[0]
        repo = parts[1]
        subpath = "/".join(parts[2:]) if len(parts) > 2 else ""
    elif "/" in source:
        # org/repo/path format
        parts = source.split("/")
        org = parts[0]
        repo = parts[1]
        subpath = "/".join(parts[2:]) if len(parts) > 2 else ""
    else:
        console.print(f"[red]✗ Invalid source: {source}[/red]")
        console.print("[dim]Use format: org/repo/path or full GitHub URL[/dim]")
        raise typer.Exit(1)

    skill_name = name or subpath.split("/")[-1] if subpath else repo
    target_dir = path / ".skills" / skill_name

    if target_dir.exists():
        console.print(f"[yellow]Skill '{skill_name}' already exists at {target_dir}[/yellow]")
        overwrite = typer.confirm("Overwrite?", default=False)
        if not overwrite:
            raise typer.Exit(0)
        shutil.rmtree(target_dir)

    console.print(f"[dim]Installing skill '{skill_name}' from {org}/{repo}...[/dim]")

    # Clone using sparse checkout if subpath, or full clone
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        clone_url = f"https://github.com/{org}/{repo}.git"

        try:
            if subpath:
                # Sparse checkout for subdirectory
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", clone_url, "repo"],
                    cwd=tmp_path, capture_output=True, check=True,
                )
                subprocess.run(
                    ["git", "sparse-checkout", "set", subpath],
                    cwd=tmp_path / "repo", capture_output=True, check=True,
                )
                source_dir = tmp_path / "repo" / subpath
            else:
                subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, "repo"],
                    cwd=tmp_path, capture_output=True, check=True,
                )
                source_dir = tmp_path / "repo"

            if not source_dir.exists():
                console.print(f"[red]✗ Path '{subpath}' not found in {org}/{repo}[/red]")
                raise typer.Exit(1)

            # Check for SKILL.md
            skill_md = source_dir / "SKILL.md"
            if not skill_md.exists():
                console.print(f"[red]✗ No SKILL.md found at {subpath or 'repo root'}[/red]")
                raise typer.Exit(1)

            # Copy to target
            target_dir.mkdir(parents=True, exist_ok=True)
            for item in source_dir.iterdir():
                if item.name.startswith(".git"):
                    continue
                dest = target_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)

        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Git clone failed: {e.stderr.decode() if e.stderr else str(e)}[/red]")
            raise typer.Exit(1)

    record_activity(
        command="skill", subcommand="install",
        args={"source": source, "name": skill_name, "path": str(path)},
        repo_path=str(path),
    )

    description = _parse_skill_description(target_dir / "SKILL.md")
    console.print(Panel.fit(
        f"[bold green]✓ Skill Installed[/bold green]\n\n"
        f"[bold]Name:[/bold] {skill_name}\n"
        f"[bold]Source:[/bold] {org}/{repo}/{subpath}\n"
        f"[bold]Location:[/bold] {target_dir}\n"
        f"[bold]Description:[/bold] {description}",
        border_style="green",
    ))


@skill_app.command("show")
def show_skill(
    name: Annotated[
        str,
        typer.Argument(help="Skill name to show details for"),
    ],
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project directory"),
    ] = Path("."),
) -> None:
    """
    Show details of an installed Agent Skill.
    """
    path = path.resolve()

    # Search for the skill
    skill_dir = None
    for search in [path / ".skills" / name, path / "skills" / name, path / ".claude" / "skills" / name]:
        if search.exists() and (search / "SKILL.md").exists():
            skill_dir = search
            break

    if not skill_dir:
        console.print(f"[red]✗ Skill '{name}' not found[/red]")
        raise typer.Exit(1)

    skill_md = skill_dir / "SKILL.md"
    description = _parse_skill_description(skill_md)

    # Build tree
    tree = Tree(f"[bold cyan]{name}[/bold cyan] — {description}")

    for item in sorted(skill_dir.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            branch = tree.add(f"[bold]{item.name}/[/bold]")
            for sub in sorted(item.iterdir()):
                branch.add(f"{sub.name}")
        else:
            size = item.stat().st_size
            tree.add(f"{item.name} [dim]({size} bytes)[/dim]")

    console.print(tree)


def _parse_skill_description(skill_md: Path) -> str:
    """Parse the description from a SKILL.md frontmatter."""
    try:
        content = skill_md.read_text()
        if not content.startswith("---"):
            return "No description"

        # Simple YAML frontmatter parser
        end = content.index("---", 3)
        frontmatter = content[3:end]

        for line in frontmatter.split("\n"):
            line = line.strip()
            if line.startswith("description:"):
                desc = line[len("description:"):].strip()
                if desc.startswith(">-") or desc.startswith(">"):
                    # Multi-line description — grab next non-empty lines
                    lines = frontmatter.split("\n")
                    desc_lines = []
                    capture = False
                    for fl in lines:
                        if fl.strip().startswith("description:"):
                            capture = True
                            continue
                        if capture:
                            stripped = fl.strip()
                            if stripped and not stripped.endswith(":"):
                                desc_lines.append(stripped)
                            else:
                                break
                    return " ".join(desc_lines) if desc_lines else "No description"
                return desc
    except (ValueError, OSError):
        pass
    return "No description"
