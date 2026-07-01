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


def get_setup_status() -> SetupStatus:
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
