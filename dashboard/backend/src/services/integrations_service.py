"""Integration status aggregator.

Surfaces a quick health snapshot of everything the dashboard depends on —
the backend itself, the Devin API key, Google Cloud auth (gcloud / ADC),
the Gemini key used by Chat, and the MCP server fleet — so the UI can render
status icons without each page re-implementing the checks.

Every probe is defensive: failures degrade to a status rather than raising,
and external calls (gcloud) are run with a short timeout.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

Status = Literal["ok", "warn", "error", "unknown"]

#: Which shelf an integration sits on. "platform" is what the app needs to work
#: and belongs in the always-visible status bar; "optional" is something a user
#: chose to connect, which is a red dot nobody should have to look at all day.
#:
#: A field rather than a hardcoded key list in the frontend: a list there means
#: the next integration added here silently fails to render anywhere.
Group = Literal["platform", "optional"]


class IntegrationStatus(BaseModel):
    key: str
    label: str
    status: Status = "unknown"
    detail: str = ""
    hint: str = ""
    group: Group = "platform"
    docs_command: str = ""


class IntegrationsResponse(BaseModel):
    integrations: list[IntegrationStatus]


# ── Individual probes ────────────────────────────────────────────────────────

def _backend_status() -> IntegrationStatus:
    return IntegrationStatus(
        key="backend",
        label="Backend",
        status="ok",
        detail="API responding (v0.1.0)",
    )


def _devin_status() -> IntegrationStatus:
    try:
        from src.services.devin_service import get_status

        s = get_status()
        if s.api_key_present:
            return IntegrationStatus(
                key="devin",
                label="Devin",
                status="ok",
                detail=f"Connected · {s.base_url}",
            )
        return IntegrationStatus(
            key="devin",
            label="Devin",
            status="warn",
            detail="No API key — dry-run only",
            hint="Set DEVIN_API_KEY on the backend to enable live sessions.",
        )
    except Exception as exc:  # noqa: BLE001
        return IntegrationStatus(
            key="devin", label="Devin", status="error", detail=str(exc)[:200]
        )


def _gcloud_status() -> IntegrationStatus:
    """Active gcloud account + project, used for Vertex/Gemini ADC."""
    gcloud = shutil.which("gcloud")
    if not gcloud:
        return IntegrationStatus(
            key="gcloud",
            label="gcloud",
            status="unknown",
            detail="gcloud CLI not found",
            hint="Install the Google Cloud SDK to enable Vertex auth.",
        )
    try:
        out = subprocess.run(
            [gcloud, "auth", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        accounts = json.loads(out.stdout or "[]")
        active = next((a.get("account") for a in accounts if a.get("status") == "ACTIVE"), None)
    except Exception as exc:  # noqa: BLE001
        return IntegrationStatus(
            key="gcloud", label="gcloud", status="error", detail=str(exc)[:200]
        )

    if not active:
        return IntegrationStatus(
            key="gcloud",
            label="gcloud",
            status="error",
            detail="No active account",
            hint="Run `gcloud auth login` and `gcloud auth application-default login`.",
        )

    project = ""
    try:
        proj = subprocess.run(
            [gcloud, "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        project = (proj.stdout or "").strip()
        if project in {"(unset)", ""}:
            project = ""
    except Exception:  # noqa: BLE001
        project = ""

    # Application Default Credentials are what the SDKs actually use.
    adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    adc_present = adc_path.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

    detail = active + (f" · {project}" if project else "")
    if not adc_present:
        return IntegrationStatus(
            key="gcloud",
            label="gcloud",
            status="warn",
            detail=f"{detail} (no ADC)",
            hint="Run `gcloud auth application-default login` for SDK access.",
        )
    return IntegrationStatus(key="gcloud", label="gcloud", status="ok", detail=detail)


def _mcp_status() -> IntegrationStatus:
    try:
        from src.services.mcp_service import check_health

        results = check_health()
        total = len(results)
        healthy = sum(1 for r in results if r.healthy)
        if total == 0:
            return IntegrationStatus(
                key="mcp",
                label="MCP",
                status="unknown",
                detail="No servers configured",
            )
        if healthy == total:
            status: Status = "ok"
        elif healthy == 0:
            status = "error"
        else:
            status = "warn"
        return IntegrationStatus(
            key="mcp",
            label="MCP",
            status=status,
            detail=f"{healthy}/{total} healthy",
        )
    except Exception as exc:  # noqa: BLE001
        return IntegrationStatus(
            key="mcp", label="MCP", status="error", detail=str(exc)[:200]
        )


def _hub_status(hub: str, label: str) -> IntegrationStatus:
    """Kaggle / Hugging Face, reported as three separable facts.

    A hub is usable when both a credential and its client are present, and the
    two fail differently: no credential is something the user fixes in a minute,
    a missing SDK is an install. Collapsing them into one red dot would send
    people to the wrong fix, so the status names which half is absent.

    Nothing here reads a credential *value* — the CLI detects where the
    credential lives and never copies it, and a status endpoint is the last
    place that should be the exception.
    """
    command = f"keel init {hub}"
    try:
        from agentic_cli import hubs

        credential = (hubs.kaggle_credential() if hub == hubs.KAGGLE
                      else hubs.huggingface_credential())
        sdk = hubs.sdk_available(hub)
    except Exception as exc:  # noqa: BLE001
        return IntegrationStatus(key=hub, label=label, status="unknown",
                                 detail=str(exc)[:200], group="optional",
                                 docs_command=command)

    account = f" · {credential.account}" if credential.account else ""
    if credential.available and sdk:
        return IntegrationStatus(key=hub, label=label, status="ok",
                                 detail=f"Ready{account}", group="optional",
                                 docs_command=command)
    if credential.available:
        return IntegrationStatus(
            key=hub, label=label, status="warn",
            detail=f"Client not installed{account}",
            hint="pip install 'agentic-cli[hubs]' to enable fetches.",
            group="optional", docs_command="pip install 'agentic-cli[hubs]'",
        )
    if sdk:
        return IntegrationStatus(
            key=hub, label=label, status="warn",
            detail="No credential",
            hint=f"Run `{command}` after authenticating with the hub's own CLI.",
            group="optional", docs_command=command,
        )
    return IntegrationStatus(
        key=hub, label=label, status="unknown",
        detail="Not configured",
        hint=f"Optional. `{command}` reports what is missing.",
        group="optional", docs_command=command,
    )


def get_integrations() -> IntegrationsResponse:
    """gcloud covers Gemini/Vertex (ADC), so no separate Gemini chip."""
    return IntegrationsResponse(
        integrations=[
            _backend_status(),
            _gcloud_status(),
            _devin_status(),
            _mcp_status(),
            _hub_status("huggingface", "Hugging Face"),
            _hub_status("kaggle", "Kaggle"),
        ]
    )
