"""Agent manifest (IR) — a declarative `agent.yaml` for an agent project.

This is the spine the Build surfaces read/write: the Project Canvas derives a
manifest from a project, and (with the "write manifest → confirm scaffold"
flow) can persist it back as `agent.yaml`. Deriving the manifest reuses the
same real sources as the canvas: discovered project metadata + installed
skills + the skills registry (for MCP bindings).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

API_VERSION = "agent/v1"
KIND = "AgentProject"
_DEFAULT_MODEL = "gemini-2.0-flash-001"


def _installed_skill_names(project: Path) -> List[str]:
    """Read installed skill names from the project's onboard manifest."""
    manifest = project / ".skills" / "onboard.json"
    if not manifest.exists():
        return []
    try:
        data = json.loads(manifest.read_text())
        return list(data.get("installed_skills", []))
    except (OSError, json.JSONDecodeError):
        return []


def _skill_mcp_map() -> Dict[str, str]:
    """Map skill name → MCP server from the registry (best-effort)."""
    try:
        from agentic_cli.analyzer.matcher import load_registry
        from agentic_cli.commands.code import _ensure_registry

        registry = load_registry(_ensure_registry())
        out: Dict[str, str] = {}
        for skill in registry.get("skills", []):
            mcp = skill.get("mcp") or {}
            server = mcp.get("server")
            if server:
                out[skill["name"]] = server
        return out
    except Exception:  # noqa: BLE001 - registry optional
        return {}


def build_manifest(path: str) -> Dict[str, Any]:
    """Derive an agent.yaml-shaped manifest for the project at ``path``."""
    project = Path(path).resolve()
    if not project.exists():
        raise FileNotFoundError(f"Project not found at {path}")

    # Reuse the dashboard's project discovery for real metadata.
    name = project.name
    framework: Optional[str] = None
    use_case: Optional[str] = None
    agent_type = "agent"
    domain: Optional[str] = None
    tools: List[str] = []
    try:
        from src.services.agent_service import discover_agent_projects, get_project_domain

        proj = next(
            (p for p in discover_agent_projects() if Path(p.path).resolve() == project),
            None,
        )
        if proj:
            name = proj.name
            framework = proj.framework
            use_case = proj.use_case
            agent_type = proj.agent_type or "agent"
            tools = list(proj.tools or [])
        domain = get_project_domain(str(project))
    except Exception:  # noqa: BLE001 - discovery optional; fall back to dir name
        pass

    # Skills + the MCP servers they bind.
    skill_names = _installed_skill_names(project)
    mcp_map = _skill_mcp_map()
    skills: List[Dict[str, Any]] = []
    mcp_servers: List[str] = []
    for sname in skill_names:
        entry: Dict[str, Any] = {"name": sname}
        server = mcp_map.get(sname)
        if server:
            entry["mcp"] = server
            if server not in mcp_servers:
                mcp_servers.append(server)
        skills.append(entry)

    # `memory` is a tool but modeled as its own ingredient.
    has_memory = any("memory" in t.lower() for t in tools)
    plain_tools = [t for t in tools if "memory" not in t.lower()]

    return {
        "apiVersion": API_VERSION,
        "kind": KIND,
        "metadata": {k: v for k, v in {"name": name, "domain": domain}.items() if v},
        "spec": {
            "agent": {
                k: v
                for k, v in {
                    "type": agent_type,
                    "framework": framework,
                    "useCase": use_case,
                    "model": _DEFAULT_MODEL,
                }.items()
                if v
            },
            "model": _DEFAULT_MODEL,
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
    except Exception:  # noqa: BLE001 - degrade to JSON rather than fail
        return json.dumps(manifest, indent=2)


def write_manifest(path: str, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Write ``agent.yaml`` into the project. Non-destructive: only touches the
    manifest file, never regenerates project code."""
    project = Path(path).resolve()
    if not project.exists() or not project.is_dir():
        raise FileNotFoundError(f"Project directory not found at {path}")

    data = manifest or build_manifest(path)
    target = project / "agent.yaml"
    target.write_text(manifest_to_yaml(data))
    return {"written": True, "file": str(target)}
