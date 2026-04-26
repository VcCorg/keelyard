"""Skill Registry commands - publish, search, and share skills via Git."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing_extensions import Annotated

from agentic_cli.config import CLI_NAME
from agentic_cli.evaluation.skill_registry import GitSkillRegistry, SkillMetadata
from agentic_cli.tracker import record_activity

console = Console()
skill_registry_app = typer.Typer(help="Publish and share skills via Git registry", rich_markup_mode=None)


@skill_registry_app.command("init")
def init_registry(
    repo_url: Annotated[
        str,
        typer.Argument(help="Git repository URL (e.g., git@github.com:company/skills.git)"),
    ],
    local_path: Annotated[
        Optional[Path],
        typer.Option("--path", "-p", help="Local path to clone registry"),
    ] = None,
) -> None:
    """Initialize skill registry from Git repository.

    Sets up a local copy of the team's skill registry for publishing and discovery.

    Examples:
        {CLI_NAME} skill-registry init git@github.com:company/skills.git
        {CLI_NAME} skill-registry init https://github.com/company/skills.git
    """.format(CLI_NAME=CLI_NAME)

    try:
        registry = GitSkillRegistry(repo_url, local_path)

        console.print("[dim]Cloning registry repository...[/dim]")
        registry.clone()

        console.print(
            Panel.fit(
                f"[bold green]✓ Registry Initialized[/bold green]\n\n"
                f"[bold]Repository:[/bold] {repo_url}\n"
                f"[bold]Local Path:[/bold] {registry.local_path}\n\n"
                f"[dim]Registry ready for publishing and discovery.[/dim]",
                border_style="green",
            )
        )

        record_activity(
            command="skill-registry",
            subcommand="init",
            args={"repo_url": repo_url},
            repo_path=str(Path.cwd()),
        )

    except Exception as e:
        console.print(f"[red]✗ Failed to initialize registry: {e}[/red]")
        raise typer.Exit(1)


@skill_registry_app.command("publish")
def publish_skill(
    skill_name: Annotated[
        str,
        typer.Argument(help="Skill name/ID to publish"),
    ],
    repo_url: Annotated[
        str,
        typer.Option("--registry", "-r", help="Registry repository URL"),
    ] = "",
    version: Annotated[
        str,
        typer.Option("--version", "-v", help="Skill version (e.g., 1.0)"),
    ] = "1.0",
    domain: Annotated[
        str,
        typer.Option("--domain", "-d", help="Domain (e.g., backend, frontend)"),
    ] = "general",
    role: Annotated[
        str,
        typer.Option("--role", help="Role (e.g., dev, qa, sm, ba)"),
    ] = "developer",
    quality_score: Annotated[
        float,
        typer.Option("--quality", "-q", help="Quality score (0-100)"),
    ] = 85.0,
    effectiveness: Annotated[
        float,
        typer.Option("--effectiveness", "-e", help="Effectiveness score (0-10)"),
    ] = 8.0,
    tags: Annotated[
        Optional[str],
        typer.Option("--tags", "-t", help="Comma-separated tags"),
    ] = None,
) -> None:
    """Publish a skill to the team registry.

    Publishes a validated and evaluated skill to the shared Git registry.
    Requires quality score and effectiveness metrics from evaluation.

    Examples:
        {CLI_NAME} skill-registry publish backend-dev-skill --registry git@github.com:company/skills.git
        {CLI_NAME} skill-registry publish qa-skill --domain qa --role qa --quality 88 --effectiveness 8.5
    """.format(CLI_NAME=CLI_NAME)

    # Find skill directory
    skill_dir = Path(".skills") / skill_name
    if not skill_dir.exists():
        console.print(f"[red]✗ Skill not found: {skill_dir}[/red]")
        raise typer.Exit(1)

    if not repo_url:
        console.print("[red]✗ Registry URL required (--registry)[/red]")
        raise typer.Exit(1)

    try:
        registry = GitSkillRegistry(repo_url)
        registry.clone()

        # Create metadata
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        metadata = SkillMetadata(
            id=skill_name,
            name=skill_name.replace("-", " ").title(),
            description=f"{skill_name} skill",
            domain=domain,
            role=role,
            tags=tag_list,
            latest_version=version,
        )

        console.print(
            Panel.fit(
                f"[bold cyan]Publishing Skill[/bold cyan]\n\n"
                f"[bold]Skill:[/bold] {skill_name}\n"
                f"[bold]Version:[/bold] {version}\n"
                f"[bold]Domain:[/bold] {domain}\n"
                f"[bold]Quality:[/bold] {quality_score}/100\n"
                f"[bold]Effectiveness:[/bold] {effectiveness}/10",
                border_style="cyan",
            )
        )

        console.print("[dim]Publishing to registry...[/dim]")
        skill_id = registry.publish_skill(
            skill_dir,
            metadata,
            quality_score=quality_score,
            effectiveness=effectiveness,
        )

        console.print(
            Panel.fit(
                f"[bold green]✓ Skill Published[/bold green]\n\n"
                f"[bold]Skill ID:[/bold] {skill_id}\n"
                f"[bold]Version:[/bold] {version}\n"
                f"[bold]Location:[/bold] {registry.local_path / domain / skill_name}\n\n"
                f"[dim]Skill is now available in the team registry.[/dim]",
                border_style="green",
            )
        )

        record_activity(
            command="skill-registry",
            subcommand="publish",
            args={
                "skill_name": skill_name,
                "version": version,
                "domain": domain,
                "quality_score": quality_score,
                "effectiveness": effectiveness,
            },
            repo_path=str(Path.cwd()),
        )

    except Exception as e:
        console.print(f"[red]✗ Publish failed: {e}[/red]")
        raise typer.Exit(1)


@skill_registry_app.command("search")
def search_skills(
    repo_url: Annotated[
        str,
        typer.Option("--registry", "-r", help="Registry repository URL"),
    ] = "",
    domain: Annotated[
        Optional[str],
        typer.Option("--domain", "-d", help="Filter by domain"),
    ] = None,
    role: Annotated[
        Optional[str],
        typer.Option("--role", help="Filter by role"),
    ] = None,
    min_effectiveness: Annotated[
        float,
        typer.Option("--min-effectiveness", "-e", help="Minimum effectiveness score"),
    ] = 0.0,
    min_quality: Annotated[
        float,
        typer.Option("--min-quality", "-q", help="Minimum quality score"),
    ] = 0.0,
    sort_by: Annotated[
        str,
        typer.Option("--sort", "-s", help="Sort by: effectiveness, quality, rating"),
    ] = "effectiveness",
) -> None:
    """Search the skill registry.

    Find and discover skills in the team registry with filtering and sorting.

    Examples:
        {CLI_NAME} skill-registry search --registry git@github.com:company/skills.git
        {CLI_NAME} skill-registry search --domain backend --min-effectiveness 8.0
        {CLI_NAME} skill-registry search --role qa --sort rating
    """.format(CLI_NAME=CLI_NAME)

    if not repo_url:
        console.print("[red]✗ Registry URL required (--registry)[/red]")
        raise typer.Exit(1)

    try:
        registry = GitSkillRegistry(repo_url)
        if not registry.local_path.exists():
            registry.clone()
        else:
            registry.pull()

        console.print("[dim]Searching registry...[/dim]\n")

        # Search
        results = registry.search(
            domain=domain,
            role=role,
            min_effectiveness=min_effectiveness,
            min_quality=min_quality,
        )

        if not results:
            console.print("[yellow]No skills found matching criteria[/yellow]")
            return

        # Display results
        table = Table(show_header=True, header_style="bold magenta", title="Available Skills")
        table.add_column("Skill ID", style="cyan")
        table.add_column("Domain", style="green")
        table.add_column("Quality", justify="right")
        table.add_column("Effectiveness", justify="right")
        table.add_column("Used By", justify="right")
        table.add_column("Rating", justify="right")

        for skill in results:
            latest = skill.latest_version
            if latest in skill.versions:
                version = skill.versions[latest]
                quality = f"{version.quality_score:.0f}/100"
                effectiveness = f"{version.effectiveness:.1f}/10"
            else:
                quality = "—"
                effectiveness = "—"

            rating = f"{skill.rating:.1f}⭐" if skill.rating > 0 else "—"
            table.add_row(
                skill.id,
                skill.domain,
                quality,
                effectiveness,
                str(skill.adopted_by),
                rating,
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(results)} skill(s)[/dim]")

        record_activity(
            command="skill-registry",
            subcommand="search",
            args={
                "domain": domain,
                "role": role,
                "min_effectiveness": min_effectiveness,
            },
            repo_path=str(Path.cwd()),
        )

    except Exception as e:
        console.print(f"[red]✗ Search failed: {e}[/red]")
        raise typer.Exit(1)


@skill_registry_app.command("show")
def show_skill(
    skill_id: Annotated[
        str,
        typer.Argument(help="Skill ID to show"),
    ],
    repo_url: Annotated[
        str,
        typer.Option("--registry", "-r", help="Registry repository URL"),
    ] = "",
) -> None:
    """Show skill details from registry.

    Display detailed information about a skill including metrics, versions, and ratings.

    Examples:
        {CLI_NAME} skill-registry show backend-dev-skill --registry git@github.com:company/skills.git
    """.format(CLI_NAME=CLI_NAME)

    if not repo_url:
        console.print("[red]✗ Registry URL required (--registry)[/red]")
        raise typer.Exit(1)

    try:
        registry = GitSkillRegistry(repo_url)
        if not registry.local_path.exists():
            registry.clone()

        index = registry.load_index()
        if skill_id not in index.skills:
            console.print(f"[red]✗ Skill not found: {skill_id}[/red]")
            raise typer.Exit(1)

        skill = index.skills[skill_id]
        latest_version = skill.latest_version

        if latest_version in skill.versions:
            version_info = skill.versions[latest_version]
            quality = f"{version_info.quality_score:.0f}/100"
            effectiveness = f"{version_info.effectiveness:.1f}/10"
        else:
            quality = "—"
            effectiveness = "—"

        console.print(
            Panel.fit(
                f"[bold cyan]{skill.name}[/bold cyan] v{latest_version}\n\n"
                f"[bold]Description:[/bold] {skill.description}\n"
                f"[bold]Domain:[/bold] {skill.domain}\n"
                f"[bold]Role:[/bold] {skill.role}\n"
                f"[bold]Author:[/bold] {skill.author}\n\n"
                f"[bold]Quality Score:[/bold] {quality} ✅\n"
                f"[bold]Effectiveness:[/bold] {effectiveness} ⭐\n"
                f"[bold]Used By:[/bold] {skill.adopted_by} agents\n"
                f"[bold]Rating:[/bold] {skill.rating:.1f}⭐\n"
                f"[bold]Downloads:[/bold] {skill.downloads}\n"
                f"[bold]Tags:[/bold] {', '.join(skill.tags) if skill.tags else '(none)'}",
                border_style="cyan",
            )
        )

        if len(skill.versions) > 1:
            console.print("\n[bold]Version History:[/bold]\n")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Version", style="cyan")
            table.add_column("Quality", justify="right")
            table.add_column("Effectiveness", justify="right")
            table.add_column("Published")

            for v_id in sorted(skill.versions.keys(), reverse=True):
                v = skill.versions[v_id]
                table.add_row(
                    v_id,
                    f"{v.quality_score:.0f}/100",
                    f"{v.effectiveness:.1f}/10",
                    v.published[:10],
                )

            console.print(table)

        record_activity(
            command="skill-registry",
            subcommand="show",
            args={"skill_id": skill_id},
            repo_path=str(Path.cwd()),
        )

    except Exception as e:
        console.print(f"[red]✗ Failed to show skill: {e}[/red]")
        raise typer.Exit(1)


@skill_registry_app.command("list")
def list_skills(
    repo_url: Annotated[
        str,
        typer.Option("--registry", "-r", help="Registry repository URL"),
    ] = "",
) -> None:
    """List all skills in registry.

    Display a summary of all available skills.

    Examples:
        {CLI_NAME} skill-registry list --registry git@github.com:company/skills.git
    """.format(CLI_NAME=CLI_NAME)

    if not repo_url:
        console.print("[red]✗ Registry URL required (--registry)[/red]")
        raise typer.Exit(1)

    try:
        registry = GitSkillRegistry(repo_url)
        if not registry.local_path.exists():
            registry.clone()

        index = registry.load_index()
        if not index.skills:
            console.print("[yellow]No skills in registry[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta", title="All Skills")
        table.add_column("Skill ID", style="cyan")
        table.add_column("Domain", style="green")
        table.add_column("Version")
        table.add_column("Effectiveness")
        table.add_column("Rating")

        for skill_id, skill in sorted(index.skills.items()):
            latest = skill.latest_version
            if latest in skill.versions:
                effectiveness = f"{skill.versions[latest].effectiveness:.1f}/10"
            else:
                effectiveness = "—"

            rating = f"{skill.rating:.1f}⭐" if skill.rating > 0 else "—"
            table.add_row(
                skill_id,
                skill.domain,
                latest,
                effectiveness,
                rating,
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(index.skills)} skill(s)[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Failed to list skills: {e}[/red]")
        raise typer.Exit(1)
