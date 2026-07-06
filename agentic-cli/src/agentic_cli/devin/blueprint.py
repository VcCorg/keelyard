"""Devin DRS blueprint generation for per-domain machine snapshots.

This implements the *blueprint-now, build-later* model:

- :func:`write_domain_blueprint` renders a self-contained Devin DRS blueprint
  (``.devin/environment.yaml`` + ``.devin/setup.sh``) into a domain meta-repo
  during onboarding. This step is deterministic and has **no** cloud/network
  dependency — it just commits files that describe how to build the snapshot.
- Later, ``keel domain build-snapshot <slug>`` shells out to the ``devin`` DRS
  CLI to actually build the snapshot from this blueprint and persists the
  resulting ``snapshot_id`` per-domain via :class:`DevinConfig`.

Why a snapshot? A Devin **Sessions-API** run only sees context delivered in its
payload (``snapshot_id``/``playbook_id``/``knowledge_ids``/``prompt``); it does
not read a repo's ``.devin/skills`` or ``.windsurf/rules`` on its own. Baking the
domain meta-repo (submodules + ``.platform/config`` governance + persona skills +
graph + MCP wiring) into a snapshot is what lets every session for the domain
start from the *same* governance-consistent environment.

The ``environment.yaml`` schema here is intentionally simple and self-describing.
The exact DRS schema can vary by Devin version, so the build command is kept
configurable (see :func:`build_command`) and the blueprint doubles as
human-readable documentation of the intended environment.
"""
from __future__ import annotations

import json
import re
import stat
from pathlib import Path
from typing import Any, Optional

import yaml

# Standard MCP servers wired into a domain session. Mirrors the workspace
# ``.devin/mcp_config.json`` defaults; used as a fallback when no workspace
# config is discoverable.
DEFAULT_MCP_SERVERS: list[dict[str, Any]] = [
    {"name": "bitbucket", "transport": "sse", "url": "http://localhost:8126/sse"},
    {"name": "jira", "transport": "sse", "url": "http://localhost:8128/sse"},
    {"name": "confluence", "transport": "sse", "url": "http://localhost:8129/sse"},
    {"name": "memory", "transport": "sse", "url": "http://localhost:8130/sse"},
    {"name": "kg", "transport": "sse", "url": "http://localhost:8131/sse"},
    {"name": "agentic", "transport": "sse", "url": "http://localhost:8132/sse"},
]

BLUEPRINT_DIR = ".devin"
ENVIRONMENT_FILE = "environment.yaml"
SETUP_FILE = "setup.sh"


def snapshot_name(domain: str) -> str:
    """Deterministic, stable snapshot/blueprint name for a domain."""
    return f"{domain}-domain"


def load_workspace_mcp_servers(start: Optional[Path] = None) -> Optional[list[dict[str, Any]]]:
    """Discover MCP servers from a nearby ``.devin/mcp_config.json``.

    Walks up from ``start`` (default: cwd) looking for ``.devin/mcp_config.json``
    and normalizes it into the blueprint's ``mcp_servers`` shape. Returns ``None``
    if no config is found so the caller can fall back to :data:`DEFAULT_MCP_SERVERS`.
    """
    here = (start or Path.cwd()).resolve()
    for base in [here, *here.parents]:
        cfg = base / BLUEPRINT_DIR / "mcp_config.json"
        if cfg.exists():
            try:
                raw = json.loads(cfg.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
            servers: list[dict[str, Any]] = []
            for name, spec in (raw.get("mcpServers") or {}).items():
                if spec.get("disabled"):
                    continue
                url = spec.get("url") or spec.get("serverUrl")
                if not url:
                    continue
                servers.append({
                    "name": name,
                    "transport": spec.get("transport", "sse"),
                    "url": url,
                })
            return servers or None
    return None


def render_environment_yaml(
    domain: str,
    product: str,
    meta_repo_name: str,
    *,
    code_assist_tool: str = "generic",
    mcp_servers: Optional[list[dict[str, Any]]] = None,
) -> str:
    """Render the ``.devin/environment.yaml`` DRS blueprint as a YAML string."""
    blueprint: dict[str, Any] = {
        "apiVersion": "devin.ai/v1",
        "kind": "Blueprint",
        "metadata": {
            "name": snapshot_name(domain),
            "domain": domain,
            "product": product,
            "tier": "domain",
            "meta_repo": meta_repo_name,
            "generated_by": "keel domain init-meta",
        },
        # The setup script is baked into the snapshot so every session starts
        # from the same governance-consistent environment.
        "setup": {
            "script": f"{BLUEPRINT_DIR}/{SETUP_FILE}",
            "code_assist_tool": code_assist_tool,
        },
        "mcp_servers": mcp_servers if mcp_servers is not None else DEFAULT_MCP_SERVERS,
        # Where the governance floor and persona skills live, and where the
        # setup script propagates them so the agent reads them as files.
        "governance": {
            "source": ".platform/config/governance.yaml",
            "personas": ".agents/skills/personas",
            "propagate_to": [".windsurf/rules/", f"{BLUEPRINT_DIR}/skills/"],
        },
    }
    header = (
        f"# Devin DRS blueprint — {domain} domain (domain / tech-lead tier).\n"
        "# Generated by `keel domain init-meta` (blueprint-now, build-later model).\n"
        f"# Build a snapshot from this with: keel domain build-snapshot {domain}\n"
        "#\n"
        "# This describes the environment baked into the per-domain snapshot so\n"
        "# every Devin session for the domain starts governance-consistent.\n"
        "#\n"
        "# NOTE: The exact key schema Devin DRS expects in environment.yaml is not\n"
        "# published offline; the fields below are a documented intent. Validate\n"
        "# against your org with: devin cloud drs blueprint-create --from-file <this>\n"
        "# (adjust keys as needed, then `keel domain gen-blueprint` can be updated).\n\n"
    )
    return header + yaml.safe_dump(blueprint, sort_keys=False, default_flow_style=False)


def render_setup_script(domain: str, *, code_assist_tool: str = "generic") -> str:
    """Render the ``.devin/setup.sh`` baked into the snapshot.

    Steps:
      1. Fetch submodule working trees (linked repos + context repo + product meta).
      2. Propagate the governance floor + persona skills into agent-readable
         locations (``.windsurf/rules`` and ``.devin/skills``).
      3. Best-effort knowledge-graph refresh via ``graphify`` if available.
    """
    return f"""#!/usr/bin/env bash
# Devin DRS snapshot setup for the {domain} domain.
# Baked into the snapshot so every session starts from the same environment.
set -euo pipefail

echo "[devin-setup] Initializing {domain} domain environment..."

# 1) Fetch submodules (linked repos + domain-context + product-meta).
if [ -f Makefile ]; then
  make init || git submodule update --init --recursive --depth 1 --jobs 8 || true
else
  git submodule update --init --recursive --depth 1 --jobs 8 || true
fi

# 2) Propagate the governance floor + persona skills so the agent reads them
#    as files (Sessions API does not auto-read repo skills/rules).
mkdir -p .windsurf/rules {BLUEPRINT_DIR}/skills

if [ -f .platform/config/governance.yaml ]; then
  {{
    echo "# {domain} — Governance floor (advisory)"
    echo ""
    echo '```yaml'
    cat .platform/config/governance.yaml
    echo '```'
  }} > .windsurf/rules/governance.md
  echo "[devin-setup] Propagated governance.yaml -> .windsurf/rules/governance.md"
fi

if [ -d .agents/skills/personas ]; then
  for skill in .agents/skills/personas/*/SKILL.md; do
    [ -f "$skill" ] || continue
    pid="$(basename "$(dirname "$skill")")"
    mkdir -p "{BLUEPRINT_DIR}/skills/$pid"
    cp "$skill" "{BLUEPRINT_DIR}/skills/$pid/SKILL.md"
  done
  echo "[devin-setup] Installed persona skills -> {BLUEPRINT_DIR}/skills/"
fi

# 3) Best-effort knowledge-graph refresh (no-op if graphify is unavailable).
if command -v graphify >/dev/null 2>&1; then
  graphify update || true
fi

echo "[devin-setup] Done."
"""


def write_domain_blueprint(
    meta_repo_path: Path,
    domain: str,
    product: str,
    *,
    code_assist_tool: str = "generic",
    mcp_servers: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Path]:
    """Write ``.devin/environment.yaml`` + ``.devin/setup.sh`` into a meta-repo.

    Returns a mapping of logical name -> path for the files written.
    """
    blueprint_dir = meta_repo_path / BLUEPRINT_DIR
    blueprint_dir.mkdir(parents=True, exist_ok=True)

    env_path = blueprint_dir / ENVIRONMENT_FILE
    env_path.write_text(
        render_environment_yaml(
            domain,
            product,
            meta_repo_path.name,
            code_assist_tool=code_assist_tool,
            mcp_servers=mcp_servers,
        ),
        encoding="utf-8",
    )

    setup_path = blueprint_dir / SETUP_FILE
    setup_path.write_text(
        render_setup_script(domain, code_assist_tool=code_assist_tool),
        encoding="utf-8",
    )
    try:
        setup_path.chmod(setup_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass

    return {"environment": env_path, "setup": setup_path}


# ── Devin DRS command surface ────────────────────────────────────────────────
# Verified against `devin cloud drs --help` (devin 2026.5.26). The DRS model is:
#   1. A blueprint holds an environment.yaml, scoped to a repo (or org-wide).
#   2. `blueprint-create --from-file` seeds a new blueprint (optionally --repo).
#   3. `blueprint-write --blueprint-id --from-file` replaces an existing one.
#   4. `build` (NO args) builds ALL current blueprints and polls to completion.
# There is no per-build `--file`/`--name`; the file is attached to a blueprint.
DRS_BASE = ["devin", "cloud", "drs"]


def blueprint_create_command(env_file: Path, repo: Optional[str] = None) -> list[str]:
    """`devin cloud drs blueprint-create [--repo <owner/repo>] --from-file <yaml>`."""
    cmd = [*DRS_BASE, "blueprint-create"]
    if repo:
        cmd += ["--repo", repo]
    cmd += ["--from-file", str(env_file)]
    return cmd


def blueprint_write_command(blueprint_id: str, env_file: Path) -> list[str]:
    """`devin cloud drs blueprint-write --blueprint-id <id> --from-file <yaml>`."""
    return [*DRS_BASE, "blueprint-write", "--blueprint-id", blueprint_id,
            "--from-file", str(env_file)]


def build_command() -> list[str]:
    """`devin cloud drs build` — builds all current blueprints and waits.

    Takes no arguments by design (verified against the CLI help); the per-domain
    environment.yaml is attached to a blueprint via create/write beforehand.
    """
    return [*DRS_BASE, "build"]


# Best-effort id extraction from DRS output. The exact field names are
# auth-gated (could not run live), so we match several plausible shapes:
#   blueprint_id: bp-abc | "blueprint_id":"bp-abc"
#   snapshot_id: snap-abc | snapshot abc
_BLUEPRINT_ID_RE = re.compile(
    r"""blueprint[ _-]?id["']?\s*[:=]\s*["']?([A-Za-z0-9][A-Za-z0-9_-]{3,})""",
    re.IGNORECASE,
)
_SNAPSHOT_ID_RE = re.compile(
    r"""(?:snapshot|snap)[ _-]?id["']?\s*[:=]\s*["']?([A-Za-z0-9][A-Za-z0-9_-]{3,})""",
    re.IGNORECASE,
)


def parse_blueprint_id(output: str) -> Optional[str]:
    """Extract a blueprint id from `blueprint-create` output (best-effort)."""
    m = _BLUEPRINT_ID_RE.search(output or "")
    return m.group(1) if m else None


def parse_snapshot_id(output: str) -> Optional[str]:
    """Extract a snapshot id from DRS build output (best-effort)."""
    m = _SNAPSHOT_ID_RE.search(output or "")
    return m.group(1) if m else None
