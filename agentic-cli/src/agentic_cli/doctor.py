"""Preflight diagnostics for the Agentic CLI.

`{CLI_NAME} doctor` validates the local environment so users get actionable
guidance before hitting cryptic runtime failures. It checks:

  - Python runtime
  - Skills registry configuration (needed for `code onboard`)
  - Integration credentials (Bitbucket / Jira / Confluence via env vars)
  - MCP server reachability (the CLI routes API calls through MCP servers)
  - Knowledge Graph provider + connection
  - Optional tooling (Devin API key, Docker)

Nothing here mutates state; it is safe to run anytime.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table

from agentic_cli.config import CLI_NAME

console = Console()

# Status constants
OK = "ok"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"

_SYMBOL = {
    OK: "[green]\u2714[/green]",
    WARN: "[yellow]\u26a0[/yellow]",
    FAIL: "[red]\u2717[/red]",
    SKIP: "[dim]\u2014[/dim]",
}

AGENT_CONFIG_FILE = Path.home() / ".agent-cli-agentic" / "config.json"


@dataclass
class CheckResult:
    """Outcome of a single diagnostic check."""

    group: str
    name: str
    status: str
    detail: str = ""
    fix: str = ""


@dataclass
class Section:
    """A named group of checks; `required` controls exit-code impact."""

    name: str
    required: bool = False
    results: List[CheckResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _host_port(url: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else default_port)
    return host, port


def _tcp_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def _load_agent_config() -> dict:
    if AGENT_CONFIG_FILE.exists():
        try:
            return json.loads(AGENT_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# ---------------------------------------------------------------------------
# Individual check groups
# ---------------------------------------------------------------------------

def _check_runtime() -> Section:
    sec = Section("Runtime", required=True)
    v = sys.version_info
    if v >= (3, 10):
        sec.results.append(CheckResult(
            "Runtime", "Python version", OK, f"Python {v.major}.{v.minor}.{v.micro}"))
    else:
        sec.results.append(CheckResult(
            "Runtime", "Python version", FAIL,
            f"Python {v.major}.{v.minor} detected",
            fix="Use Python 3.10+ (the project targets 3.12)."))
    return sec


def _check_registry() -> Section:
    sec = Section("Skills registry", required=True)
    cfg = _load_agent_config()
    registry = cfg.get("skills_registry") or os.environ.get("DVA_SKILLS_REGISTRY", "")

    if not registry:
        sec.results.append(CheckResult(
            "Skills registry", "Configured", WARN,
            "No skills registry configured",
            fix=f"Run: {CLI_NAME} code config --registry ./skills  (local path or git URL)"))
        return sec

    if registry.startswith(("http://", "https://", "git@")):
        sec.results.append(CheckResult(
            "Skills registry", "Configured", OK, f"git: {registry}"))
    elif Path(registry).expanduser().exists():
        sec.results.append(CheckResult(
            "Skills registry", "Configured", OK, f"path: {registry}"))
    else:
        sec.results.append(CheckResult(
            "Skills registry", "Configured", FAIL,
            f"Path does not exist: {registry}",
            fix=f"Point to a valid path/URL: {CLI_NAME} code config --registry <path|url>"))
    return sec


def _check_integration(name: str, url_env: str, token_env: str, default_port: int,
                        probe: bool, require: bool = False) -> List[CheckResult]:
    """Validate one Bitbucket/Jira/Confluence-style integration.

    When ``require`` is True, an unconfigured integration is a FAIL instead of a
    SKIP so ``--require-integrations`` can hard-fail (used by the installer).
    """
    out: List[CheckResult] = []
    url = os.environ.get(url_env, "").strip()
    token = os.environ.get(token_env, "").strip()

    if not url and not token:
        out.append(CheckResult(
            "Integrations", name, FAIL if require else SKIP,
            f"Not configured ({url_env} / {token_env} unset)",
            fix=f"{CLI_NAME} init {name.lower()} --url <url> --token <pat>"))
        return out

    # URL
    if not url:
        out.append(CheckResult("Integrations", f"{name} URL", FAIL,
                               f"{url_env} is empty", fix=f"Set {url_env}=https://..."))
    elif not _is_valid_url(url):
        out.append(CheckResult("Integrations", f"{name} URL", FAIL,
                               f"Invalid URL: {url}", fix=f"Set {url_env} to a full http(s) URL."))
    else:
        out.append(CheckResult("Integrations", f"{name} URL", OK, url))

    # Token
    if not token:
        out.append(CheckResult("Integrations", f"{name} token", FAIL,
                               f"{token_env} is empty",
                               fix=f"Set {token_env} to a personal access token."))
    else:
        out.append(CheckResult("Integrations", f"{name} token", OK, "set (hidden)"))

    # Optional host reachability
    if probe and url and _is_valid_url(url):
        host, port = _host_port(url, default_port)
        if _tcp_reachable(host, port):
            out.append(CheckResult("Integrations", f"{name} reachable", OK, f"{host}:{port}"))
        else:
            out.append(CheckResult("Integrations", f"{name} reachable", WARN,
                                   f"Cannot reach {host}:{port}",
                                   fix="Check VPN/network access to the server."))
    return out


def _check_integrations(probe: bool, require: bool = False) -> Section:
    sec = Section("Integrations", required=require)
    # Surface which .env files supply these credentials (loaded at startup).
    try:
        from agentic_cli.env import resolved_env_files
        files = resolved_env_files()
        if files:
            sec.results.append(CheckResult(
                "Integrations", ".env files", OK,
                ", ".join(str(f) for f in files)))
        else:
            sec.results.append(CheckResult(
                "Integrations", ".env files", SKIP, "none found",
                fix=f"Scaffold one: {CLI_NAME} init env"))
    except Exception:
        pass
    sec.results += _check_integration(
        "Bitbucket", "BITBUCKET_SERVER_URL", "BITBUCKET_PERSONAL_ACCESS_TOKEN", 443, probe, require)
    sec.results += _check_integration(
        "Jira", "JIRA_SERVER_URL", "JIRA_PERSONAL_ACCESS_TOKEN", 443, probe, require)
    sec.results += _check_integration(
        "Confluence", "CONFLUENCE_SERVER_URL", "CONFLUENCE_PERSONAL_ACCESS_TOKEN", 443, probe, require)
    return sec


def _check_mcp() -> Section:
    sec = Section("MCP servers", required=False)
    endpoints = {
        "Bitbucket MCP": os.environ.get("MCP_BITBUCKET_URL", "http://localhost:8126/sse"),
        "Confluence MCP": os.environ.get("MCP_CONFLUENCE_URL", "http://localhost:8129/sse"),
    }
    gateway = os.environ.get("MCP_GATEWAY_URL", "")
    if gateway:
        endpoints["MCP Gateway"] = gateway

    for label, url in endpoints.items():
        host, port = _host_port(url, 80)
        if _tcp_reachable(host, port):
            sec.results.append(CheckResult("MCP servers", label, OK, f"{host}:{port}"))
        else:
            sec.results.append(CheckResult(
                "MCP servers", label, WARN, f"Not reachable at {host}:{port}",
                fix="Start servers: cd mcp-servers && docker compose up -d"))
    return sec


def _check_kg() -> Section:
    sec = Section("Knowledge Graph", required=False)
    try:
        from agentic_cli.kg.config import KGConfig
        config = KGConfig.load()
    except Exception as e:  # pragma: no cover - defensive
        sec.results.append(CheckResult("Knowledge Graph", "Config", WARN,
                                       f"Could not load KG config: {e}"))
        return sec

    provider = config.provider
    sec.results.append(CheckResult("Knowledge Graph", "Provider", OK, provider))

    try:
        if provider == "neo4j":
            from agentic_cli.kg.validation import check_neo4j_availability
            if not config.neo4j_password:
                sec.results.append(CheckResult(
                    "Knowledge Graph", "Neo4j", WARN, "No password configured",
                    fix=f"Run: {CLI_NAME} kg init --provider neo4j --uri bolt://localhost:7687 "
                        "--username neo4j --password <pw>"))
            else:
                ok, msg = check_neo4j_availability(
                    uri=config.neo4j_uri, username=config.neo4j_username,
                    password=config.neo4j_password)
                sec.results.append(CheckResult(
                    "Knowledge Graph", "Neo4j", OK if ok else WARN, msg,
                    fix="" if ok else "Start KG infra: cd mcp-servers && docker compose up -d kg-neo4j"))
        elif provider == "lightrag":
            from agentic_cli.kg.lightrag_client import check_lightrag_availability
            ok, msg = check_lightrag_availability(base_url=config.lightrag_url)
            sec.results.append(CheckResult(
                "Knowledge Graph", "LightRAG", OK if ok else WARN, msg,
                fix="" if ok else "Start LightRAG infra (see kg-infrastructure/)."))
        else:
            sec.results.append(CheckResult(
                "Knowledge Graph", provider, SKIP,
                f"Reachability check not implemented for '{provider}'"))
    except Exception as e:
        sec.results.append(CheckResult("Knowledge Graph", "Connection", WARN, str(e)))
    return sec


def _check_optional() -> Section:
    sec = Section("Optional tooling", required=False)

    # Devin
    if os.environ.get("DEVIN_API_KEY"):
        sec.results.append(CheckResult("Optional tooling", "Devin API key", OK, "set (hidden)"))
    else:
        sec.results.append(CheckResult(
            "Optional tooling", "Devin API key", SKIP, "DEVIN_API_KEY unset",
            fix="Set DEVIN_API_KEY to enable Devin sessions/knowledge."))

    # Docker
    try:
        from agentic_cli.kg.validation import check_docker_running
        ok, msg = check_docker_running()
        sec.results.append(CheckResult(
            "Optional tooling", "Docker", OK if ok else WARN, msg,
            fix="" if ok else "Start Docker Desktop / daemon to run MCP + KG infra."))
    except Exception as e:
        sec.results.append(CheckResult("Optional tooling", "Docker", WARN, str(e)))
    return sec


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_doctor(probe: bool = False, as_json: bool = False, strict: bool = False,
               require_integrations: bool = False) -> int:
    """Run all checks. Returns a process exit code (0 = healthy).

    When ``require_integrations`` is True, the Integrations section is treated
    as required, so missing Bitbucket/Jira/Confluence credentials cause a
    non-zero exit (useful for installers / CI gates).
    """
    sections = [
        _check_runtime(),
        _check_registry(),
        _check_integrations(probe, require=require_integrations),
        _check_mcp(),
        _check_kg(),
        _check_optional(),
    ]

    if as_json:
        payload = {
            "sections": [
                {
                    "name": s.name,
                    "required": s.required,
                    "results": [r.__dict__ for r in s.results],
                }
                for s in sections
            ]
        }
        console.print_json(json.dumps(payload))
    else:
        _render(sections)

    # Determine exit code
    has_required_fail = any(
        s.required and any(r.status == FAIL for r in s.results) for s in sections
    )
    has_any_fail = any(any(r.status == FAIL for r in s.results) for s in sections)

    if has_required_fail or (strict and has_any_fail):
        return 1
    return 0


def _render(sections: List[Section]) -> None:
    fixes: List[CheckResult] = []

    for sec in sections:
        if not sec.results:
            continue
        suffix = " [dim](required)[/dim]" if sec.required else ""
        table = Table(title=f"{sec.name}{suffix}", title_justify="left",
                      show_header=True, header_style="bold")
        table.add_column("", width=2)
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Detail")
        for r in sec.results:
            table.add_row(_SYMBOL.get(r.status, "?"), r.name, r.detail)
            if r.status in (FAIL, WARN) and r.fix:
                fixes.append(r)
        console.print(table)
        console.print()

    if fixes:
        console.print("[bold]Suggested fixes[/bold]")
        for r in fixes:
            sym = _SYMBOL.get(r.status, "?")
            console.print(f"  {sym} [cyan]{r.name}[/cyan]: {r.fix}")
        console.print()

    # Summary line
    total = sum(len(s.results) for s in sections)
    fails = sum(1 for s in sections for r in s.results if r.status == FAIL)
    warns = sum(1 for s in sections for r in s.results if r.status == WARN)
    oks = sum(1 for s in sections for r in s.results if r.status == OK)
    console.print(
        f"[bold]Summary:[/bold] [green]{oks} ok[/green], "
        f"[yellow]{warns} warning(s)[/yellow], [red]{fails} failure(s)[/red] "
        f"of {total} checks."
    )
