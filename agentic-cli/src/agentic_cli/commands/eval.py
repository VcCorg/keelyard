"""Evaluation commands - generalized for skills, agents, models, and comparisons."""

import asyncio
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
from agentic_cli.evaluation.runner import SkillImpactEvaluator
from agentic_cli.tracker import record_activity

console = Console()
eval_app = typer.Typer(help="Evaluate agents, skills, and performance", rich_markup_mode=None)

# Subcommand apps
dataset_app = typer.Typer(help="Manage evaluation datasets")
validate_app = typer.Typer(help="Validate agents, skills, and datasets")
run_app = typer.Typer(help="Run evaluations (agent, skill, model)")
metrics_app = typer.Typer(help="View evaluation metrics")
report_app = typer.Typer(help="View and export evaluation reports")

# Register subcommands
eval_app.add_typer(dataset_app, name="dataset")
eval_app.add_typer(validate_app, name="validate")
eval_app.add_typer(run_app, name="run")
eval_app.add_typer(metrics_app, name="metrics")
eval_app.add_typer(report_app, name="report")

# Default datasets directory
DATASETS_DIR = Path.home() / ".agentic-cli" / "datasets"
EVALS_DIR = Path.home() / ".agentic-cli" / "evaluations"

dataset_manager = DatasetManager(DATASETS_DIR)
EVALS_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# DATASET COMMANDS
# ==============================================================================

@dataset_app.command("create")
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
        typer.Option("--tags", "-t", help="Comma-separated tags"),
    ] = None,
) -> None:
    """Create a new evaluation dataset.

    Examples:
        {CLI_NAME} eval dataset create customer-qa
        {CLI_NAME} eval dataset create bug-triage --tags "qa,backend"
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
        subcommand="dataset-create",
        args={"name": name},
        repo_path=str(Path.cwd()),
    )

    console.print(
        Panel.fit(
            f"[bold green]✓ Dataset Created[/bold green]\n\n"
            f"[bold]Name:[/bold] {name}\n"
            f"[bold]ID:[/bold] {dataset_id}\n"
            f"[bold]Location:[/bold] {DATASETS_DIR / dataset_id}.json",
            border_style="green",
        )
    )


@dataset_app.command("list")
def list_datasets() -> None:
    """List all evaluation datasets.

    Examples:
        {CLI_NAME} eval dataset list
    """.format(CLI_NAME=CLI_NAME)

    datasets = dataset_manager.list_datasets()

    if not datasets:
        console.print("[yellow]No datasets found[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Evaluation Datasets")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Samples", justify="right")
    table.add_column("Tags")

    for ds in datasets:
        tags = ", ".join(ds.tags) if ds.tags else "—"
        table.add_row(ds.id, ds.name, str(len(ds.samples)), tags)

    console.print(table)


@dataset_app.command("show")
def show_dataset(
    dataset_id: Annotated[
        str,
        typer.Argument(help="Dataset ID"),
    ],
) -> None:
    """Show dataset details.

    Examples:
        {CLI_NAME} eval dataset show customer-qa
    """.format(CLI_NAME=CLI_NAME)

    dataset = dataset_manager.load_dataset(dataset_id)
    if not dataset:
        console.print(f"[red]Dataset not found: {dataset_id}[/red]")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]{dataset.name}[/bold cyan]\n\n"
            f"[bold]ID:[/bold] {dataset.id}\n"
            f"[bold]Description:[/bold] {dataset.description}\n"
            f"[bold]Samples:[/bold] {len(dataset.samples)}\n"
            f"[bold]Tags:[/bold] {', '.join(dataset.tags) if dataset.tags else '(none)'}\n"
            f"[bold]Created:[/bold] {dataset.created[:10]}",
            border_style="cyan",
        )
    )

    if dataset.samples:
        console.print("\n[bold]First 5 Samples:[/bold]\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Input", style="green", width=40)
        table.add_column("Expected Output", width=40)

        for sample in dataset.samples[:5]:
            input_text = sample.input[:37] + "..." if len(sample.input) > 40 else sample.input
            expected = sample.expected_output[:37] + "..." if len(sample.expected_output) > 40 else sample.expected_output
            table.add_row(
                sample.sample_id or "—",
                input_text,
                expected,
            )

        console.print(table)


# ==============================================================================
# VALIDATE COMMANDS
# ==============================================================================

@validate_app.command("skill")
def validate_skill(
    skill_path: Annotated[
        Path,
        typer.Argument(help="Path to SKILL.md file"),
    ],
    output_format: Annotated[
        str,
        typer.Option("--output", "-o", help="Output: console, json"),
    ] = "console",
) -> None:
    """Validate a skill file structure and quality.

    Checks:
      - YAML frontmatter (name, description)
      - Required sections (Instructions, Available Tools, Workflow)
      - Markdown formatting and syntax
      - Tool documentation
      - Completeness and clarity

    Examples:
        {CLI_NAME} eval validate skill .skills/my-skill/SKILL.md
        {CLI_NAME} eval validate skill .skills/pr-reviewer/SKILL.md --output json
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
        args={"skill_path": str(skill_path)},
        repo_path=str(skill_path.parent.parent.parent),
    )

    if output_format == "json":
        output = {
            "skill_name": result.skill_name,
            "quality_score": result.quality_score,
            "passed": result.passed,
            "checks": [
                {
                    "name": c.check_name,
                    "passed": c.passed,
                    "message": c.message,
                }
                for c in result.checks
            ],
            "errors": result.errors,
            "warnings": result.warnings,
        }
        console.print(json.dumps(output, indent=2))
    else:
        status_color = "green" if result.passed else "yellow"
        console.print(
            Panel.fit(
                f"[bold {status_color}]{'✓' if result.passed else '⚠'} Skill Validation[/bold {status_color}]\n\n"
                f"[bold]Skill:[/bold] {result.skill_name}\n"
                f"[bold]Score:[/bold] {result.quality_score}/100\n"
                f"[bold]Status:[/bold] {'[green]PASSED[/green]' if result.passed else '[yellow]NEEDS IMPROVEMENT[/yellow]'}",
                border_style=status_color,
            )
        )

        # Show checks
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Message")

        for check in result.checks:
            status = "✓" if check.passed else "✗"
            status_style = "green" if check.passed else "red" if check.severity == "error" else "yellow"
            table.add_row(
                check.check_name,
                f"[{status_style}]{status}[/{status_style}]",
                check.message[:60] + "..." if len(check.message) > 60 else check.message,
            )

        console.print("\n")
        console.print(table)

        if result.errors:
            console.print(f"\n[bold red]Errors ({len(result.errors)}):[/bold red]")
            for err in result.errors:
                console.print(f"  [red]✗[/red] {err}")

    if not result.passed:
        raise typer.Exit(1)


# ==============================================================================
# RUN COMMANDS
# ==============================================================================

@run_app.command("skill")
def run_skill_impact(
    agent_name: Annotated[
        str,
        typer.Option("--agent", help="Agent name/identifier"),
    ],
    skill_name: Annotated[
        str,
        typer.Option("--skill", help="Skill name/identifier"),
    ],
    dataset_id: Annotated[
        str,
        typer.Option("--dataset", help="Dataset ID"),
    ],
    metrics: Annotated[
        str,
        typer.Option("--metrics", "-m", help="Comma-separated metric names"),
    ] = "accuracy,helpfulness,latency_ms",
    judge: Annotated[
        str,
        typer.Option("--judge", "-j", help="Judge: vertex-ai, anthropic, openai"),
    ] = "anthropic",
    parallel: Annotated[
        int,
        typer.Option("--parallel", "-p", help="Parallel evaluation workers"),
    ] = 1,
    save_report: Annotated[
        bool,
        typer.Option("--save", help="Save results to file"),
    ] = True,
) -> None:
    """Run skill impact evaluation with Vertex AI.

    Measures how much a skill improves agent performance:
      1. Baseline: Run agent WITHOUT skill on dataset
      2. With Skill: Run agent WITH skill on dataset
      3. Evaluate: Use Vertex AI (or Claude/GPT-4) to score responses
      4. Delta: Calculate performance improvement
      5. Score: Effectiveness rating (0-10)

    **Judges:**
      - vertex-ai: Google Cloud Vertex AI (Gemini) - primary
      - anthropic: Claude API - fallback
      - openai: GPT-4 - fallback

    Examples:
        {CLI_NAME} eval run skill --agent support --skill faq --dataset qa --judge vertex-ai
        {CLI_NAME} eval run skill --agent rag --skill research --dataset docs --metrics accuracy,helpfulness
        {CLI_NAME} eval run skill --agent dev --skill pr-reviewer --dataset prs --parallel 4
    """.format(CLI_NAME=CLI_NAME)

    import asyncio
    from agentic_cli.evaluation.skill_evaluator import (
        AsyncSkillEvaluator,
        SkillEvaluationConfig,
        SkillEvaluationReporter,
    )
    from agentic_cli.evaluation.agent_adapters import MockAgents

    # Load dataset
    dataset = dataset_manager.load_dataset(dataset_id)
    if not dataset:
        console.print(f"[red]✗ Dataset not found: {dataset_id}[/red]")
        raise typer.Exit(1)

    if not dataset.samples:
        console.print(f"[red]✗ Dataset has no samples[/red]")
        raise typer.Exit(1)

    # Parse metrics
    metric_list = [m.strip() for m in metrics.split(",")]
    invalid_metrics = [m for m in metric_list if not get_metric(m)]
    if invalid_metrics:
        console.print(f"[red]✗ Unknown metrics: {', '.join(invalid_metrics)}[/red]")
        raise typer.Exit(1)

    # Show configuration
    console.print(
        Panel.fit(
            f"[bold cyan]Skill Impact Evaluation[/bold cyan]\n\n"
            f"[bold]Agent:[/bold] {agent_name}\n"
            f"[bold]Skill:[/bold] {skill_name}\n"
            f"[bold]Dataset:[/bold] {dataset_id} ({len(dataset.samples)} samples)\n"
            f"[bold]Metrics:[/bold] {', '.join(metric_list)}\n"
            f"[bold]Judge:[/bold] {judge} (Vertex AI with fallback)\n"
            f"[bold]Parallel Workers:[/bold] {parallel}",
            border_style="cyan",
        )
    )

    try:
        # Create evaluation config
        config = SkillEvaluationConfig(
            agent_name=agent_name,
            skill_name=skill_name,
            dataset_id=dataset_id,
            metrics=metric_list,
            judge_type=judge,
            parallel_workers=parallel,
        )

        # Create async evaluator
        evaluator = AsyncSkillEvaluator(
            agent_name=agent_name,
            skill_name=skill_name,
            dataset=dataset,
            metrics=metric_list,
            judge_type=judge,
            max_workers=parallel,
        )

        # Mock agent functions for demo
        # In production, these would be actual agent implementations
        agent_fn = MockAgents.get_agent("helpful")
        baseline_fn = MockAgents.get_agent("simple")

        # Progress callback
        def on_progress(msg: str) -> None:
            console.print(f"[dim]→[/dim] {msg}")

        # Run async evaluation
        console.print("\n[bold]Starting evaluation...[/bold]\n")
        results = asyncio.run(
            evaluator.evaluate(
                agent_fn=agent_fn,
                baseline_agent_fn=baseline_fn,
                on_progress=on_progress,
            )
        )

        # Display results
        console.print("\n" + SkillEvaluationReporter.format_console(config, results))

        # Save results
        if save_report:
            output_path = evaluator.save_results(results, EVALS_DIR)
            console.print(f"[green]✓ Results saved:[/green] {output_path}")

        # Record activity
        record_activity(
            command="eval",
            subcommand="run-skill",
            args={
                "agent_name": agent_name,
                "skill_name": skill_name,
                "dataset_id": dataset_id,
                "metrics": metrics,
                "judge": judge,
            },
            repo_path=str(Path.cwd()),
        )

    except Exception as e:
        console.print(f"[red]✗ Evaluation failed: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# METRICS COMMANDS
# ==============================================================================

@metrics_app.command("list")
def list_metrics_command() -> None:
    """List all available evaluation metrics.

    Metrics are organized by type:
      - Quantitative: accuracy, F1, BLEU, latency, tokens, cost
      - Qualitative: helpfulness, clarity, relevance, safety (1-5 scale, LLM-judged)
      - Boolean: contains_hallucination, is_complete

    Examples:
        {CLI_NAME} eval metrics list
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
        table.add_column("Name", style="cyan")
        table.add_column("Unit", style="green")
        table.add_column("Lower Better", justify="center")
        table.add_column("Description")

        for name, metric in sorted(quantitative.items()):
            lower = "✓" if metric.lower_is_better else "✗"
            table.add_row(name, metric.unit or "—", lower, metric.description[:40] + "...")
        console.print(table)

    # Display qualitative metrics
    if qualitative:
        console.print("\n[bold cyan]Qualitative Metrics (1-5 scale, LLM-judged)[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Threshold", style="green")
        table.add_column("Description")

        for name, metric in sorted(qualitative.items()):
            threshold = f"{metric.threshold}" if metric.threshold else "—"
            table.add_row(name, threshold, metric.description[:40] + "...")
        console.print(table)

    # Display boolean metrics
    if boolean:
        console.print("\n[bold cyan]Boolean Metrics[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Description")

        for name, metric in sorted(boolean.items()):
            table.add_row(name, metric.description[:40] + "...")
        console.print(table)


# ==============================================================================
# REPORT COMMANDS
# ==============================================================================

@report_app.command("list")
def list_reports() -> None:
    """List evaluation reports.

    Examples:
        {CLI_NAME} eval report list
    """.format(CLI_NAME=CLI_NAME)

    eval_files = list(EVALS_DIR.glob("*.json"))
    if not eval_files:
        console.print("[yellow]No evaluations found[/yellow]")
        return

    console.print(f"[dim]Found {len(eval_files)} evaluations in {EVALS_DIR}[/dim]")
