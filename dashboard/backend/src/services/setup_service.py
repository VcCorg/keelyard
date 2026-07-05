"""CLI setup/config status — reports which `dva init` steps are done.

Many dashboard workflows (onboarding, KG ingest/export, OKF enrich, agents)
require the CLI to be initialized first:

  - workspaces   `dva init workspace`   (code + docs directories)
  - vertex_ai    `dva init vertex-ai`   (LLM / embeddings provider)
  - neo4j        `dva kg init`           (graph DB for KG ingest/export)
  - devin        $DEVIN_API_KEY          (optional — Devin Cloud push)

This service reads the same config the CLI uses (single source of truth) and
exposes a status the dashboard surfaces in the sidebar + as per-feature
validation banners. Mutations are performed by shelling out to the real
`dva init ...` so all setup logic lives in exactly one place.
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Optional

from pydantic import BaseModel


class SetupItem(BaseModel):
    key: str                 # workspaces | vertex_ai | neo4j | devin
    label: str
    configured: bool
    required: bool           # blocks core workflows when False
    detail: str = ""
    fix_hint: str = ""


class SetupStatus(BaseModel):
    cli_available: bool
    cli_version: str = ""
    ready: bool              # every REQUIRED item is configured
    items: list[SetupItem] = []

    def item(self, key: str) -> Optional[SetupItem]:
        return next((i for i in self.items if i.key == key), None)


def resolve_cli_command() -> list[str]:
    dva = shutil.which("dva")
    if dva:
        return [dva]
    return [sys.executable, "-m", "agentic_cli.main"]


def _cli_available() -> tuple[bool, str]:
    if shutil.which("dva"):
        try:
            from agentic_cli import __version__  # type: ignore
            return True, str(__version__)
        except Exception:
            return True, ""
    # Fallback: importable as a module even if the alias is absent.
    try:
        import agentic_cli  # noqa: F401
        return True, getattr(agentic_cli, "__version__", "")
    except Exception:
        return False, ""


def _main_config() -> dict:
    """Load the shared CLI config (~/.agent-cli-agentic/config.json)."""
    try:
        from agentic_cli.commands.code import _get_config
        return _get_config() or {}
    except Exception:
        try:
            import json
            from pathlib import Path
            p = Path.home() / ".agent-cli-agentic" / "config.json"
            return json.loads(p.read_text()) if p.exists() else {}
        except Exception:
            return {}


def _integration_item(
    key: str,
    label: str,
    url_env: str,
    token_env: str,
    extra_env: Optional[str] = None,
) -> SetupItem:
    """Build an env-only setup item for a PAT-based integration.

    Like the Devin item, nothing is persisted to disk — credentials are read
    from the backend's environment. ``configured`` requires both the server
    URL and the personal access token to be present, matching what the MCP
    services and dashboard services expect.
    """
    url = os.environ.get(url_env, "").strip()
    token = os.environ.get(token_env, "").strip()
    configured = bool(url and token)

    if configured:
        detail = f"{url_env} + token set ({url})"
    elif url and not token:
        detail = f"{url_env} set — {token_env} missing"
    elif token and not url:
        detail = f"{token_env} set — {url_env} missing"
    else:
        detail = f"Set {url_env} and {token_env} on the backend environment"

    hint = f"dva init {key} --url <url> --token <pat>"
    if extra_env:
        hint += f"  (optional: {extra_env})"

    return SetupItem(
        key=key, label=label, configured=configured, required=False,
        detail=detail, fix_hint=hint,
    )


def get_setup_status() -> SetupStatus:
    # Re-read ~/.dva/.env so tokens written via the setup panel are reflected
    # without restarting the backend (real exports still take precedence).
    try:
        from agentic_cli.env import load_env
        load_env(force=True)
    except Exception:
        pass

    cli_available, cli_version = _cli_available()
    cfg = _main_config()

    code_ws = cfg.get("code_workspace")
    docs_ws = cfg.get("docs_workspace")
    workspaces_ok = bool(code_ws and docs_ws)

    google = cfg.get("google") or cfg.get("vertex_ai") or {}
    vertex_ok = bool(google.get("project_id"))

    try:
        from agentic_cli.kg.config import KGConfig
        neo4j_ok = KGConfig.load().is_neo4j_configured()
    except Exception:
        neo4j_ok = False

    devin_ok = bool(os.environ.get("DEVIN_API_KEY"))

    items = [
        SetupItem(
            key="workspaces", label="Workspaces", configured=workspaces_ok, required=True,
            detail=(f"code: {code_ws}" if workspaces_ok else "Code & docs directories not set"),
            fix_hint="dva init workspace --code <dir> --docs <dir>",
        ),
        SetupItem(
            key="vertex_ai", label="Vertex AI (LLM)", configured=vertex_ok, required=True,
            detail=(f"project: {google.get('project_id')}" if vertex_ok else "Google Cloud project not set"),
            fix_hint="dva init vertex-ai --project-id <id> --location <region>",
        ),
        SetupItem(
            key="neo4j", label="Knowledge Graph (Neo4j)", configured=neo4j_ok, required=False,
            detail=("configured" if neo4j_ok else "Required for KG ingest / OKF export"),
            fix_hint="dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password <pwd>",
        ),
        SetupItem(
            key="devin", label="Devin Cloud (optional)", configured=devin_ok, required=False,
            detail=("$DEVIN_API_KEY present" if devin_ok else "Set $DEVIN_API_KEY for Devin push"),
            fix_hint="export DEVIN_API_KEY=<key>  (backend environment)",
        ),
        _integration_item(
            key="jira", label="Jira (Work Items)",
            url_env="JIRA_SERVER_URL", token_env="JIRA_PERSONAL_ACCESS_TOKEN",
            extra_env="JIRA_DEFAULT_PROJECT",
        ),
        _integration_item(
            key="bitbucket", label="Bitbucket (Repos / PRs)",
            url_env="BITBUCKET_SERVER_URL", token_env="BITBUCKET_PERSONAL_ACCESS_TOKEN",
            extra_env="BITBUCKET_DEFAULT_PROJECT",
        ),
        _integration_item(
            key="confluence", label="Confluence (Docs)",
            url_env="CONFLUENCE_SERVER_URL", token_env="CONFLUENCE_PERSONAL_ACCESS_TOKEN",
            extra_env="CONFLUENCE_DEFAULT_SPACE",
        ),
    ]
    ready = cli_available and all(i.configured for i in items if i.required)
    return SetupStatus(cli_available=cli_available, cli_version=cli_version, ready=ready, items=items)


# ── Init arg builders (non-interactive: every value passed as a flag) ────────

def init_workspace_args(code: str, docs: str) -> list[str]:
    return ["init", "workspace", "--code", code, "--docs", docs]


def init_vertex_args(project_id: str, location: str = "us-central1", model: str = "") -> list[str]:
    # --skip-auth: gcloud ADC login is interactive; the user runs it in the
    # Terminal page. We persist the project/location/model here non-interactively.
    args = ["init", "vertex-ai", "--project-id", project_id, "--location", location, "--skip-auth"]
    if model:
        args += ["--model", model]
    return args


def kg_init_neo4j_args(uri: str, username: str, password: str) -> list[str]:
    return ["kg", "init", "--provider", "neo4j", "--uri", uri,
            "--username", username, "--password", password]


# ── Integration credential writers (persist to ~/.dva/.env via the CLI) ──────

_INTEGRATION_KEYS = {"jira", "bitbucket", "confluence"}


def init_integration_args(kind: str, url: str, token: str) -> list[str]:
    """Build `dva init <kind> --url <> --token <>` for Jira/Bitbucket/Confluence.

    The CLI writes the credentials to ~/.dva/.env (chmod 600); no shell export
    is needed. Raises ValueError for an unknown integration kind.
    """
    if kind not in _INTEGRATION_KEYS:
        raise ValueError(f"Unknown integration: {kind}")
    return ["init", kind, "--url", url, "--token", token]
