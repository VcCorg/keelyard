"""Evaluation commands for validating skills and measuring agent performance."""

import json
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing_extensions import Annotated

from agentic_cli.config import CLI_NAME
from agentic_cli.evaluation.validator import SkillValidator
from agentic_cli.tracker import record_activity

console = Console()
eval_app = typer.Typer(help="Evaluate agents and skills", rich_markup_mode=None)


@eval_app.command("validate-skill")
def validate_skill(
    skill_path: Annotated[
        Path,
        typer.Argument(help="Path to SKILL.md file to validate"),
    ],
    checks: Annotated[
        Optional[str],
        typer.Option(
            "--check",
            help="Specific checks to run: structure, completeness, clarity (default: all)",
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: console, json"),
    ] = "console",
) -> None:
    """
    Validate a skill file for quality, structure, and completeness.

    Performs comprehensive validation including:
    - YAML frontmatter structure and required fields
    - Markdown formatting and syntax
    - Required sections (Instructions, Available Tools, Workflow)
    - Tool reference documentation
    - Overall completeness and clarity

    Examples:
        {CLI_NAME} eval validate-skill .skills/my-skill/SKILL.md
        {CLI_NAME} eval validate-skill .skills/my-skill/SKILL.md --output json
        {CLI_NAME} eval validate-skill .skills/pr-reviewer/SKILL.md --check structure
    """.format(CLI_NAME=CLI_NAME)

    skill_path = Path(skill_path).resolve()

    if not skill_path.exists():
        console.print(f"[red]✗ Skill file not found: {skill_path}[/red]")
        raise typer.Exit(1)

    validator = SkillValidator(skill_path)
    result = validator.validate()

    record_activity(
        command="eval",
        subcommand="validate-skill",
        args={"skill_path": str(skill_path), "output_format": output_format},
        repo_path=str(skill_path.parent.parent.parent),
    )

    if output_format == "json":
        _output_validation_json(result)
    else:
        _output_validation_console(result)

    # Exit with error code if validation failed
    if not result.passed:
        raise typer.Exit(1)


def _output_validation_console(result) -> None:
    """Output validation results to console with rich formatting."""
    # Header
    status_emoji = "✅" if result.passed else "⚠️"
    status_color = "green" if result.passed else "yellow"

    header = Panel.fit(
        f"[bold {status_color}]{status_emoji} Skill Validation Results[/bold {status_color}]\n\n"
        f"[bold]Skill:[/bold] {result.skill_name}\n"
        f"[bold]Quality Score:[/bold] {result.quality_score}/100\n"
        f"[bold]Status:[/bold] {'[green]✓ PASSED[/green]' if result.passed else '[yellow]⚠ NEEDS IMPROVEMENT[/yellow]'}",
        border_style=status_color,
    )
    console.print(header)

    # Checks table
    if result.checks:
        console.print("\n[bold]Validation Checks:[/bold]\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Message")

        for check in result.checks:
            status = "✓" if check.passed else "✗"
            status_style = "green" if check.passed else "yellow" if check.severity == "warning" else "red"
            table.add_row(
                check.check_name,
                f"[{status_style}]{status}[/{status_style}]",
                check.message,
            )

        console.print(table)

    # Sections status
    if result.sections:
        console.print("\n[bold]Sections Found:[/bold]\n")
        required_section_table = Table(show_header=True, header_style="bold magenta")
        required_section_table.add_column("Section", style="cyan")
        required_section_table.add_column("Status", justify="center")

        required = {"Instructions", "Available Tools", "Workflow"}
        for section in sorted(result.sections.keys()):
            found = result.sections[section]
            status = "✓" if found else "✗"
            status_style = "green" if found else "red" if section in required else "yellow"
            required_marker = " [bold red](required)[/bold red]" if section in required else ""
            required_section_table.add_row(
                section + required_marker,
                f"[{status_style}]{status}[/{status_style}]",
            )

        console.print(required_section_table)

    # Issues
    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in result.errors:
            console.print(f"  [red]✗[/red] {error}")

    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  [yellow]⚠[/yellow] {warning}")

    # Recommendations
    if not result.passed:
        console.print("\n[bold cyan]Recommendations:[/bold cyan]")
        if result.quality_score < 50:
            console.print(f"  • Skill quality score is low ({result.quality_score}/100)")
            console.print(f"  • Review error messages above and fix critical issues")
            console.print(f"  • Ensure all required sections are present")
        elif result.quality_score < 70:
            console.print(f"  • Skill quality score is acceptable ({result.quality_score}/100)")
            console.print(f"  • Address warnings to improve score")
            console.print(f"  • Add more detailed examples and documentation")
        if result.errors:
            console.print(f"  • Fix {len(result.errors)} error(s) before publishing")
        if result.warnings:
            console.print(f"  • Address {len(result.warnings)} warning(s) for better quality")

    console.print()


def _output_validation_json(result) -> None:
    """Output validation results as JSON."""
    output = {
        "skill_name": result.skill_name,
        "skill_path": str(result.skill_path),
        "passed": result.passed,
        "quality_score": result.quality_score,
        "checks": [
            {
                "name": check.check_name,
                "passed": check.passed,
                "score": check.score,
                "message": check.message,
                "severity": check.severity,
            }
            for check in result.checks
        ],
        "sections": result.sections,
        "frontmatter": result.frontmatter,
        "errors": result.errors,
        "warnings": result.warnings,
    }
    console.print(json.dumps(output, indent=2))
