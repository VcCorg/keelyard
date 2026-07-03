"""Agent manifest (IR) — thin dashboard delegation to the CLI.

The manifest is the platform spine and its logic is the CLI's source of truth
(``agentic_cli.manifest``). The dashboard does not reimplement it: it calls the
CLI and tags writes with ``source="dashboard"`` so the CLI's central audit
trail records where the action originated. This keeps the dashboard a lens over
the CLI rather than a parallel engine.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_manifest(path: str) -> Dict[str, Any]:
    """Derive the agent.yaml manifest for a project (delegates to the CLI)."""
    from agentic_cli.manifest import build_manifest as _build

    return _build(path)


def manifest_to_yaml(manifest: Dict[str, Any]) -> str:
    """Serialize a manifest to YAML (delegates to the CLI)."""
    from agentic_cli.manifest import manifest_to_yaml as _to_yaml

    return _to_yaml(manifest)


def write_manifest(path: str, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Write agent.yaml via the CLI, auditing the action as dashboard-sourced."""
    from agentic_cli.manifest import write_manifest as _write

    return _write(path, manifest, source="dashboard")
