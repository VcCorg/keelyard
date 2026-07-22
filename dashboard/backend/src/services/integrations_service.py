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


class IntegrationStatus(BaseModel):
    key: str
    label: str
    status: Status = "unknown"
    detail: str = ""
    hint: str = ""


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


def get_integrations() -> IntegrationsResponse:
    """gcloud covers Gemini/Vertex (ADC), so no separate Gemini chip."""
    return IntegrationsResponse(
        integrations=[
            _backend_status(),
            _gcloud_status(),
            _devin_status(),
            _mcp_status(),
        ]
    )
