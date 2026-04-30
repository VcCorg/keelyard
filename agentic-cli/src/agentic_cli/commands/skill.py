"""Skill management commands for creating, listing, and installing Agent Skills."""

import json
import os
import shutil
import subprocess
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.tree import Tree
from typing_extensions import Annotated

from agentic_cli.config import CLI_NAME
from agentic_cli.tracker import record_activity

console = Console()
skill_app = typer.Typer(help="Create, list, and install Agent Skills (agentskills.io format)")


SKILL_TEMPLATE = '''---
name: {name}
description: >-
  {description}
tags: [custom, development]
---

# {title}

## Overview

This skill provides guidance and best practices for {description}.

## Key Concepts

- Concept 1: Brief explanation
- Concept 2: Brief explanation
- Concept 3: Brief explanation

## Common Patterns

### Pattern 1
```
Code or configuration example here
```

### Pattern 2
```
Code or configuration example here
```

## Best Practices

1. **Practice 1** — Explanation of the best practice and why it matters
2. **Practice 2** — Explanation of the best practice and why it matters
3. **Practice 3** — Explanation of the best practice and why it matters

## Resources

- [Documentation](https://example.com)
- [Guide](https://example.com)

## When to Use This Skill

This skill is useful when you need to:
- Task or scenario 1
- Task or scenario 2
- Task or scenario 3

## MCP Tools

If using MCP tools:
- Tool 1: Description
- Tool 2: Description

## Prerequisites

- Prerequisite 1
- Prerequisite 2
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
        {CLI_NAME} skill create pr-reviewer --template pr-reviewer
        {CLI_NAME} skill create code-analyzer --description "Analyze code quality"
        {CLI_NAME} skill create pr-reviewer --template pr-reviewer --jira
    """.format(CLI_NAME=CLI_NAME)
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
        console.print(f"[dim]Create one with: {CLI_NAME} skill create <name>[/dim]")
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
        {CLI_NAME} skill install anthropics/skills/skills/mcp-builder
        {CLI_NAME} skill install https://github.com/anthropics/skills --name mcp-builder
        {CLI_NAME} skill install anthropics/skills/skills/pdf --path ./my-project
    """.format(CLI_NAME=CLI_NAME)
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


@skill_app.command("generate")
def generate_skill(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Directory to save the skill into (.skills/ subdirectory)"),
    ] = Path("."),
    model_name: Annotated[
        str,
        typer.Option("--model", "-m", help="Model to use for generation"),
    ] = "gemini-2.5-flash",
    register: Annotated[
        bool,
        typer.Option("--register/--no-register", help="Add skill to the DVA skills registry after saving"),
    ] = False,
) -> None:
    """
    Interactively generate an Agent Skill using AI.

    Follows Anthropic's skill-creator 5-stage methodology:
      Stage 1 (Capture Intent): Interview questions cover trigger conditions,
        input/output specs, success criteria, edge cases, and common patterns
      Stage 2 (Interview): 4-step interactive flow with type-specific questions
      Stage 3 (Draft): AI-powered SKILL.md generation with examples and workflows
      Stage 4-5 (Evaluate & Iterate): Use 'eval' framework to test and improve

    The generated SKILL.md is production-quality and compatible with Windsurf,
    VS Code, Claude Code, and OpenCode.

    Provider-agnostic: Works with any LLM (Gemini, Claude, GPT) via --model.

    After generation, test and iterate using:
      {CLI_NAME} eval dataset create <dataset>
      {CLI_NAME} eval run skill --skill <name> --dataset <dataset>

    Examples:
        {CLI_NAME} skill generate
        {CLI_NAME} skill generate --path ./my-project
        {CLI_NAME} skill generate --model claude-3-5-sonnet-20241022
        {CLI_NAME} skill generate --model gpt-4
    """.format(CLI_NAME=CLI_NAME)
    from agentic_cli.agents.skill_creator.prompts import (
        QUESTIONS_BY_TYPE,
        SKILL_CREATOR_SYSTEM,
        SKILL_CREATOR_USER,
        SKILL_REFINE_USER,
        SKILL_TYPE_LABELS,
    )

    path = path.resolve()

    console.print()
    console.print(Panel.fit(
        "[bold cyan]Agent Skill Generator[/bold cyan]\n"
        "[dim]Powered by AI · agentskills.io format[/dim]\n\n"
        "Answer a few questions and I'll generate a SKILL.md that works\n"
        "in Windsurf, VS Code, Claude Code, and OpenCode.",
        border_style="cyan",
    ))
    console.print()

    # --- Step 1: Skill type ---
    console.print("[bold]Step 1 of 4 — Skill type[/bold]")
    console.print()
    type_choices = list(SKILL_TYPE_LABELS.keys())
    for i, key in enumerate(type_choices, 1):
        console.print(f"  [cyan]{i}[/cyan]  {SKILL_TYPE_LABELS[key]}")
    console.print()

    while True:
        choice = Prompt.ask("Choose a type", default="1")
        if choice.isdigit() and 1 <= int(choice) <= len(type_choices):
            skill_type_key = type_choices[int(choice) - 1]
            break
        console.print("[red]Enter a number 1–5[/red]")

    skill_type_label = SKILL_TYPE_LABELS[skill_type_key]
    console.print(f"[dim]→ {skill_type_label}[/dim]")
    console.print()

    # --- Step 2: Identity ---
    console.print(Rule())
    console.print("[bold]Step 2 of 4 — Identity[/bold]")
    console.print()

    raw_name = Prompt.ask("Skill name (e.g., spring-boot-gcp, pr-reviewer, servicenow-mcp)")
    skill_name = raw_name.lower().replace(" ", "-").replace("_", "-")
    if raw_name != skill_name:
        console.print(f"[dim]→ Normalized to: {skill_name}[/dim]")

    one_liner = Prompt.ask("One-line description (what does this skill help with?)")
    console.print()

    # --- Step 3: Type-specific Q&A ---
    console.print(Rule())
    console.print("[bold]Step 3 of 4 — Details[/bold]")
    console.print()

    answers: dict[str, str] = {}
    for field_key, prompt_text, optional in QUESTIONS_BY_TYPE[skill_type_key]:
        value = Prompt.ask(prompt_text, default="" if optional else None)
        if value:
            answers[field_key] = value
        console.print()

    # --- Step 4: Target environments ---
    console.print(Rule())
    console.print("[bold]Step 4 of 4 — Target environments[/bold]")
    console.print("[dim]Which tools will this skill be used in?[/dim]")
    console.print()

    env_options = ["Windsurf", "VS Code", "Claude Code", "OpenCode"]
    selected_envs: list[str] = []
    for env in env_options:
        if Confirm.ask(f"  {env}", default=True):
            selected_envs.append(env)
    environments = ", ".join(selected_envs) if selected_envs else "All agentskills.io-compatible tools"
    console.print()

    # --- Build details block from answers ---
    details_lines = []
    for field_key, prompt_text, _ in QUESTIONS_BY_TYPE[skill_type_key]:
        label = prompt_text.split("?")[0].split("[")[0].strip().rstrip("(")
        value = answers.get(field_key, "")
        if value:
            details_lines.append(f"**{label.title()}:** {value}")
    details = "\n".join(details_lines) if details_lines else f"Skill for: {one_liner}"

    # --- Initialize LLM Provider (Provider-agnostic) ---
    try:
        from agentic_cli.llm.factory import get_llm_provider
        from agentic_cli.llm.base import ProviderNotConfigured, MissingProviderSDK

        provider = get_llm_provider(
            model_name=model_name,
            system_instruction=SKILL_CREATOR_SYSTEM
        )
    except MissingProviderSDK as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except ProviderNotConfigured as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ LLM initialization failed: {e}[/red]")
        raise typer.Exit(1)

    # --- Generation + refine loop ---
    user_prompt = SKILL_CREATOR_USER.format(
        skill_type=skill_type_label,
        name=skill_name,
        one_liner=one_liner,
        details=details,
        environments=environments,
    )
    current_skill: str = ""

    while True:
        console.print(Rule())
        console.print(f"[dim]Generating with {provider.get_name()}...[/dim]")
        console.print()

        try:
            import asyncio

            # Use streaming API
            output_parts: list[str] = []

            async def stream_generation():
                async for chunk in provider.generate_streaming(user_prompt):
                    console.print(chunk, end="", flush=True)
                    output_parts.append(chunk)

            asyncio.run(stream_generation())
            console.print()
            current_skill = "".join(output_parts).strip()
        except Exception as e:
            console.print(f"\n[red]✗ Generation failed: {e}[/red]")
            raise typer.Exit(1)

        # Preview as rendered Markdown
        console.print()
        console.print(Rule("[bold]Preview[/bold]"))
        console.print(Markdown(current_skill))
        console.print(Rule())
        console.print()

        action = Prompt.ask(
            "What next?",
            choices=["save", "refine", "quit"],
            default="save",
        )

        if action == "quit":
            console.print("[dim]Exiting without saving.[/dim]")
            raise typer.Exit(0)

        if action == "refine":
            feedback = Prompt.ask("What should be changed or improved?")
            console.print()
            user_prompt = SKILL_REFINE_USER.format(
                current_skill=current_skill,
                feedback=feedback,
            )
            continue

        # action == "save"
        break

    # --- Save ---
    skill_dir = path / ".skills" / skill_name
    if skill_dir.exists():
        if not Confirm.ask(f"[yellow]Skill '{skill_name}' already exists. Overwrite?[/yellow]", default=False):
            raise typer.Exit(0)
        shutil.rmtree(skill_dir)

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(current_skill + "\n")

    record_activity(
        command="skill", subcommand="generate",
        args={"name": skill_name, "type": skill_type_key, "path": str(path)},
        repo_path=str(path),
    )

    # --- P1: Register in registry.json ---
    registry_note = ""
    if register:
        reg_path = _register_skill(skill_name, skill_type_key, one_liner, answers, current_skill)
        if reg_path:
            registry_note = f"\n[dim]Registry:[/dim]  {reg_path}"

    console.print()
    console.print(Panel.fit(
        f"[bold green]✓ Skill Generated[/bold green]\n\n"
        f"[bold]Name:[/bold]    {skill_name}\n"
        f"[bold]Type:[/bold]    {skill_type_label}\n"
        f"[bold]Location:[/bold] {skill_dir / 'SKILL.md'}\n"
        f"[bold]Works in:[/bold] {environments}"
        f"{registry_note}\n\n"
        f"[dim]Next steps:[/dim]\n"
        f"  1. [bold]Test:[/bold]  {CLI_NAME} eval dataset create {skill_name}-tests\n"
        f"  2. [bold]Evaluate:[/bold]  {CLI_NAME} eval run skill --skill {skill_name} --dataset {skill_name}-tests\n"
        f"  3. [bold]Iterate:[/bold]  Refine based on evaluation metrics\n\n"
        f"[dim]Auto-discovery:[/dim]\n"
        f"  Claude Code / Windsurf auto-discover skills from .skills/\n"
        f"[dim]Install elsewhere:[/dim]\n"
        f"  {CLI_NAME} skill install {skill_dir} --path /path/to/project[/dim]",
        border_style="green",
    ))


def _register_skill(
    skill_name: str,
    skill_type_key: str,
    one_liner: str,
    answers: dict,
    skill_content: str,
) -> Optional[str]:
    """Add a generated skill to the skills registry.json. Returns registry path or None."""
    try:
        # Try to find the skills registry
        from agentic_cli.commands.code import _get_registry_path
        reg_dir = _get_registry_path()
    except Exception:
        reg_dir = None

    if not reg_dir or not (reg_dir / "registry.json").exists():
        console.print("[yellow]⚠ Registry not found — skill saved locally only.[/yellow]")
        console.print(f"[dim]Configure with: {CLI_NAME} code config --registry ./skills[/dim]")
        return None

    reg_file = reg_dir / "registry.json"
    try:
        registry = json.loads(reg_file.read_text())
    except Exception as e:
        console.print(f"[yellow]⚠ Could not read registry: {e}[/yellow]")
        return None

    # Check for duplicate
    existing_names = {s["name"] for s in registry.get("skills", [])}
    if skill_name in existing_names:
        console.print(f"[yellow]⚠ '{skill_name}' already exists in registry — skipping.[/yellow]")
        return None

    # Build auto_detect from collected answers
    auto_detect: dict = {}
    if skill_type_key == "framework":
        deps = answers.get("framework", "").lower().replace("+", ",").replace(" ", "")
        if deps:
            auto_detect["dependencies"] = [d.strip() for d in deps.split(",") if d.strip()]
    elif skill_type_key == "data":
        source = answers.get("source", "").lower()
        if source:
            auto_detect["dependencies"] = [source]

    # Build tags from type + answers
    tags = [skill_type_key]
    if skill_type_key == "mcp":
        tags.append("mcp")
        server = answers.get("server_name", "")
        if server:
            tags.append(server)
    framework_text = answers.get("framework", answers.get("service", answers.get("source", "")))
    for word in framework_text.lower().replace("+", " ").split():
        clean = word.strip(".,")
        if clean and clean not in tags:
            tags.append(clean)

    entry: dict = {
        "name": skill_name,
        "description": one_liner,
        "tags": tags,
    }
    if auto_detect:
        entry["auto_detect"] = auto_detect
    if skill_type_key == "mcp":
        server_name = answers.get("server_name", skill_name)
        entry["mcp"] = {"server": server_name}

    console.print()
    console.print("[bold]Registry entry to add:[/bold]")
    console.print(json.dumps(entry, indent=2))
    console.print()

    if not Confirm.ask(f"Add '{skill_name}' to {reg_file}?", default=True):
        return None

    try:
        registry.setdefault("skills", []).append(entry)
        reg_file.write_text(json.dumps(registry, indent=2))

        # Also copy the SKILL.md into the registry's skills/ directory
        skills_dir = reg_dir / "skills" / skill_name
        if not skills_dir.exists():
            skills_dir.mkdir(parents=True, exist_ok=True)
            skill_md_content = skill_content + "\n"
            (skills_dir / "SKILL.md").write_text(skill_md_content)
            console.print(f"[green]✓[/green] SKILL.md copied to registry: {skills_dir}")

        console.print(f"[green]✓[/green] Added to registry: {reg_file}")
        console.print(f"[dim]Future '{CLI_NAME} code onboard' runs will auto-detect and install '{skill_name}'[/dim]")
        return str(reg_file)
    except Exception as e:
        console.print(f"[yellow]⚠ Could not register skill: {e}[/yellow]")
        return None
