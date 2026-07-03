"""Agent manifest (IR) — the canonical ``agent.yaml`` for an agent project.

This is the platform spine: a declarative description of an agent project
(metadata + runtime/model + tools + skills + MCP bindings + memory). It lives
in the CLI so the CLI is the single source of truth — the dashboard and any
other surface derive/write manifests by calling here, and every write is
recorded in the central audit trail.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

API_VERSION = "agent/v1"
KIND = "AgentProject"
DEFAULT_MODEL = "gemini-2.0-flash-001"


def _installed_skill_names(project: Path) -> List[str]:
    manifest = project / ".skills" / "onboard.json"
    if not manifest.exists():
        return []
    try:
        return list(json.loads(manifest.read_text()).get("installed_skills", []))
    except (OSError, json.JSONDecodeError):
        return []


def _skill_mcp_map() -> Dict[str, str]:
    """Map skill name → MCP server from the configured registry (best-effort)."""
    try:
        from agentic_cli.analyzer.matcher import load_registry
        from agentic_cli.commands.code import _ensure_registry

        registry = load_registry(_ensure_registry())
        out: Dict[str, str] = {}
        for skill in registry.get("skills", []):
            server = (skill.get("mcp") or {}).get("server")
            if server:
                out[skill["name"]] = server
        return out
    except Exception:  # noqa: BLE001 - registry optional
        return {}


def _project_meta(path: Path) -> Dict[str, Any]:
    """Pull real project metadata from the tracker, falling back to the dir."""
    meta: Dict[str, Any] = {
        "name": path.name,
        "framework": None,
        "use_case": None,
        "agent_type": "agent",
        "domain": None,
        "tools": [],
    }
    try:
        from agentic_cli.tracker import get_projects

        for row in get_projects():
            if Path(row.get("path", "")).resolve() == path:
                tools = row.get("tools") or []
                if isinstance(tools, str):
                    tools = json.loads(tools)
                meta.update(
                    name=row.get("name") or path.name,
                    framework=row.get("framework"),
                    use_case=row.get("use_case"),
                    domain=row.get("domain"),
                    tools=list(tools),
                )
                break
    except Exception:  # noqa: BLE001 - tracker optional
        pass
    return meta


def build_manifest(path: str) -> Dict[str, Any]:
    """Derive the agent.yaml manifest for the project at ``path``."""
    project = Path(path).resolve()
    if not project.exists():
        raise FileNotFoundError(f"Project not found at {path}")

    meta = _project_meta(project)
    mcp_map = _skill_mcp_map()

    skills: List[Dict[str, Any]] = []
    mcp_servers: List[str] = []
    for sname in _installed_skill_names(project):
        entry: Dict[str, Any] = {"name": sname}
        server = mcp_map.get(sname)
        if server:
            entry["mcp"] = server
            if server not in mcp_servers:
                mcp_servers.append(server)
        skills.append(entry)

    tools = meta["tools"]
    has_memory = any("memory" in t.lower() for t in tools)
    plain_tools = [t for t in tools if "memory" not in t.lower()]

    agent = {
        k: v
        for k, v in {
            "type": meta["agent_type"],
            "framework": meta["framework"],
            "useCase": meta["use_case"],
            "model": DEFAULT_MODEL,
        }.items()
        if v
    }

    return {
        "apiVersion": API_VERSION,
        "kind": KIND,
        "metadata": {k: v for k, v in {"name": meta["name"], "domain": meta["domain"]}.items() if v},
        "spec": {
            "agent": agent,
            "model": DEFAULT_MODEL,
            "tools": plain_tools,
            "skills": skills,
            "mcpServers": mcp_servers,
            "retrievers": [],
            "memory": has_memory,
        },
    }


def manifest_to_yaml(manifest: Dict[str, Any]) -> str:
    """Serialize a manifest to YAML (falls back to JSON if PyYAML is absent)."""
    try:
        import yaml

        return yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False)
    except Exception:  # noqa: BLE001
        return json.dumps(manifest, indent=2)


def write_manifest(
    path: str,
    manifest: Optional[Dict[str, Any]] = None,
    *,
    source: str = "cli",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Write ``agent.yaml`` into the project and audit the action.

    Non-destructive: only the manifest file is written, never project code.
    """
    project = Path(path).resolve()
    if not project.exists() or not project.is_dir():
        raise FileNotFoundError(f"Project directory not found at {path}")

    data = manifest or build_manifest(path)
    target = project / "agent.yaml"
    target.write_text(manifest_to_yaml(data))

    # Central audit trail — the CLI is the auditor for every surface.
    try:
        from agentic_cli.tracker import record_action

        record_action(
            "project",
            "manifest",
            entity_type="project",
            entity_id=str(project),
            correlation_id=correlation_id,
            source=source,
            details={"file": str(target), "skills": len(data.get("spec", {}).get("skills", []))},
        )
    except Exception:  # noqa: BLE001 - never break on audit
        pass

    return {"written": True, "file": str(target)}
