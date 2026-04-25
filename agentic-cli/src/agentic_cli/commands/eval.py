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
from agentic_cli.evaluation.datasets import DatasetManager, EvaluationDataset
from agentic_cli.evaluation.metrics import get_all_metrics, get_metric
from agentic_cli.tracker import record_activity

console = Console()
eval_app = typer.Typer(help="Evaluate agents and skills", rich_markup_mode=None)

# Default datasets directory
DATASETS_DIR = Path.home() / ".agentic-cli" / "datasets"
dataset_manager = DatasetManager(DATASETS_DIR)


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


@eval_app.command("create-dataset")
def create_dataset(
    name: Annotated[
        str,
        typer.Argument(help="Dataset name (e.g., customer-qa, bug-triage)"),
    ],
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Dataset description"),
    ] = "Evaluation dataset",
    tags: Annotated[
        Optional[str],
        typer.Option("--tags", "-t", help="Comma-separated tags (e.g., qa,production)"),
    ] = None,
) -> None:
    """
    Create a new evaluation dataset.

    Datasets are collections of input-output pairs used to evaluate agent performance.
    They can be created manually and then populated with samples.

    Examples:
        {CLI_NAME} eval create-dataset customer-qa --description "QA dataset"
        {CLI_NAME} eval create-dataset bug-triage --tags "qa,backend"
    """.format(CLI_NAME=CLI_NAME)

    dataset_id = name.lower().replace(" ", "-")
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    dataset = dataset_manager.create_dataset(
        dataset_id=dataset_id,
        name=name,
        description=description,
        tags=tag_list,
    )

    record_activity(
        command="eval",
        subcommand="create-dataset",
        args={"name": name, "description": description},
        repo_path=str(Path.cwd()),
    )

    console.print(
        Panel.fit(
            f"[bold green]✓ Dataset Created[/bold green]\n\n"
            f"[bold]Name:[/bold] {name}\n"
            f"[bold]ID:[/bold] {dataset_id}\n"
            f"[bold]Tags:[/bold] {', '.join(tag_list) if tag_list else '(none)'}\n\n"
            f"[dim]Dataset created. You can now add samples to it.[/dim]",
            border_style="green",
        )
    )


@eval_app.command("list-metrics")
def list_metrics() -> None:
    """
    List all available evaluation metrics.

    Shows built-in metrics with their descriptions, types, and thresholds.

    Examples:
        {CLI_NAME} eval list-metrics
    """.format(CLI_NAME=CLI_NAME)

    metrics = get_all_metrics()

    if not metrics:
        console.print("[yellow]No metrics available[/yellow]")
        return

    # Group by type
    quantitative = {}
    qualitative = {}
    boolean = {}

    for name, metric in metrics.items():
        if metric.metric_type.value == "qualitative":
            qualitative[name] = metric
        elif metric.metric_type.value == "boolean":
            boolean[name] = metric
        else:
            quantitative[name] = metric

    # Display quantitative metrics
    if quantitative:
        console.print("\n[bold cyan]Quantitative Metrics[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Unit", style="green")
        table.add_column("Lower Better", justify="center")
        table.add_column("Description")

        for name, metric in quantitative.items():
            lower = "✓" if metric.lower_is_better else "✗"
            table.add_row(name, metric.unit or "—", lower, metric.description[:50] + "...")
        console.print(table)

    # Display qualitative metrics
    if qualitative:
        console.print("\n[bold cyan]Qualitative Metrics (LLM-Judged, 1-5 scale)[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Threshold", style="green")
        table.add_column("Description")

        for name, metric in qualitative.items():
            threshold = f"{metric.threshold}" if metric.threshold else "—"
            table.add_row(name, threshold, metric.description[:50] + "...")
        console.print(table)

    # Display boolean metrics
    if boolean:
        console.print("\n[bold cyan]Boolean Metrics[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Description")

        for name, metric in boolean.items():
            table.add_row(name, metric.description[:50] + "...")
        console.print(table)

    console.print("\n[dim]Use metrics in: {CLI_NAME} eval measure-skill-impact --metrics <names>[/dim]".format(CLI_NAME=CLI_NAME))
