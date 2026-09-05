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
from agentic_cli.evaluation.eval_config import EvaluationConfig, EvalConfigManager
from agentic_cli.evaluation.csv_dataset import CsvDatasetManager
from agentic_cli.evaluation.frameworks import get_framework, list_frameworks
from agentic_cli.evaluation.results import EvalResultStore
from agentic_cli.evaluation.reporting import compare_runs, write_html_report
from agentic_cli.evaluation.custom_metrics import CustomMetric, CustomMetricManager
from agentic_cli.evaluation.csv_dataset import CsvRow
from agentic_cli.evaluation.generation import (
    GenerationConfig,
    GoldenRegistry,
    get_generator,
    DEFAULT_PERSONAS,
)
from agentic_cli.tracker import record_activity

console = Console()
eval_app = typer.Typer(help="Evaluate agents, skills, and performance", rich_markup_mode=None)

# Subcommand apps
dataset_app = typer.Typer(help="Manage evaluation datasets")
validate_app = typer.Typer(help="Validate agents, skills, and datasets")
run_app = typer.Typer(help="Run evaluations (agent, skill, model)")
metrics_app = typer.Typer(help="View evaluation metrics")
metric_app = typer.Typer(help="Register and manage custom (prompt-based) metrics")
report_app = typer.Typer(help="View and export evaluation reports")

# Register subcommands
eval_app.add_typer(dataset_app, name="dataset")
eval_app.add_typer(validate_app, name="validate")
eval_app.add_typer(run_app, name="run")
eval_app.add_typer(metrics_app, name="metrics")
eval_app.add_typer(metric_app, name="metric")
eval_app.add_typer(report_app, name="report")

# Default datasets directory
DATASETS_DIR = Path.home() / ".agentic-cli" / "datasets"
EVALS_DIR = Path.home() / ".agentic-cli" / "evaluations"
EVAL_CONFIGS_DIR = Path.home() / ".agentic-cli" / "eval-configs"
CSV_DATASETS_DIR = Path.home() / ".agentic-cli" / "csv-datasets"
CUSTOM_METRICS_DIR = Path.home() / ".agentic-cli" / "custom-metrics"

dataset_manager = DatasetManager(DATASETS_DIR)
config_manager = EvalConfigManager(EVAL_CONFIGS_DIR)
csv_manager = CsvDatasetManager(CSV_DATASETS_DIR)
EVALS_DIR.mkdir(parents=True, exist_ok=True)
result_store = EvalResultStore(EVALS_DIR)
custom_metric_manager = CustomMetricManager(CUSTOM_METRICS_DIR)
golden_registry = GoldenRegistry(CSV_DATASETS_DIR)


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


@dataset_app.command("register")
def register_csv_dataset(
    name: Annotated[
        str,
        typer.Argument(help="Dataset name to register the CSV under"),
    ],
    csv_path: Annotated[
        Path,
        typer.Argument(help="Path to a CSV with a 'user_input' column (Ragas schema)"),
    ],
) -> None:
    """Register a CSV file as a new (versioned) evaluation dataset.

    Expected columns (only user_input is required):
      user_input, reference_contexts, reference, response

    Examples:
        {CLI_NAME} eval dataset register support-qa ./qa.csv
    """.format(CLI_NAME=CLI_NAME)

    try:
        version = csv_manager.register_from_file(name, Path(csv_path))
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    rows = csv_manager.read(name, version)
    record_activity(
        command="eval",
        subcommand="dataset-register",
        args={"name": name, "version": version},
        repo_path=str(Path.cwd()),
    )
    console.print(
        Panel.fit(
            f"[bold green]✓ CSV Dataset Registered[/bold green]\n\n"
            f"[bold]Name:[/bold] {name}\n"
            f"[bold]Version:[/bold] v{version}\n"
            f"[bold]Rows:[/bold] {len(rows)}\n"
            f"[bold]Location:[/bold] {csv_manager.path_for(name, version)}",
            border_style="green",
        )
    )


@dataset_app.command("versions")
def list_dataset_versions(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Dataset name (omit to list all CSV datasets)"),
    ] = None,
) -> None:
    """List versions of CSV datasets.

    Examples:
        {CLI_NAME} eval dataset versions
        {CLI_NAME} eval dataset versions support-qa
    """.format(CLI_NAME=CLI_NAME)

    if name:
        versions = csv_manager.list_versions(name)
        if not versions:
            console.print(f"[yellow]No versions found for CSV dataset '{name}'[/yellow]")
            return
        console.print(f"[bold cyan]{name}[/bold cyan]: " + ", ".join(f"v{v}" for v in versions))
        return

    datasets = csv_manager.list_datasets()
    if not datasets:
        console.print("[yellow]No CSV datasets found[/yellow]")
        return
    table = Table(show_header=True, header_style="bold magenta", title="CSV Datasets")
    table.add_column("Name", style="cyan")
    table.add_column("Versions", style="green")
    table.add_column("Latest", justify="right")
    for ds_name, versions in sorted(datasets.items()):
        table.add_row(ds_name, ", ".join(f"v{v}" for v in versions), f"v{versions[-1]}")
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


# ==============================================================================
# EVALUATION CONFIG COMMANDS (create / describe / delete / list)
# ==============================================================================

@eval_app.command("frameworks")
def list_frameworks_command() -> None:
    """List available evaluation frameworks.

    Examples:
        {CLI_NAME} eval frameworks
    """.format(CLI_NAME=CLI_NAME)

    table = Table(show_header=True, header_style="bold magenta", title="Evaluation Frameworks")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Notes")
    for name in list_frameworks():
        if name == "builtin":
            table.add_row(name, "available", "Native metrics + LLM judges (no extra deps)")
        elif name == "ragas":
            table.add_row(name, "optional", r"Install: pip install 'agentic-cli\[eval]'")
        else:
            table.add_row(name, "—", "")
    console.print(table)


@eval_app.command("create")
def create_eval_config(
    name: Annotated[str, typer.Argument(help="Evaluation config name")],
    dataset: Annotated[str, typer.Argument(help="CSV dataset name (see 'eval dataset versions')")],
    metrics: Annotated[
        str,
        typer.Option("--metrics", "-m", help="Comma-separated metric names"),
    ] = "accuracy,f1_score",
    framework: Annotated[
        str,
        typer.Option("--framework", "-f", help="Framework: builtin or ragas"),
    ] = "builtin",
    judge: Annotated[
        str,
        typer.Option("--judge", "-j", help="LLM judge for qualitative metrics: vertex-ai, anthropic, openai, none"),
    ] = "none",
    llm_model: Annotated[
        Optional[str],
        typer.Option("--llm", help="LLM model id (used by ragas)"),
    ] = None,
    embedding_model: Annotated[
        Optional[str],
        typer.Option("--embedding-model", help="Embedding model id (used by ragas)"),
    ] = None,
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Config description"),
    ] = "",
    domain: Annotated[
        Optional[str],
        typer.Option("--domain", help="Also store this config in the domain meta-repo (.platform/config/eval)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing config"),
    ] = False,
) -> None:
    """Create a reusable evaluation config (dataset + metrics + framework).

    Examples:
        {CLI_NAME} eval create support-eval support-qa --metrics accuracy,f1_score
        {CLI_NAME} eval create rag-eval docs-qa -f ragas -m Faithfulness,AnswerCorrectness
        {CLI_NAME} eval create qa-eval support-qa -m helpfulness,relevance -j vertex-ai
        {CLI_NAME} eval create facility-eval facility-qa --domain cwow-facility
    """.format(CLI_NAME=CLI_NAME)

    if config_manager.exists(name) and not force:
        console.print(f"[red]✗ Config '{name}' already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)

    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    if not metric_list:
        console.print("[red]✗ At least one metric is required[/red]")
        raise typer.Exit(1)

    # Validate framework + metrics (builtin validates locally; ragas validates lazily).
    # Include any registered custom metrics referenced by this config so they
    # validate as supported.
    requested_custom = {
        m.name: m.prompt
        for m in custom_metric_manager.list()
        if m.name in metric_list
    }
    try:
        fw = get_framework(
            framework,
            judge_type=judge,
            llm_model=llm_model,
            custom_metrics=requested_custom or None,
        )
    except (ValueError, ImportError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    unsupported = fw.validate_metrics(metric_list)
    if unsupported:
        console.print(
            f"[red]✗ Metrics not supported by '{framework}': {', '.join(unsupported)}[/red]"
        )
        console.print(f"[dim]Supported: {', '.join(fw.supported_metrics())}[/dim]")
        raise typer.Exit(1)

    config = EvaluationConfig(
        name=name,
        dataset=dataset,
        metrics=metric_list,
        framework=framework,
        judge=judge,
        llm_model=llm_model,
        embedding_model=embedding_model,
        description=description,
    )
    path = config_manager.save(config)

    # Optionally persist into the domain meta-repo for team sharing.
    meta_path = None
    if domain:
        from agentic_cli.evaluation.domain_eval import save_config_to_meta_repo

        config.metadata["domain"] = domain
        config_manager.save(config)
        meta_path = save_config_to_meta_repo(config, domain)
        if meta_path:
            console.print(f"[green]✓ Stored in meta-repo:[/green] {meta_path}")
        else:
            console.print(
                f"[yellow]No domain meta-repo found for '{domain}'; saved locally only.[/yellow]"
            )

    record_activity(
        command="eval",
        subcommand="create",
        args={"name": name, "dataset": dataset, "framework": framework, "domain": domain},
        repo_path=str(Path.cwd()),
    )
    console.print(
        Panel.fit(
            f"[bold green]✓ Evaluation Config Created[/bold green]\n\n"
            f"[bold]Name:[/bold] {name}\n"
            f"[bold]Dataset:[/bold] {dataset}\n"
            f"[bold]Framework:[/bold] {framework}\n"
            f"[bold]Judge:[/bold] {judge}\n"
            f"[bold]Metrics:[/bold] {', '.join(metric_list)}\n"
            f"[bold]Location:[/bold] {path}",
            border_style="green",
        )
    )


@eval_app.command("list")
def list_eval_configs() -> None:
    """List saved evaluation configs.

    Examples:
        {CLI_NAME} eval list
    """.format(CLI_NAME=CLI_NAME)

    configs = config_manager.list()
    if not configs:
        console.print("[yellow]No evaluation configs found[/yellow]")
        return
    table = Table(show_header=True, header_style="bold magenta", title="Evaluation Configs")
    table.add_column("Name", style="cyan")
    table.add_column("Dataset", style="green")
    table.add_column("Framework")
    table.add_column("Judge")
    table.add_column("Metrics")
    for c in configs:
        table.add_row(c.name, c.dataset, c.framework, c.judge, ", ".join(c.metrics))
    console.print(table)


@eval_app.command("describe")
def describe_eval_config(
    name: Annotated[str, typer.Argument(help="Evaluation config name")],
) -> None:
    """Show details of a saved evaluation config.

    Examples:
        {CLI_NAME} eval describe support-eval
    """.format(CLI_NAME=CLI_NAME)

    config = config_manager.load(name)
    if not config:
        console.print(f"[red]✗ Config not found: {name}[/red]")
        raise typer.Exit(1)
    console.print(
        Panel.fit(
            f"[bold cyan]{config.name}[/bold cyan]\n\n"
            f"[bold]Dataset:[/bold] {config.dataset}\n"
            f"[bold]Framework:[/bold] {config.framework}\n"
            f"[bold]Judge:[/bold] {config.judge}\n"
            f"[bold]Metrics:[/bold] {', '.join(config.metrics)}\n"
            f"[bold]LLM model:[/bold] {config.llm_model or '—'}\n"
            f"[bold]Embedding model:[/bold] {config.embedding_model or '—'}\n"
            f"[bold]Description:[/bold] {config.description or '—'}\n"
            f"[bold]Created:[/bold] {config.created[:19]}\n"
            f"[bold]Updated:[/bold] {config.updated[:19]}",
            border_style="cyan",
        )
    )


@eval_app.command("delete")
def delete_eval_config(
    name: Annotated[str, typer.Argument(help="Evaluation config name")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete a saved evaluation config.

    Examples:
        {CLI_NAME} eval delete support-eval --force
    """.format(CLI_NAME=CLI_NAME)

    if not config_manager.exists(name):
        console.print(f"[red]✗ Config not found: {name}[/red]")
        raise typer.Exit(1)
    if not force and not typer.confirm(f"Delete evaluation config '{name}'?", default=False):
        raise typer.Exit(0)
    config_manager.delete(name)
    console.print(f"[green]✓ Deleted config:[/green] {name}")


# ==============================================================================
# RUN AGENT COMMAND
# ==============================================================================

@run_app.command("agent")
def run_agent_eval(
    agent: Annotated[
        str,
        typer.Argument(help="Agent spec: 'module.path:function' or 'mock:<simple|qa|helpful>'"),
    ],
    eval_name: Annotated[
        str,
        typer.Argument(help="Saved evaluation config name (see 'eval list')"),
    ],
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", "-b", help="Parallel response-collection batch size (1-20)"),
    ] = 10,
    force_response_collection: Annotated[
        bool,
        typer.Option("--force-response-collection", help="Re-collect responses even if present"),
    ] = False,
    save_report: Annotated[
        bool,
        typer.Option("--save/--no-save", help="Save results JSON to the evaluations dir"),
    ] = True,
) -> None:
    """Run a saved evaluation config against a real agent.

    Steps:
      1. Load the eval config and its CSV dataset (latest version).
      2. Collect agent responses (writes a new dataset version if any collected).
      3. Score responses using the config's framework + metrics.
      4. Print aggregate scores and (optionally) save a results report.

    Examples:
        {CLI_NAME} eval run agent mock:helpful support-eval
        {CLI_NAME} eval run agent my_pkg.agents:answer support-eval --batch-size 5
    """.format(CLI_NAME=CLI_NAME)

    import uuid
    from datetime import datetime, timezone
    from agentic_cli.evaluation.agent_runner import AgentResponseCollector, resolve_agent
    from agentic_cli.evaluation.frameworks import EvalRow

    # 1. Load config
    config = config_manager.load(eval_name)
    if not config:
        console.print(f"[red]✗ Eval config not found: {eval_name}[/red]")
        raise typer.Exit(1)

    # 2. Load CSV dataset (latest version)
    try:
        version = csv_manager.latest_version(config.dataset)
        if version is None:
            raise FileNotFoundError(
                f"No CSV dataset '{config.dataset}'. Register one with "
                f"'{CLI_NAME} eval dataset register {config.dataset} <file.csv>'"
            )
        rows = csv_manager.read(config.dataset, version)
    except FileNotFoundError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    if not rows:
        console.print(f"[red]✗ Dataset '{config.dataset}' v{version} has no rows[/red]")
        raise typer.Exit(1)

    # Resolve agent
    try:
        agent_fn = resolve_agent(agent)
    except (ValueError, ImportError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]Agent Evaluation[/bold cyan]\n\n"
            f"[bold]Agent:[/bold] {agent}\n"
            f"[bold]Config:[/bold] {eval_name}\n"
            f"[bold]Dataset:[/bold] {config.dataset} v{version} ({len(rows)} rows)\n"
            f"[bold]Framework:[/bold] {config.framework}\n"
            f"[bold]Judge:[/bold] {config.judge}\n"
            f"[bold]Metrics:[/bold] {', '.join(config.metrics)}",
            border_style="cyan",
        )
    )

    # 2b. Collect responses
    needs_collection = force_response_collection or not csv_manager.has_responses(rows)
    if needs_collection:
        console.print("\n[bold]Collecting agent responses...[/bold]")
        collector = AgentResponseCollector(agent_fn, batch_size=batch_size)

        def on_progress(done: int, total: int) -> None:
            console.print(f"[dim]→ {done}/{total} responses collected[/dim]")

        collector.collect(rows, force=force_response_collection, on_progress=on_progress)
        new_version = csv_manager.write_new_version(config.dataset, rows)
        console.print(f"[green]✓ Responses saved:[/green] {config.dataset} v{new_version}")
    else:
        console.print("[dim]Responses already present; skipping collection "
                      "(use --force-response-collection to override).[/dim]")

    # 3. Score with framework (include any registered custom metrics in scope)
    requested_custom = {
        m.name: m.prompt
        for m in custom_metric_manager.list()
        if m.name in config.metrics
    }
    try:
        fw = get_framework(
            config.framework,
            judge_type=config.judge,
            llm_model=config.llm_model,
            embedding_model=config.embedding_model,
            custom_metrics=requested_custom or None,
        )
    except (ValueError, ImportError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    eval_rows = [
        EvalRow(
            input_text=r.user_input,
            reference=r.reference,
            response=r.response,
            retrieved_contexts=r.reference_contexts,
            row_id=str(i),
        )
        for i, r in enumerate(rows)
    ]

    console.print("\n[bold]Scoring responses...[/bold]")
    try:
        scores = fw.evaluate(
            eval_rows,
            config.metrics,
            llm_model=config.llm_model,
            embedding_model=config.embedding_model,
        )
    except Exception as e:
        console.print(f"[red]✗ Scoring failed: {e}[/red]")
        raise typer.Exit(1)

    # 4. Display + save
    table = Table(show_header=True, header_style="bold magenta", title="Aggregate Scores")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Range", justify="center")
    for metric_name in config.metrics:
        value = scores.aggregate.get(metric_name)
        rng = scores.metric_ranges.get(metric_name)
        rng_str = f"{rng[0]}-{rng[1]}" if rng else "—"
        table.add_row(metric_name, f"{value:.3f}" if value is not None else "—", rng_str)
    console.print("\n")
    console.print(table)

    if save_report:
        result = {
            "eval_id": f"agenteval-{uuid.uuid4().hex[:8]}",
            "eval_name": eval_name,
            "agent": agent,
            "dataset": config.dataset,
            "dataset_version": version,
            "framework": config.framework,
            "judge": config.judge,
            "metrics": config.metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scores": scores.to_dict(),
            "num_rows": len(rows),
        }
        out_path = EVALS_DIR / f"{result['eval_id']}.json"
        out_path.write_text(json.dumps(result, indent=2))
        console.print(f"[green]✓ Results saved:[/green] {out_path}")

    record_activity(
        command="eval",
        subcommand="run-agent",
        args={"agent": agent, "eval_name": eval_name},
        repo_path=str(Path.cwd()),
    )


# ==============================================================================
# COMPARE COMMAND
# ==============================================================================

@eval_app.command("compare")
def compare_eval(
    eval_name: Annotated[
        str,
        typer.Argument(help="Eval config name whose runs should be compared"),
    ],
    agents: Annotated[
        Optional[str],
        typer.Option("--agents", help="Comma-separated agent names to include (default: all)"),
    ] = None,
    compare_versions: Annotated[
        bool,
        typer.Option("--compare-versions", help="Compare all runs (label by agent@version) instead of latest-per-agent"),
    ] = False,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Optional HTML report output path"),
    ] = None,
) -> None:
    """Compare agent-evaluation runs for an eval config.

    By default compares the latest run per agent. Use --compare-versions to
    include every run (labeled by agent@dataset-version).

    Examples:
        {CLI_NAME} eval compare support-eval
        {CLI_NAME} eval compare support-eval --agents mock:simple,mock:helpful
        {CLI_NAME} eval compare support-eval --compare-versions -o compare.html
    """.format(CLI_NAME=CLI_NAME)

    if compare_versions:
        runs = result_store.for_eval(eval_name)
    else:
        runs = list(result_store.latest_per_agent(eval_name).values())

    if agents:
        wanted = {a.strip() for a in agents.split(",") if a.strip()}
        runs = [r for r in runs if r.agent in wanted]

    if not runs:
        console.print(f"[yellow]No runs found for eval '{eval_name}'. Run 'eval run agent' first.[/yellow]")
        raise typer.Exit(1)

    comparison = compare_runs(runs, by_version=compare_versions)

    # Render comparison table.
    table = Table(show_header=True, header_style="bold magenta", title=f"Comparison: {eval_name}")
    table.add_column("Metric", style="cyan")
    for label in comparison.labels:
        table.add_column(label, justify="right")
    for row in comparison.rows:
        cells = []
        for label in comparison.labels:
            score = row.scores.get(label)
            if score is None:
                cells.append("—")
            elif label == row.best_label:
                cells.append(f"[green]{score:.3f}[/green]")
            else:
                cells.append(f"{score:.3f}")
        table.add_row(row.metric, *cells)
    overall_cells = [f"{comparison.overall.get(l, 0):.3f}" for l in comparison.labels]
    table.add_row("[bold]Overall[/bold]", *overall_cells)
    console.print(table)

    if comparison.ranking:
        console.print(f"\n[bold]Ranking:[/bold] {' > '.join(comparison.ranking)}")

    if output:
        path = write_html_report(
            Path(output),
            title=f"Comparison: {eval_name}",
            runs=runs,
            comparison=comparison,
        )
        console.print(f"[green]✓ HTML report written:[/green] {path}")

    record_activity(
        command="eval",
        subcommand="compare",
        args={"eval_name": eval_name, "compare_versions": compare_versions},
        repo_path=str(Path.cwd()),
    )


# ==============================================================================
# REPORT GENERATE COMMAND (HTML)
# ==============================================================================

@report_app.command("generate")
def report_generate(
    eval_name: Annotated[
        str,
        typer.Argument(help="Eval config name to report on"),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="HTML report output path"),
    ] = Path("eval-report.html"),
    agent: Annotated[
        Optional[str],
        typer.Option("--agent", help="Only include runs for this agent"),
    ] = None,
    latest_only: Annotated[
        bool,
        typer.Option("--latest-only/--all-runs", help="Include only the latest run per agent"),
    ] = True,
) -> None:
    """Generate a self-contained interactive HTML report for an eval config.

    Examples:
        {CLI_NAME} eval report generate support-eval -o report.html
        {CLI_NAME} eval report generate support-eval --all-runs
    """.format(CLI_NAME=CLI_NAME)

    if latest_only:
        runs = list(result_store.latest_per_agent(eval_name).values())
    else:
        runs = result_store.for_eval(eval_name)

    if agent:
        runs = [r for r in runs if r.agent == agent]

    if not runs:
        console.print(f"[yellow]No runs found for eval '{eval_name}'.[/yellow]")
        raise typer.Exit(1)

    comparison = compare_runs(runs) if len(runs) > 1 else None
    path = write_html_report(
        Path(output),
        title=f"Evaluation Report: {eval_name}",
        runs=runs,
        comparison=comparison,
    )
    console.print(f"[green]✓ HTML report written:[/green] {path}")
    console.print(f"[dim]Open with: open {path}[/dim]")

    record_activity(
        command="eval",
        subcommand="report-generate",
        args={"eval_name": eval_name, "output": str(output)},
        repo_path=str(Path.cwd()),
    )


# ==============================================================================
# DATASET GENERATE COMMAND
# ==============================================================================

@dataset_app.command("generate")
def generate_dataset(
    name: Annotated[
        str,
        typer.Argument(help="Dataset name to create/version"),
    ],
    source: Annotated[
        str,
        typer.Option("--source", "-s", help="Source spec: 'local:<path>' or 'kg:<domain>'"),
    ],
    num_questions: Annotated[
        int,
        typer.Option("--num-questions", "-n", help="Number of questions to generate"),
    ] = 10,
    adversarial_ratio: Annotated[
        float,
        typer.Option("--adversarial-ratio", help="Fraction (0-1) of adversarial questions"),
    ] = 0.0,
    personas: Annotated[
        Optional[str],
        typer.Option("--personas", help="Comma-separated personas (default: end_user,domain_expert,new_employee)"),
    ] = None,
    use_ai: Annotated[
        bool,
        typer.Option("--ai/--no-ai", help="Use Vertex AI generation (falls back to heuristic on error)"),
    ] = False,
    model: Annotated[
        str,
        typer.Option("--model", help="Vertex AI model for generation"),
    ] = "gemini-2.5-flash",
    golden: Annotated[
        bool,
        typer.Option("--golden", help="Mark the generated version as the golden baseline"),
    ] = False,
) -> None:
    """Generate a Q&A evaluation dataset from documents or the domain KG.

    The dataset uses the Ragas schema and is written as a new version. Use
    'kg:<domain>' to source questions from ingested domain knowledge.

    Examples:
        {CLI_NAME} eval dataset generate faq --source local:./docs -n 20
        {CLI_NAME} eval dataset generate facility --source kg:cwow-facility -n 15 --adversarial-ratio 0.2
        {CLI_NAME} eval dataset generate faq --source local:./docs --ai --golden
    """.format(CLI_NAME=CLI_NAME)

    # Resolve source (kg: handled by domain_eval, file/placeholder by sources).
    from agentic_cli.evaluation.domain_eval import resolve_source

    try:
        doc_source = resolve_source(source)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Loading source:[/bold] {source}")
    try:
        chunks = doc_source.load_chunks()
    except (FileNotFoundError, ValueError, NotImplementedError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    console.print(f"[dim]→ {len(chunks)} source chunk(s) loaded[/dim]")

    persona_list = (
        [p.strip() for p in personas.split(",") if p.strip()] if personas else list(DEFAULT_PERSONAS)
    )
    gen_config = GenerationConfig(
        num_questions=num_questions,
        adversarial_ratio=adversarial_ratio,
        personas=persona_list,
    )

    generator = get_generator(use_ai=use_ai, model=model)
    console.print(f"[bold]Generating questions[/bold] (generator={'vertex-ai' if use_ai else 'heuristic'})...")
    rows = generator.generate(chunks, gen_config)

    if not rows:
        console.print("[red]✗ No questions generated.[/red]")
        raise typer.Exit(1)

    version = csv_manager.write_new_version(name, rows)
    console.print(f"[green]✓ Dataset written:[/green] {name} v{version} ({len(rows)} rows)")

    if golden:
        golden_registry.mark(name, version, note="generated")
        console.print(f"[green]✓ Marked golden:[/green] {name} v{version}")

    record_activity(
        command="eval",
        subcommand="dataset-generate",
        args={"name": name, "source": source, "num_questions": num_questions},
        repo_path=str(Path.cwd()),
    )


@dataset_app.command("golden")
def mark_golden(
    name: Annotated[str, typer.Argument(help="Dataset name")],
    version: Annotated[
        Optional[int],
        typer.Option("--version", "-v", help="Version to mark (default: latest)"),
    ] = None,
    unmark: Annotated[
        bool,
        typer.Option("--unmark", help="Remove the golden marker instead"),
    ] = False,
) -> None:
    """Mark (or unmark) a dataset version as the golden baseline.

    Examples:
        {CLI_NAME} eval dataset golden faq            # mark latest
        {CLI_NAME} eval dataset golden faq -v 2       # mark version 2
        {CLI_NAME} eval dataset golden faq --unmark
    """.format(CLI_NAME=CLI_NAME)

    if unmark:
        removed = golden_registry.unmark(name)
        if removed:
            console.print(f"[green]✓ Removed golden marker for[/green] {name}")
        else:
            console.print(f"[yellow]No golden marker for '{name}'.[/yellow]")
        return

    if version is None:
        version = csv_manager.latest_version(name)
    if version is None:
        console.print(f"[red]✗ No versions found for dataset '{name}'.[/red]")
        raise typer.Exit(1)

    golden_registry.mark(name, version)
    console.print(f"[green]✓ Marked golden:[/green] {name} v{version}")


# ==============================================================================
# CUSTOM METRIC COMMANDS
# ==============================================================================

@metric_app.command("register")
def register_metric(
    name: Annotated[str, typer.Argument(help="Custom metric name")],
    prompt: Annotated[
        Optional[str],
        typer.Option("--prompt", "-p", help="Scoring prompt/criteria text"),
    ] = None,
    prompt_file: Annotated[
        Optional[Path],
        typer.Option("--prompt-file", "-f", help="Read scoring prompt from a file"),
    ] = None,
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Short description"),
    ] = "",
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite if a metric with this name exists"),
    ] = False,
) -> None:
    """Register a custom prompt-based (LLM-as-Judge) metric (scored 1-5).

    Examples:
        {CLI_NAME} eval metric register empathy -p "Rate how empathetic the answer is (1-5)."
        {CLI_NAME} eval metric register policy_adherence -f ./prompts/policy.md
    """.format(CLI_NAME=CLI_NAME)

    if custom_metric_manager.exists(name) and not force:
        console.print(f"[red]✗ Metric '{name}' already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)

    text = prompt
    if prompt_file:
        if not prompt_file.exists():
            console.print(f"[red]✗ Prompt file not found: {prompt_file}[/red]")
            raise typer.Exit(1)
        text = prompt_file.read_text(encoding="utf-8")

    if not text or not text.strip():
        console.print("[red]✗ A scoring prompt is required (--prompt or --prompt-file).[/red]")
        raise typer.Exit(1)

    metric = CustomMetric(name=name, prompt=text.strip(), description=description)
    path = custom_metric_manager.register(metric)
    console.print(f"[green]✓ Registered custom metric '{name}'[/green] → {path}")

    record_activity(
        command="eval",
        subcommand="metric-register",
        args={"name": name},
        repo_path=str(Path.cwd()),
    )


@metric_app.command("unregister")
def unregister_metric(
    name: Annotated[str, typer.Argument(help="Custom metric name")],
) -> None:
    """Remove a registered custom metric.

    Examples:
        {CLI_NAME} eval metric unregister empathy
    """.format(CLI_NAME=CLI_NAME)

    if custom_metric_manager.unregister(name):
        console.print(f"[green]✓ Unregistered custom metric '{name}'[/green]")
    else:
        console.print(f"[yellow]No custom metric named '{name}'.[/yellow]")


@metric_app.command("list")
def list_custom_metrics() -> None:
    """List registered custom (prompt-based) metrics.

    Examples:
        {CLI_NAME} eval metric list
    """.format(CLI_NAME=CLI_NAME)

    metrics = custom_metric_manager.list()
    if not metrics:
        console.print("[yellow]No custom metrics registered.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Custom Metrics")
    table.add_column("Name", style="cyan")
    table.add_column("Scale", justify="center")
    table.add_column("Description")
    table.add_column("Prompt (preview)")
    for m in metrics:
        preview = (m.prompt[:50] + "…") if len(m.prompt) > 50 else m.prompt
        table.add_row(m.name, f"{m.scale_min:g}-{m.scale_max:g}", m.description or "—", preview)
    console.print(table)


@eval_app.command("session")
def eval_session(
    session: Annotated[str, typer.Argument(help="Session / correlation id (see `keel context trace`)")],
    reference: Annotated[Optional[str], typer.Option("--reference", help="Ground-truth answer, if you have one — unlocks ContextRecall")] = None,
    metrics: Annotated[Optional[str], typer.Option("--metrics", help="Comma-separated metric names (default: the reference-free set)")] = None,
    framework: Annotated[str, typer.Option("--framework", help="Evaluation framework")] = "ragas",
    as_json: Annotated[bool, typer.Option("--json", help="Emit scores as JSON")] = False,
) -> None:
    """Score a real session against the context it actually retrieved.

    This is the eval feed: ``EvalRow.retrieved_contexts`` is built from the
    tier-two payload store, so metrics that need retrieved context finally have
    some. Until now they scored against an empty list.

    Reads the split diagnosis a single number cannot express — low precision
    means the retriever brought junk, low faithfulness means the agent had the
    context and ignored it.
    """
    import json as _json

    from agentic_cli.evaluation import session_feed

    feed = session_feed.build(session, reference=reference or "")

    if not feed.scorable:
        console.print(f"[yellow]Session [bold]{session}[/bold] cannot be scored.[/yellow]")
        for problem in feed.problems:
            console.print(f"  [yellow]•[/yellow] {problem}")
        raise typer.Exit(1)

    names = ([m.strip() for m in metrics.split(",") if m.strip()]
             if metrics else session_feed.metrics_for(reference or ""))

    console.print(
        f"Scoring [bold]{session}[/bold] over [bold]{feed.contexts}[/bold] "
        f"retrieved context(s) with: {', '.join(names)}")
    if feed.lossy:
        console.print(
            f"[yellow]⚠ Some context was masked before storage "
            f"({', '.join(feed.masked_kinds)}). Scores are computed over text "
            f"the agent did not literally see.[/yellow]")

    from rich.markup import escape

    from agentic_cli.evaluation.frameworks import get_framework

    def _unavailable(exc: Exception) -> None:
        # Exception text carries "pip install 'agentic-cli[eval]'", and Rich
        # reads [eval] as a style tag and swallows it — leaving advice that
        # tells the user to install what they already have.
        console.print(f"[red]✗ {escape(str(exc))}[/red]")
        console.print("[dim]Context metrics need an LLM judge, so they cannot run "
                      "in test mode or without the optional extra.[/dim]")

    try:
        engine = get_framework(framework)
    except Exception as exc:  # noqa: BLE001
        _unavailable(exc)
        raise typer.Exit(1)

    try:
        scores = engine.evaluate([feed.row], names)
    except ImportError as exc:
        _unavailable(exc)
        raise typer.Exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]✗ Evaluation failed: {escape(str(exc))}[/red]")
        raise typer.Exit(1)

    if as_json:
        payload = scores.to_dict()
        payload["feed"] = feed.to_dict()
        console.print_json(_json.dumps(payload))
        raise typer.Exit(0)

    table = Table(title=f"Context evaluation — {session}", show_lines=False)
    table.add_column("Metric", no_wrap=True)
    table.add_column("Score", justify="right")
    table.add_column("Reads as", overflow="fold")

    for name, value in (scores.aggregate or {}).items():
        table.add_row(name, f"{value:.2f}" if isinstance(value, (int, float)) else str(value),
                      _DIAGNOSIS.get(name.lower(), ""))
    console.print(table)

    for error in scores.errors or []:
        console.print(f"[yellow]⚠ {error}[/yellow]")

    record_activity(command="eval", subcommand="session",
                    args={"session": session, "metrics": names,
                          "contexts": feed.contexts, "lossy": feed.lossy})


#: What a low score on each metric points at — the split diagnosis a single
#: number cannot express, and the reason the feed was worth building.
_DIAGNOSIS = {
    "faithfulness": "low → the agent had the context and ignored it (prompt or skill)",
    "responserelevancy": "low → the answer drifted from the question",
    "contextprecisionwithoutreference": "low → the retriever brought junk (retriever / KG query)",
    "contextrecall": "low → the right source was never retrieved (ingestion coverage)",
}


@eval_app.command("playground")
def eval_playground(
    session: Annotated[str, typer.Argument(help="Session to replay (see `keel context trace`)")],
    without: Annotated[Optional[list[str]], typer.Option("--without", help="Source key to switch off, e.g. kg/query. Repeatable — one variant each.")] = None,
    model: Annotated[Optional[list[str]], typer.Option("--model", help="Also replay with this model, context unchanged. Repeatable.")] = None,
    metrics: Annotated[Optional[str], typer.Option("--metrics", help="Comma-separated metrics (default: the reference-free set)")] = None,
    no_score: Annotated[bool, typer.Option("--no-score", help="Re-run without scoring — shows the answer change only")] = False,
    sources: Annotated[bool, typer.Option("--sources", help="List what can be switched off, and stop")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the comparison as JSON")] = False,
) -> None:
    """Re-run a session's question against a different context, and watch it move.

    A score tells you a session went badly; removing a source and re-running
    tells you that source was why. Ablation is what makes the ledger an
    instrument rather than a report.

    Scoring needs a judge, re-running only needs a provider — so without Ragas
    this still shows the answer changing, which is often enough to see what a
    source was contributing.
    """
    import json as _json

    from rich.markup import escape

    from agentic_cli.evaluation import playground

    available = playground.list_sources(session)
    if not available:
        console.print(f"[yellow]No stored context for session [bold]{session}[/bold].[/yellow]")
        console.print("[dim]Enable KEEL_PAYLOAD_STORE before the session runs, or the "
                      "payloads may have expired.[/dim]")
        raise typer.Exit(1)

    if sources:
        table = Table(title=f"Ablatable sources — {session}", show_lines=False)
        table.add_column("Key", no_wrap=True)
        table.add_column("Payloads", justify="right")
        table.add_column("Bytes", justify="right")
        for src in available:
            table.add_row(src.key, str(src.payloads), str(src.bytes))
        console.print(table)
        console.print(f"[dim]Switch one off: {CLI_NAME} eval playground {session} "
                      f"--without {available[0].key}[/dim]")
        raise typer.Exit(0)

    known = {s.key for s in available}
    unknown = [w for w in (without or []) if w not in known]
    if unknown:
        console.print(f"[red]✗ Unknown source(s): {', '.join(unknown)}[/red]")
        console.print(f"[dim]Available: {', '.join(sorted(known))}[/dim]")
        raise typer.Exit(1)

    names = [m.strip() for m in metrics.split(",") if m.strip()] if metrics else None
    comparison = playground.compare(
        session,
        ablations=[[w] for w in (without or [])],
        models=list(model or []),
        metrics=names,
        do_score=not no_score,
    )

    if as_json:
        console.print_json(_json.dumps(comparison.to_dict()))
        raise typer.Exit(0)

    rows = [comparison.baseline] + comparison.variants if comparison.baseline else comparison.variants
    metric_names = sorted({m for r in rows for m in r.scores})

    table = Table(title=f"Context playground — {session}", show_lines=True)
    table.add_column("Variant", no_wrap=True)
    table.add_column("Ctx", justify="right", no_wrap=True)
    for name in metric_names:
        table.add_column(name[:14], justify="right", no_wrap=True)
    table.add_column("Answer", overflow="fold")

    baseline_scores = comparison.baseline.scores if comparison.baseline else {}
    for variant in rows:
        cells = []
        for name in metric_names:
            value = variant.scores.get(name)
            if value is None:
                cells.append("[dim]—[/dim]")
                continue
            base = baseline_scores.get(name)
            if variant is comparison.baseline or base is None:
                cells.append(f"{value:.2f}")
            else:
                delta = value - base
                style = "red" if delta < -0.01 else ("green" if delta > 0.01 else "dim")
                cells.append(f"{value:.2f}\n[{style}]{delta:+.2f}[/{style}]")
        answer = variant.answer or f"[dim]{escape('; '.join(variant.problems))}[/dim]"
        table.add_row(variant.label, str(variant.contexts), *cells, answer[:220])

    console.print(table)

    if not metric_names:
        console.print("[dim]No scores — re-run only. Scoring needs Ragas and a judge; "
                      "the answer column still shows what each source was contributing.[/dim]")

    record_activity(command="eval", subcommand="playground",
                    args={"session": session, "variants": len(comparison.variants),
                          "scored": bool(metric_names)})
