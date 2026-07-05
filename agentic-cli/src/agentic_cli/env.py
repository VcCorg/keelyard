"""Central `.env` loading for the Agentic CLI.

Goal: users configure Jira / Confluence / Bitbucket / AI tokens **once** in a
`.env` file instead of exporting them into the shell before every session.

Precedence (lowest → highest):

    1. ~/.dva/.env            global, machine-wide (loaded from any directory)
    2. ./.env                 project-local (walking up from the cwd)
    3. real exported env vars (never overridden)

Rule: values already present in ``os.environ`` (i.e. a real ``export`` or a CI
secret) always win. `.env` files only *fill gaps*, so this is safe in CI and
respects explicit shell overrides.

`load_env()` is idempotent and cheap; it is invoked once at CLI startup.
"""

from __future__ import annotations

import os
import stat as _stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Recognized keys — single source of truth for scaffolding + validation.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnvVar:
    """A recognized environment variable the CLI understands."""

    name: str
    group: str
    required: bool = False
    secret: bool = False
    default: str = ""
    description: str = ""


# Integration credentials come in URL + token pairs. Marked required so
# `dva doctor` flags them, but the CLI still runs without them.
RECOGNIZED_VARS: List[EnvVar] = [
    # --- Jira -------------------------------------------------------------
    EnvVar("JIRA_SERVER_URL", "Jira", required=True,
           description="Base URL, e.g. https://jira.company.com"),
    EnvVar("JIRA_PERSONAL_ACCESS_TOKEN", "Jira", required=True, secret=True,
           description="Personal access token for Jira"),
    # --- Confluence -------------------------------------------------------
    EnvVar("CONFLUENCE_SERVER_URL", "Confluence", required=True,
           description="Base URL, e.g. https://confluence.company.com"),
    EnvVar("CONFLUENCE_PERSONAL_ACCESS_TOKEN", "Confluence", required=True, secret=True,
           description="Personal access token for Confluence"),
    # --- Bitbucket --------------------------------------------------------
    EnvVar("BITBUCKET_SERVER_URL", "Bitbucket", required=True,
           description="Base URL, e.g. https://bitbucket.company.com"),
    EnvVar("BITBUCKET_PERSONAL_ACCESS_TOKEN", "Bitbucket", required=True, secret=True,
           description="Personal access token for Bitbucket"),
    # --- AI / Google Cloud (Vertex AI) -----------------------------------
    EnvVar("GOOGLE_PROJECT_ID", "AI", required=False,
           description="GCP project id for Vertex AI"),
    EnvVar("GOOGLE_LOCATION", "AI", required=False, default="us-central1",
           description="Vertex AI location/region"),
    EnvVar("VERTEX_AI_MODEL", "AI", required=False, default="gemini-2.0-flash-001",
           description="Default Vertex AI model id"),
    EnvVar("GOOGLE_API_KEY", "AI", required=False, secret=True,
           description="Google/Gemini API key (alternative to Vertex project)"),
    EnvVar("GEMINI_API_KEY", "AI", required=False, secret=True,
           description="Gemini API key (alias of GOOGLE_API_KEY)"),
    # --- MCP endpoints ----------------------------------------------------
    EnvVar("MCP_GATEWAY_URL", "MCP", required=False,
           description="MCP gateway URL (optional)"),
    EnvVar("MCP_JIRA_URL", "MCP", required=False,
           default="http://localhost:8128/sse", description="Jira MCP SSE URL"),
    EnvVar("MCP_CONFLUENCE_URL", "MCP", required=False,
           default="http://localhost:8129/sse", description="Confluence MCP SSE URL"),
    EnvVar("MCP_BITBUCKET_URL", "MCP", required=False,
           default="http://localhost:8126/sse", description="Bitbucket MCP SSE URL"),
    # --- Optional tooling -------------------------------------------------
    EnvVar("DEVIN_API_KEY", "Optional", required=False, secret=True,
           description="Devin API key for cloud sessions/knowledge"),
    EnvVar("DVA_SKILLS_REGISTRY", "Optional", required=False,
           description="Path/URL to the skills registry"),
]

RECOGNIZED_NAMES = {v.name for v in RECOGNIZED_VARS}


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

GLOBAL_ENV_PATH = Path.home() / ".dva" / ".env"


def _find_project_env(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from ``start`` (cwd) looking for a project-local ``.env``.

    Stops at the filesystem root or a ``.git`` boundary (whichever comes
    first) so we don't accidentally pick up an unrelated parent `.env`.
    """
    cur = (start or Path.cwd()).resolve()
    for directory in [cur, *cur.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None


def resolved_env_files(start: Optional[Path] = None) -> List[Path]:
    """Return the `.env` files that would be loaded, in precedence order
    (lowest first: global, then project-local)."""
    files: List[Path] = []
    if GLOBAL_ENV_PATH.is_file():
        files.append(GLOBAL_ENV_PATH)
    proj = _find_project_env(start)
    if proj and proj != GLOBAL_ENV_PATH:
        files.append(proj)
    return files


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_LOADED = False
# Persists across calls so source attribution survives the idempotent startup
# load (validate can report which file each value came from).
_APPLIED: Dict[str, Path] = {}


@dataclass
class LoadResult:
    """Summary of what `load_env` did (useful for `dva init env` / doctor)."""

    files: List[Path] = field(default_factory=list)
    applied: Dict[str, Path] = field(default_factory=dict)   # var -> source file
    skipped_existing: List[str] = field(default_factory=list)  # already in real env


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a `.env` file. Prefers python-dotenv; falls back to a tiny parser."""
    try:
        from dotenv import dotenv_values
        return {k: (v or "") for k, v in dotenv_values(path).items() if k}
    except Exception:
        pass

    out: Dict[str, str] = {}
    try:
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                out[key] = val
    except OSError:
        pass
    return out


def load_env(start: Optional[Path] = None, force: bool = False) -> LoadResult:
    """Load `.env` files into ``os.environ`` without overriding real exports.

    Idempotent: subsequent calls are no-ops unless ``force=True``.
    """
    global _LOADED
    result = LoadResult()
    if _LOADED and not force:
        result.applied = dict(_APPLIED)
        result.files = resolved_env_files(start)
        return result

    for path in resolved_env_files(start):
        result.files.append(path)
        for key, val in _parse_env_file(path).items():
            already = key in os.environ and os.environ[key] != ""
            # A value we ourselves set from a *lower-precedence* .env may be
            # overridden by a higher-precedence one; a real export never is.
            from_env = key in _APPLIED
            if already and not from_env:
                result.skipped_existing.append(key)
                continue
            os.environ[key] = val
            result.applied[key] = path
            _APPLIED[key] = path

    _LOADED = True
    return result


def mask(value: str) -> str:
    """Mask a secret for display: keep first/last 2 chars."""
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}…{value[-2:]}"


# ---------------------------------------------------------------------------
# Writing (used by `dva init` and the dashboard setup panel)
# ---------------------------------------------------------------------------

def render_example() -> str:
    """Build a `.env` template from the recognized-vars registry."""
    lines = [
        "# Agentic CLI environment configuration",
        "# Configure integration tokens here instead of exporting them each session.",
        "# Real exported shell variables always override these values.",
        "",
    ]
    groups: Dict[str, List[EnvVar]] = {}
    for v in RECOGNIZED_VARS:
        groups.setdefault(v.group, []).append(v)
    for group, vars_ in groups.items():
        lines.append(f"# --- {group} " + "-" * max(0, 56 - len(group)))
        for v in vars_:
            tag = " (required)" if v.required else ""
            if v.description:
                lines.append(f"# {v.description}{tag}")
            lines.append(f"{v.name}={v.default}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def scaffold_env(path: Path = GLOBAL_ENV_PATH, force: bool = False) -> bool:
    """Create a `.env` file from the template. Returns True if written.

    Existing files are left untouched unless ``force`` is set.
    """
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_example())
    try:
        path.chmod(_stat.S_IRUSR | _stat.S_IWUSR)  # 600 — secrets file
    except OSError:
        pass
    return True


def set_env_vars(updates: Dict[str, str], path: Path = GLOBAL_ENV_PATH) -> Path:
    """Update or append ``KEY=value`` pairs in a `.env` file.

    Preserves existing lines/comments; updates keys in place, appends new ones.
    Creates the file (chmod 600) if missing. Also updates ``os.environ`` and the
    live source-attribution map so the change is visible in the same process.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    if path.is_file():
        lines = path.read_text().splitlines()

    remaining = dict(updates)
    out: List[str] = []
    for raw in lines:
        stripped = raw.strip()
        key = ""
        if stripped and not stripped.startswith("#") and "=" in stripped:
            candidate = stripped[len("export "):] if stripped.startswith("export ") else stripped
            key = candidate.partition("=")[0].strip()
        if key and key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(raw)

    for key, val in remaining.items():
        out.append(f"{key}={val}")

    path.write_text("\n".join(out).rstrip() + "\n")
    try:
        path.chmod(_stat.S_IRUSR | _stat.S_IWUSR)
    except OSError:
        pass

    # Reflect immediately in-process.
    for key, val in updates.items():
        os.environ[key] = val
        _APPLIED[key] = path
    return path
