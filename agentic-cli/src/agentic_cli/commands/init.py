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


@init_app.callback()
def check_workspace_config(
    ctx: typer.Context,
) -> None:
    """
    Check if workspaces are configured before running init commands.
    
    If workspaces are not configured, prompt the user to run 'dva init workspace'.
    """
    # Skip check for show, reset, and workspace commands
    if ctx.invoked_subcommand in ["show", "reset", "workspace"]:
        return
    
    config = load_config()
    code_workspace = config.get("code_workspace")
    docs_workspace = config.get("docs_workspace")
    
    if not code_workspace or not docs_workspace:
        console.print()
        console.print("[yellow]⚠ Workspace configuration required[/yellow]")
        console.print(f"[dim]Run '{CLI_NAME} init workspace' to configure workspaces.[/dim]")
        console.print()
        
        # Auto-prompt for workspace configuration
        if Confirm.ask("Configure workspaces now?", default=True):
            ctx.invoke(init_workspace)


# Configuration file location
CONFIG_DIR = Path.home() / ".agent-cli-agentic"
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
        console.print(f"[dim]Run '{CLI_NAME} init workspace' to configure workspaces.[/dim]")
        console.print(f"[dim]Run '{CLI_NAME} init vertex-ai' to configure Vertex AI.[/dim]")
        return

    console.print(
        Panel.fit(
            "[bold cyan]Current Configuration[/bold cyan]",
            border_style="cyan",
        )
    )

    # Show workspaces
    console.print("\n[bold]Workspaces:[/bold]")
    code_workspace = config.get("code_workspace", "Not set")
    docs_workspace = config.get("docs_workspace", "Not set")
    console.print(f"  Code Workspace: {code_workspace}")
    console.print(f"  Docs Workspace: {docs_workspace}")

    # Show LLM provider configurations
    if "google" in config:
        google_config = config["google"]
        console.print("\n[bold]Vertex AI:[/bold]")
        console.print(f"  Project ID: {google_config.get('project_id', 'Not set')}")
        console.print(f"  Location: {google_config.get('location', 'Not set')}")
        console.print(f"  Model: {google_config.get('model', 'Not set')}")
        console.print(
            f"  Credentials: {google_config.get('credentials_path', 'Application Default') or 'Application Default'}"
        )

    if "anthropic" in config:
        anthropic_config = config["anthropic"]
        console.print("\n[bold]Anthropic:[/bold]")
        console.print(f"  Model: {anthropic_config.get('model', 'Not set')}")
        console.print(f"  API Key: {'✓ Configured' if anthropic_config.get('api_key') else '✗ Not set'}")

    if "openai" in config:
        openai_config = config["openai"]
        console.print("\n[bold]OpenAI:[/bold]")
        console.print(f"  Model: {openai_config.get('model', 'Not set')}")
        console.print(f"  API Key: {'✓ Configured' if openai_config.get('api_key') else '✗ Not set'}")

    if "llm" in config:
        llm_config = config["llm"]
        console.print("\n[bold]LLM Settings:[/bold]")
        console.print(f"  Default Provider: {llm_config.get('default_provider', 'Not set')}")

    # Integration credentials (from .env / environment)
    import os
    from agentic_cli.env import resolved_env_files
    console.print("\n[bold]Integrations (.env / environment):[/bold]")
    for name, (label, url_env, token_env) in _INTEGRATIONS.items():
        url = os.environ.get(url_env, "").strip()
        token = os.environ.get(token_env, "").strip()
        if url and token:
            console.print(f"  {label}: [green]✓ configured[/green] ({url})")
        elif url or token:
            console.print(f"  {label}: [yellow]partial[/yellow] (missing {'token' if url else 'URL'})")
        else:
            console.print(f"  {label}: [dim]not set[/dim]  →  {CLI_NAME} init {name} --url <> --token <>")
    env_files = resolved_env_files()
    if env_files:
        console.print(f"[dim]  .env: {', '.join(str(f) for f in env_files)}[/dim]")

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
    workspaces: Annotated[
        bool,
        typer.Option(
            "--workspaces",
            help="Reset only workspace configuration",
        ),
    ] = False,
    llm: Annotated[
        bool,
        typer.Option(
            "--llm",
            help="Reset only LLM provider configuration",
        ),
    ] = False,
) -> None:
    """Reset configuration to defaults."""
    config = load_config()
    
    if not confirm:
        if workspaces:
            if not Confirm.ask("Are you sure you want to reset workspace configuration?"):
                console.print("[dim]Operation cancelled.[/dim]")
                raise typer.Exit(0)
        elif llm:
            if not Confirm.ask("Are you sure you want to reset LLM provider configuration?"):
                console.print("[dim]Operation cancelled.[/dim]")
                raise typer.Exit(0)
        else:
            if not Confirm.ask("Are you sure you want to reset all configuration?"):
                console.print("[dim]Operation cancelled.[/dim]")
                raise typer.Exit(0)

    if workspaces:
        # Reset only workspaces
        if "code_workspace" in config:
            del config["code_workspace"]
        if "docs_workspace" in config:
            del config["docs_workspace"]
        save_config(config)
        record_activity(command="init", subcommand="reset", args={"workspaces": True})
        console.print("[green]✓[/green] Workspace configuration reset successfully")
    elif llm:
        # Reset only LLM providers
        if "google" in config:
            del config["google"]
        if "anthropic" in config:
            del config["anthropic"]
        if "openai" in config:
            del config["openai"]
        if "llm" in config:
            del config["llm"]
        save_config(config)
        record_activity(command="init", subcommand="reset", args={"llm": True})
        console.print("[green]✓[/green] LLM provider configuration reset successfully")
    else:
        # Reset all configuration
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            record_activity(command="init", subcommand="reset")
            console.print("[green]✓[/green] Configuration reset successfully")
        else:
            console.print("[yellow]No configuration to reset.[/yellow]")


@init_app.command("workspace")
def init_workspace(
    code_workspace: Annotated[
        str,
        typer.Option(
            "--code",
            help="Directory for code repositories",
        ),
    ] = "",
    docs_workspace: Annotated[
        str,
        typer.Option(
            "--docs",
            help="Directory for local documents",
        ),
    ] = "",
) -> None:
    """
    Initialize workspace configuration.
    
    This command sets up the directories where code repositories and local documents
    will be stored and managed.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Workspace Configuration[/bold cyan]",
            border_style="cyan",
        )
    )

    # Load existing configuration
    config = load_config()
    
    # Get code workspace
    if not code_workspace:
        existing_code = config.get("code_workspace", "")
        if existing_code:
            console.print(f"[dim]Using existing code workspace: {existing_code}[/dim]")
            code_workspace = existing_code
        else:
            # Default to ~/dva-code-workspace
            default_code = str(Path.home() / "dva-code-workspace")
            code_workspace = Prompt.ask(
                "Enter code workspace directory",
                default=default_code
            )
    
    # Get docs workspace
    if not docs_workspace:
        existing_docs = config.get("docs_workspace", "")
        if existing_docs:
            console.print(f"[dim]Using existing docs workspace: {existing_docs}[/dim]")
            docs_workspace = existing_docs
        else:
            # Default to ~/dva-doc-workspace
            default_docs = str(Path.home() / "dva-doc-workspace")
            docs_workspace = Prompt.ask(
                "Enter docs workspace directory",
                default=default_docs
            )
    
    # Expand paths
    code_path = Path(code_workspace).expanduser().resolve()
    docs_path = Path(docs_workspace).expanduser().resolve()
    
    # Create directories if they don't exist
    console.print("\n[cyan]Creating workspace directories...[/cyan]")
    try:
        code_path.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Code workspace: {code_path}")
    except Exception as e:
        console.print(f"[red]✗ Failed to create code workspace: {e}[/red]")
        raise typer.Exit(1)
    
    try:
        docs_path.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Docs workspace: {docs_path}")
    except Exception as e:
        console.print(f"[red]✗ Failed to create docs workspace: {e}[/red]")
        raise typer.Exit(1)
    
    # Save configuration
    config["code_workspace"] = str(code_path)
    config["docs_workspace"] = str(docs_path)
    save_config(config)
    
    record_activity(
        command="init",
        subcommand="workspace",
        args={"code_workspace": str(code_path), "docs_workspace": str(docs_path)},
    )
    
    console.print(
        Panel.fit(
            f"[bold green]✓ Workspace configuration saved![/bold green]\n\n"
            f"[bold]Workspaces:[/bold]\n"
            f"  Code: {code_path}\n"
            f"  Docs: {docs_path}\n\n"
            f"[dim]Config saved to: {CONFIG_FILE}[/dim]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Configure LLM provider: {CLI_NAME} init vertex-ai\n"
            f"  2. Onboard code: {CLI_NAME} code onboard --path <repo>\n"
            f"  3. Ingest documents: {CLI_NAME} kg ingest submit --path <docs>",
            title="Success",
            border_style="green",
        )
    )


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


@init_app.command("devin")
def init_devin(
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="Devin API key — persisted to ~/.dva/.env (chmod 600)"),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Devin API base URL"),
    ] = None,
    max_acu: Annotated[
        int | None,
        typer.Option("--max-acu", help="Default per-session ACU ceiling"),
    ] = None,
    domain: Annotated[
        str | None,
        typer.Option("--domain", help="Configure per-domain defaults for this slug"),
    ] = None,
    snapshot_id: Annotated[
        str | None,
        typer.Option("--snapshot-id", help="Machine snapshot id for the domain"),
    ] = None,
    playbook_id: Annotated[
        str | None,
        typer.Option("--playbook-id", help="Playbook id for the domain"),
    ] = None,
    knowledge_folder: Annotated[
        str | None,
        typer.Option("--knowledge-folder", help="Devin folder name for the domain"),
    ] = None,
) -> None:
    """Initialize Devin Cloud configuration.

    Alias of ``dva devin init`` — kept here for consistency with the other
    provider init commands. Pass ``--api-key`` to persist the Devin API key to
    ``~/.dva/.env`` (chmod 600), the same store used for the other integration
    tokens; otherwise the key is read from ``$DEVIN_API_KEY``.
    """
    from agentic_cli.commands.devin import configure_devin
    from agentic_cli.env import mask, set_env_vars

    if api_key:
        path = set_env_vars({"DEVIN_API_KEY": api_key.strip()})
        console.print(f"[bold green]✓[/bold green] Saved DEVIN_API_KEY ({mask(api_key.strip())}) to {path}")

    configure_devin(
        base_url=base_url,
        max_acu=max_acu,
        domain=domain,
        snapshot_id=snapshot_id,
        playbook_id=playbook_id,
        knowledge_folder=knowledge_folder,
    )
    record_activity(
        command="init",
        subcommand="devin",
        args={"base_url": base_url, "max_acu": max_acu, "domain": domain,
              "api_key_set": bool(api_key)},
    )


@init_app.command("glean")
def init_glean(
    url: Annotated[str, typer.Option("--url", help="Glean instance URL, e.g. https://company-be.glean.com")] = "",
    token: Annotated[str, typer.Option("--token", help="Glean API token (token mode)")] = "",
    sso: Annotated[bool, typer.Option("--sso", help="Use SSO/OAuth instead of a static API token")] = False,
    issuer: Annotated[str, typer.Option("--issuer", help="OIDC issuer URL (sso mode)")] = "",
    client_id: Annotated[str, typer.Option("--client-id", help="OAuth client id (sso mode)")] = "",
) -> None:
    """Configure Glean (enterprise search / context), writing to ~/.dva/.env.

    Two auth modes:
      * token — set ``--url`` and ``--token`` (a Glean API token).
      * sso   — pass ``--sso`` with ``--url``, ``--issuer`` and ``--client-id``
                to authenticate via the org's SSO/OAuth (no static token).
    """
    from agentic_cli.env import mask, set_env_vars

    if not url.strip():
        console.print("[red]✗[/red] --url is required (the Glean instance URL).")
        raise typer.Exit(1)

    updates = {"GLEAN_API_URL": url.strip().rstrip("/")}
    if sso:
        if not (issuer.strip() and client_id.strip()):
            console.print("[red]✗[/red] SSO mode needs --issuer and --client-id.")
            raise typer.Exit(1)
        updates["GLEAN_AUTH_MODE"] = "sso"
        updates["GLEAN_OAUTH_ISSUER"] = issuer.strip()
        updates["GLEAN_OAUTH_CLIENT_ID"] = client_id.strip()
        detail = f"SSO via {issuer.strip()}"
    else:
        if not token.strip():
            console.print("[red]✗[/red] token mode needs --token (or pass --sso).")
            raise typer.Exit(1)
        updates["GLEAN_AUTH_MODE"] = "token"
        updates["GLEAN_API_TOKEN"] = token.strip()
        detail = f"API token {mask(token.strip())}"

    path = set_env_vars(updates)
    console.print(f"[bold green]✓[/bold green] Glean configured ({detail}) → {path}")
    record_activity(command="init", subcommand="glean",
                    args={"url": url.strip(), "mode": updates["GLEAN_AUTH_MODE"]})


# ---------------------------------------------------------------------------
# Integration credentials (.env — Jira / Confluence / Bitbucket)
#
# These live in ~/.dva/.env (loaded automatically at CLI startup) instead of
# being exported into the shell every session. See agentic_cli.env.
# ---------------------------------------------------------------------------

_INTEGRATIONS = {
    "jira": ("Jira", "JIRA_SERVER_URL", "JIRA_PERSONAL_ACCESS_TOKEN"),
    "confluence": ("Confluence", "CONFLUENCE_SERVER_URL", "CONFLUENCE_PERSONAL_ACCESS_TOKEN"),
    "bitbucket": ("Bitbucket", "BITBUCKET_SERVER_URL", "BITBUCKET_PERSONAL_ACCESS_TOKEN"),
}


def _configure_integration(name: str, url: str, token: str) -> None:
    """Write an integration's URL + token to ~/.dva/.env."""
    from agentic_cli.env import mask, set_env_vars

    label, url_env, token_env = _INTEGRATIONS[name]

    if not url:
        url = Prompt.ask(f"Enter {label} server URL (e.g. https://{name}.company.com)")
    if not token:
        token = Prompt.ask(f"Enter {label} personal access token", password=True)

    if not url or not token:
        console.print(f"[red]✗ Error:[/red] Both URL and token are required for {label}")
        raise typer.Exit(1)

    path = set_env_vars({url_env: url.rstrip("/"), token_env: token})

    record_activity(command="init", subcommand=name, args={"url": url})
    console.print(
        Panel.fit(
            f"[bold green]✓ {label} configured![/bold green]\n\n"
            f"  {url_env}: {url.rstrip('/')}\n"
            f"  {token_env}: {mask(token)}\n\n"
            f"[dim]Saved to: {path} (chmod 600)[/dim]\n"
            f"[dim]Loaded automatically on next {CLI_NAME} run — no shell export needed.[/dim]",
            title="Success",
            border_style="green",
        )
    )


@init_app.command("jira")
def init_jira(
    url: Annotated[str, typer.Option("--url", help="Jira server URL")] = "",
    token: Annotated[str, typer.Option("--token", help="Jira personal access token")] = "",
) -> None:
    """Configure Jira credentials (writes to ~/.dva/.env)."""
    _configure_integration("jira", url, token)


@init_app.command("confluence")
def init_confluence(
    url: Annotated[str, typer.Option("--url", help="Confluence server URL")] = "",
    token: Annotated[str, typer.Option("--token", help="Confluence personal access token")] = "",
) -> None:
    """Configure Confluence credentials (writes to ~/.dva/.env)."""
    _configure_integration("confluence", url, token)


@init_app.command("bitbucket")
def init_bitbucket(
    url: Annotated[str, typer.Option("--url", help="Bitbucket server URL")] = "",
    token: Annotated[str, typer.Option("--token", help="Bitbucket personal access token")] = "",
) -> None:
    """Configure Bitbucket credentials (writes to ~/.dva/.env)."""
    _configure_integration("bitbucket", url, token)


@init_app.command("env")
def init_env(
    scope: Annotated[
        str,
        typer.Option("--scope", help="Where to create .env: 'global' (~/.dva/.env) or 'project' (./.env)"),
    ] = "global",
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing .env")] = False,
) -> None:
    """Scaffold a .env file with all recognized integration/AI keys."""
    from agentic_cli.env import GLOBAL_ENV_PATH, resolved_env_files, scaffold_env

    if scope == "global":
        target = GLOBAL_ENV_PATH
    elif scope == "project":
        target = Path.cwd() / ".env"
    else:
        console.print(f"[red]✗[/red] Invalid --scope '{scope}' (use 'global' or 'project')")
        raise typer.Exit(1)

    created = scaffold_env(target, force=force)
    if not created:
        console.print(f"[yellow]⚠[/yellow] {target} already exists. Use --force to overwrite.")
    else:
        console.print(f"[green]✓[/green] Created {target} [dim](chmod 600)[/dim]")

    loaded = resolved_env_files()
    if loaded:
        console.print("\n[bold]Loaded .env files (low → high precedence):[/bold]")
        for f in loaded:
            console.print(f"  • {f}")
    console.print(
        f"\n[dim]Fill in tokens, or run: {CLI_NAME} init jira|confluence|bitbucket --url <> --token <>[/dim]\n"
        f"[dim]Validate anytime with: {CLI_NAME} doctor[/dim]"
    )


def get_google_config() -> dict:
    """Get Google configuration for use in other commands."""
    config = load_config()
    return config.get("google", {})
