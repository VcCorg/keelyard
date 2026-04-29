"""Initialization and authentication commands."""

import json
import subprocess
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from typing_extensions import Annotated

from agentic_cli.tracker import record_activity
from agentic_cli.config import CLI_NAME

console = Console()
init_app = typer.Typer(help="Initialize and configure authentication", rich_markup_mode=None)

# Configuration file location
CONFIG_DIR = Path.home() / ".dva-agentic"
CONFIG_FILE = CONFIG_DIR / "config.json"


def ensure_config_dir():
    """Ensure configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict):
    """Save configuration to file."""
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


@init_app.command("vertex-ai")
def init_vertex_ai(
    project_id: Annotated[
        str,
        typer.Option(
            "--project-id",
            help="Google Cloud Project ID",
        ),
    ] = "",
    location: Annotated[
        str,
        typer.Option(
            "--location",
            help="Google Cloud location/region",
        ),
    ] = "",
    credentials_path: Annotated[
        str,
        typer.Option(
            "--credentials",
            help="Path to service account JSON key file",
        ),
    ] = "",
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Vertex AI model to use",
        ),
    ] = "",
    skip_auth: Annotated[
        bool,
        typer.Option(
            "--skip-auth",
            help="Skip gcloud auth application-default login",
        ),
    ] = False,
) -> None:
    """
    Initialize Vertex AI configuration.
    
    This command saves your Vertex AI settings for use in new projects.
    Reuses existing configuration if available.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Vertex AI Configuration[/bold cyan]",
            border_style="cyan",
        )
    )

    # Load existing configuration
    config = load_config()
    existing_google_config = config.get("google", {})
    
    # Use existing values as defaults if not provided via CLI
    if not project_id:
        existing_project_id = existing_google_config.get("project_id", "")
        if existing_project_id:
            console.print(f"[dim]Using existing project ID: {existing_project_id}[/dim]")
            project_id = existing_project_id
        else:
            project_id = Prompt.ask("Enter your Google Cloud Project ID")
    
    if not location:
        location = existing_google_config.get("location", "us-central1")
    
    if not model:
        model = existing_google_config.get("model", "gemini-pro")
    
    if not credentials_path:
        credentials_path = existing_google_config.get("credentials_path", "")

    # Validate project ID
    if not project_id:
        console.print("[red]✗ Error:[/red] Project ID is required")
        raise typer.Exit(1)

    # Check if gcloud is installed
    try:
        result = subprocess.run(
            ["gcloud", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            console.print("[green]✓[/green] gcloud CLI detected")
        else:
            console.print(
                "[yellow]⚠ Warning:[/yellow] gcloud CLI not found. "
                "Install from: https://cloud.google.com/sdk/docs/install"
            )
    except FileNotFoundError:
        console.print(
            "[yellow]⚠ Warning:[/yellow] gcloud CLI not found. "
            "Install from: https://cloud.google.com/sdk/docs/install"
        )

    # Authenticate unless skipped
    if not skip_auth:
        console.print("\n[cyan]Running gcloud authentication...[/cyan]")
        try:
            subprocess.run(
                ["gcloud", "auth", "application-default", "login"],
                check=True,
            )
            console.print("[green]✓[/green] Authentication successful")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Error:[/red] Authentication failed: {e}")
            if not Confirm.ask("Continue anyway?"):
                raise typer.Exit(1)
        except FileNotFoundError:
            console.print(
                "[red]✗ Error:[/red] gcloud CLI not found. "
                "Install from: https://cloud.google.com/sdk/docs/install"
            )
            if not Confirm.ask("Continue anyway?"):
                raise typer.Exit(1)
    else:
        console.print("\n[yellow]⚠[/yellow] Skipping authentication (--skip-auth flag used)")

    # Validate credentials file if provided
    if credentials_path:
        creds_path = Path(credentials_path).expanduser().resolve()
        if not creds_path.exists():
            console.print(
                f"[yellow]⚠ Warning:[/yellow] Credentials file not found: {creds_path}"
            )
            if not Confirm.ask("Continue anyway?"):
                raise typer.Exit(1)
        else:
            console.print(f"[green]✓[/green] Credentials file found: {creds_path}")
            credentials_path = str(creds_path)

    # Save configuration (reuse already loaded config)
    config["google"] = {
        "project_id": project_id,
        "location": location,
        "credentials_path": credentials_path,
        "model": model,
    }
    save_config(config)

    record_activity(
        command="init",
        subcommand="vertex-ai",
        args={"project_id": project_id, "location": location, "model": model},
    )

    console.print(
        Panel.fit(
            f"[bold green]✓ Configuration saved![/bold green]\n\n"
            f"[bold]Vertex AI Settings:[/bold]\n"
            f"  Project ID: {project_id}\n"
            f"  Location: {location}\n"
            f"  Model: {model}\n"
            f"  Credentials: {credentials_path or 'Application Default Credentials'}\n\n"
            f"[dim]Config saved to: {CONFIG_FILE}[/dim]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Create a new project: {CLI_NAME} project create my-project\n"
            f"  2. The Vertex AI settings will be automatically added to .env",
            title="Success",
            border_style="green",
        )
    )


@init_app.command("show")
def show_config() -> None:
    """Show current configuration."""
    config = load_config()
    
    if not config:
        console.print("[yellow]No configuration found.[/yellow]")
        console.print(f"[dim]Run '{CLI_NAME} init vertex-ai' to configure Vertex AI.[/dim]")
        return

    console.print(
        Panel.fit(
            "[bold cyan]Current Configuration[/bold cyan]",
            border_style="cyan",
        )
    )

    if "google" in config:
        google_config = config["google"]
        console.print("\n[bold]Vertex AI:[/bold]")
        console.print(f"  Project ID: {google_config.get('project_id', 'Not set')}")
        console.print(f"  Location: {google_config.get('location', 'Not set')}")
        console.print(f"  Model: {google_config.get('model', 'Not set')}")
        console.print(
            f"  Credentials: {google_config.get('credentials_path', 'Application Default') or 'Application Default'}"
        )

    console.print(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")


@init_app.command("reset")
def reset_config(
    confirm: Annotated[
        bool,
        typer.Option(
            "--yes",
            help="Skip confirmation prompt",
        ),
    ] = False,
) -> None:
    """Reset configuration to defaults."""
    if not confirm:
        if not Confirm.ask("Are you sure you want to reset all configuration?"):
            console.print("[dim]Operation cancelled.[/dim]")
            raise typer.Exit(0)

    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        record_activity(command="init", subcommand="reset")
        console.print("[green]✓[/green] Configuration reset successfully")
    else:
        console.print("[yellow]No configuration to reset.[/yellow]")


@init_app.command("anthropic")
def init_anthropic(
    api_key: Annotated[
        str,
        typer.Option(
            "--api-key",
            help="Anthropic API key (or use ANTHROPIC_API_KEY env var)",
        ),
    ] = "",
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Claude model to use",
        ),
    ] = "",
) -> None:
    """
    Initialize Anthropic (Claude) configuration.

    This command saves your Anthropic API key for use in new projects.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Anthropic Configuration[/bold cyan]",
            border_style="cyan",
        )
    )

    # Load existing configuration
    config = load_config()
    existing_anthropic_config = config.get("anthropic", {})

    # Get API key
    if not api_key:
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            console.print(f"[dim]Using ANTHROPIC_API_KEY from environment[/dim]")
        else:
            existing_key = existing_anthropic_config.get("api_key", "")
            if existing_key:
                console.print(f"[dim]Using existing API key[/dim]")
                api_key = existing_key
            else:
                api_key = Prompt.ask("Enter your Anthropic API key (from https://console.anthropic.com)")

    if not model:
        model = existing_anthropic_config.get("model", "claude-3-5-sonnet-20241022")

    if not api_key:
        console.print("[red]✗ Error:[/red] API key is required")
        raise typer.Exit(1)

    # Save configuration
    config["anthropic"] = {
        "provider_type": "anthropic",
        "api_key": api_key,
        "model": model,
    }
    save_config(config)

    record_activity(
        command="init",
        subcommand="anthropic",
        args={"model": model},
    )

    console.print(
        Panel.fit(
            f"[bold green]✓ Configuration saved![/bold green]\n\n"
            f"[bold]Anthropic Settings:[/bold]\n"
            f"  Model: {model}\n"
            f"  API Key: {'✓ Configured' if api_key else '✗ Not set'}\n\n"
            f"[dim]Config saved to: {CONFIG_FILE}[/dim]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Use Claude with skill generation: {CLI_NAME} skill generate --model {model}\n"
            f"  2. Set as default: {CLI_NAME} init set-default-provider anthropic",
            title="Success",
            border_style="green",
        )
    )


@init_app.command("openai")
def init_openai(
    api_key: Annotated[
        str,
        typer.Option(
            "--api-key",
            help="OpenAI API key (or use OPENAI_API_KEY env var)",
        ),
    ] = "",
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="OpenAI model to use",
        ),
    ] = "",
) -> None:
    """
    Initialize OpenAI (GPT) configuration.

    This command saves your OpenAI API key for use in new projects.
    """
    console.print(
        Panel.fit(
            "[bold cyan]OpenAI Configuration[/bold cyan]",
            border_style="cyan",
        )
    )

    # Load existing configuration
    config = load_config()
    existing_openai_config = config.get("openai", {})

    # Get API key
    if not api_key:
        import os
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            console.print(f"[dim]Using OPENAI_API_KEY from environment[/dim]")
        else:
            existing_key = existing_openai_config.get("api_key", "")
            if existing_key:
                console.print(f"[dim]Using existing API key[/dim]")
                api_key = existing_key
            else:
                api_key = Prompt.ask("Enter your OpenAI API key (from https://platform.openai.com/api-keys)")

    if not model:
        model = existing_openai_config.get("model", "gpt-4")

    if not api_key:
        console.print("[red]✗ Error:[/red] API key is required")
        raise typer.Exit(1)

    # Save configuration
    config["openai"] = {
        "provider_type": "openai",
        "api_key": api_key,
        "model": model,
    }
    save_config(config)

    record_activity(
        command="init",
        subcommand="openai",
        args={"model": model},
    )

    console.print(
        Panel.fit(
            f"[bold green]✓ Configuration saved![/bold green]\n\n"
            f"[bold]OpenAI Settings:[/bold]\n"
            f"  Model: {model}\n"
            f"  API Key: {'✓ Configured' if api_key else '✗ Not set'}\n\n"
            f"[dim]Config saved to: {CONFIG_FILE}[/dim]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Use GPT with skill generation: {CLI_NAME} skill generate --model {model}\n"
            f"  2. Set as default: {CLI_NAME} init set-default-provider openai",
            title="Success",
            border_style="green",
        )
    )


@init_app.command("set-default-provider")
def set_default_provider(
    provider: Annotated[
        str,
        typer.Argument(help="Provider to set as default (google, anthropic, openai)"),
    ],
) -> None:
    """
    Set the default LLM provider for skill generation and other commands.

    The default provider is used when no --model flag is specified.
    """
    valid_providers = ["google", "anthropic", "openai"]
    if provider not in valid_providers:
        console.print(f"[red]✗ Invalid provider: {provider}[/red]")
        console.print(f"[dim]Valid options: {', '.join(valid_providers)}[/dim]")
        raise typer.Exit(1)

    # Load existing configuration
    config = load_config()

    # Verify provider is configured
    provider_config_key = "google" if provider == "google" else provider
    if provider_config_key not in config:
        console.print(f"[yellow]⚠ Warning:[/yellow] {provider} is not configured")
        console.print(f"[dim]Initialize first: {CLI_NAME} init {provider}[/dim]")
        if not Confirm.ask("Continue anyway?", default=False):
            raise typer.Exit(0)

    # Ensure llm section exists
    config.setdefault("llm", {})
    config["llm"]["default_provider"] = provider

    save_config(config)

    record_activity(
        command="init",
        subcommand="set-default-provider",
        args={"provider": provider},
    )

    console.print()
    console.print(
        Panel.fit(
            f"[bold green]✓ Default provider set![/bold green]\n\n"
            f"[bold]Default Provider:[/bold] {provider}\n\n"
            f"[dim]From now on, commands will use {provider} by default[/dim]\n"
            f"[dim]You can still override with --model flag[/dim]",
            border_style="green",
        )
    )


def get_google_config() -> dict:
    """Get Google configuration for use in other commands."""
    config = load_config()
    return config.get("google", {})
