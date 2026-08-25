"""Persona-tiered workspace service — thin proxy over the agentic-cli core.

Mirrors the `keel workspace` / `keel domain sync` model in the dashboard:

- Reads (tracker + path resolution) import the CLI library directly.
- Long-running steps (`keel workspace open`, `keel domain sync`) shell out to the
  real CLI and stream stdout so the worktree/graphify logic lives in one place.
- "Open in IDE" launches a local editor (windsurf / code / cursor) at the folder
  that matches the chosen persona's tier:
    * solutions-architect -> product meta-repo  (product tier)
    * tech-lead           -> domain meta-repo   (domain tier)
    * dev                 -> repo worktree       (repo tier)
"""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

from pydantic import BaseModel

# Safe at import time: template_service only reaches back into this module from
# inside function bodies, so there is no import cycle.
from src.services.template_service import TemplateDriftSummary


# ── Models ───────────────────────────────────────────────────────────────────

class WorkspaceInfo(BaseModel):
    tier: str
    persona: str
    root_path: str
    product: Optional[str] = None
    domain: Optional[str] = None
    store_path: Optional[str] = None
    repos: list[dict] = []
    created_at: Optional[str] = None
    last_active: Optional[str] = None


class WorkspaceTarget(BaseModel):
    persona: str
    tier: str                       # product | domain | repo
    path: Optional[str] = None      # folder to open in the IDE
    exists: bool = False            # folder is present on disk
    ready: bool = False             # registered workspace exists for this target
    needs: Optional[str] = None     # suggested action: "sync" | "open" | None
    hint: str = ""                  # human-readable guidance
    # Template drift, populated only when explicitly requested: the check renders
    # the whole template to compare against, which is too slow for every
    # persona/context change. `ready` deliberately stays true for a drifted repo —
    # it IS usable; it is just no longer the template it was generated from.
    drift: Optional[TemplateDriftSummary] = None


class OpenIdeResult(BaseModel):
    success: bool
    editor: str
    command: str
    path: str
    message: str


# ── CLI access helpers ─────────────────────────────────────────────────────--

def _tracker():
    from agentic_cli import tracker
    return tracker


def _pw():
    from agentic_cli import persona_workspace
    return persona_workspace


def resolve_cli_command() -> list[str]:
    keel = shutil.which("keel")
    if keel:
        return [keel]
    return [sys.executable, "-m", "agentic_cli.main"]


# ── Persona → tier mapping ─────────────────────────────────────────────────--

PERSONA_TIER = {
    "solutions-architect": "product",
    "tech-lead": "domain",
    "dev": "repo",
}

PERSONA_LABELS = {
    "solutions-architect": "Solutions Architect",
    "tech-lead": "Tech Lead",
    "dev": "Developer",
}


# ── Reads ───────────────────────────────────────────────────────────────────

def list_workspaces(tier: Optional[str] = None) -> list[WorkspaceInfo]:
    t = _tracker()
    rows = t.get_workspaces(tier=tier)
    return [
        WorkspaceInfo(
            tier=r.get("tier"),
            persona=r.get("persona"),
            root_path=r.get("root_path"),
            product=r.get("product"),
            domain=r.get("domain"),
            store_path=r.get("store_path"),
            repos=r.get("repos") or [],
            created_at=r.get("created_at"),
            last_active=r.get("last_active"),
        )
        for r in rows
    ]


def resolve_target(
    persona: str,
    product: Optional[str] = None,
    domain: Optional[str] = None,
    repo: Optional[str] = None,
    include_drift: bool = False,
) -> WorkspaceTarget:
    """Resolve the folder a persona should open, and whether it's ready.

    With ``include_drift``, a domain-tier target is also annotated with template
    drift counts so the UI can show a `drifted` state. Off by default because the
    check re-renders the template (seconds), and this function is on the hot path
    of every persona/context change and of ``workflow_service``.
    """
    pw = _pw()
    tier = PERSONA_TIER.get(persona)
    if not tier:
        raise ValueError(f"Unknown persona '{persona}'.")

    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    path: Optional[Path] = None
    needs: Optional[str] = None
    hint = ""

    if tier == "product":
        if not product:
            raise ValueError("Solutions Architect requires a product.")
        path = pw.find_product_meta(product)
        hint = (
            "Product meta-repo (governance, crosswalk, persona catalog). "
            "Tracker-only — no code checkout."
        )
        if not path:
            needs = "onboard"
            hint = f"No product meta-repo found for '{product}'. Onboard the product first."

    elif tier == "domain":
        if not domain:
            raise ValueError("Tech Lead requires a domain.")
        meta = detect_domain_meta_repo(domain)
        path = meta
        hint = (
            "Domain meta-repo with federated graph references across all repos "
            "(.graph/graph-refs.json) — no code checkout."
        )
        if meta is None:
            needs = "onboard"
            hint = f"No domain meta-repo found for '{domain}'. Onboard the domain first."
        else:
            refs = meta / pw.GRAPH_DIR_NAME / pw.GRAPH_REFS_FILENAME
            if not refs.exists():
                needs = "sync"
                hint = (
                    "Domain meta-repo found, but graphs aren't synced yet. "
                    "Run 'Sync (Tech Lead)' to build .graph/graph-refs.json."
                )

    elif tier == "repo":
        if not (domain and repo):
            raise ValueError("Developer requires a domain and a repo.")
        path = pw.get_workspace_base() / domain / "repos" / repo
        hint = "Editable git worktree of a single repo (branch ws/dev/<repo>)."
        if not (path.exists() and any(path.iterdir()) if path.exists() else False):
            needs = "open"
            hint = (
                "Worktree not created yet. Run 'Open (Developer)' to materialize a "
                "worktree from the canonical store."
            )

    exists = bool(path and Path(path).exists())
    ready = exists and needs is None

    drift = None
    if include_drift and tier == "domain" and exists and domain:
        from src.services import template_service

        drift = template_service.drift_summary(domain)

    return WorkspaceTarget(
        persona=persona, tier=tier,
        path=str(path) if path else None,
        exists=exists, ready=ready, needs=needs, hint=hint,
        drift=drift,
    )


# ── Open in IDE ──────────────────────────────────────────────────────────────

# Editor key → the `code_assist_tool` value that controls where persona skills
# are written so the editor actually picks them up:
#   devin    → .devin/skills/<name>/SKILL.md  (Devin project skills)
#   windsurf → .windsurf/workflows/<name>.md
#   cursor   → .cursor/rules/<name>.md
#   code     → .skills/<name>/SKILL.md        (generic/portable)
EDITOR_TOOL = {
    "windsurf": "windsurf",
    "cursor": "cursor",
    "devin": "devin",
    "code": "generic",
}

# Preference order when no editor is explicitly chosen.
_EDITOR_ORDER = ["devin", "windsurf", "cursor", "code"]

# Execution-engine name (admin code_assist) → local editor-launcher key. The
# admin config is the single source of truth for which IDE tools are offered;
# `local` maps to nothing (it renders a bundle, it isn't an editor to open).
ENGINE_TO_EDITOR = {
    "vscode-copilot": "code",
    "devin": "devin",
    "devin-cli": "devin",   # the CLI variant still opens the Devin app to review
    "cursor": "cursor",
    "windsurf": "windsurf",
}

_DEVIN_APP = Path("/Applications/Devin.app")

# macOS `.app` fallbacks — an editor is often installed as a bundle without the
# shell shim on PATH (VS Code needs a manual "Install 'code' command in PATH"
# step). We treat the app as sufficient and launch via `open -a "<Name>"`, so a
# user's admin default doesn't silently get substituted just because the CLI
# shim is missing.
_EDITOR_APP: dict[str, tuple[str, Path]] = {
    "code":     ("Visual Studio Code", Path("/Applications/Visual Studio Code.app")),
    "cursor":   ("Cursor",             Path("/Applications/Cursor.app")),
    "windsurf": ("Windsurf",           Path("/Applications/Windsurf.app")),
}


def _editor_app_available(editor: str) -> bool:
    if sys.platform != "darwin":
        return False
    info = _EDITOR_APP.get(editor)
    return bool(info and info[1].exists())


def tool_for_editor(editor: Optional[str]) -> str:
    """Map a launcher/editor key to its `keel --code-assist-tool` value."""
    return EDITOR_TOOL.get((editor or "").lower(), "generic")


def _devin_available() -> bool:
    """Devin counts as available via its CLI or the macOS desktop app."""
    if shutil.which("devin"):
        return True
    return sys.platform == "darwin" and _DEVIN_APP.exists()


def _editor_available(editor: str) -> bool:
    if editor == "devin":
        return _devin_available()
    return bool(shutil.which(editor)) or _editor_app_available(editor)


def detect_editors() -> list[str]:
    """Return available editor keys, in preference order (devin first)."""
    return [e for e in _EDITOR_ORDER if _editor_available(e)]


def _code_assist():
    """The admin code-assist config, or None if unavailable."""
    try:
        from agentic_cli.admin import load_settings

        return load_settings().code_assist
    except Exception:  # noqa: BLE001
        return None


def enabled_editors() -> list[str]:
    """Installed editor launchers permitted by the admin code-assist config,
    org default first.

    This makes the admin ``code_assist`` config the single source of truth for
    which IDE tools the "Open in IDE" flows offer — no ad-hoc dropdown of every
    detected editor. Falls back to raw detection only if the admin config can't
    be read, so the feature never silently breaks.
    """
    installed = detect_editors()
    ca = _code_assist()
    if not ca:
        return installed
    order = [ca.default] + [e for e in ca.enabled if e != ca.default]
    out: list[str] = []
    for eng in order:
        ed = ENGINE_TO_EDITOR.get(eng)
        if ed and ed in installed and ed not in out:
            out.append(ed)
    return out


def _editor_command(editor: str, target: Path) -> Optional[list[str]]:
    """Build the launch command for an editor, or None if unavailable.

    Prefers the editor's shell CLI on PATH (`code <path>`, `cursor <path>`, …);
    on macOS, falls back to `open -a "<App Name>" <path>` when only the desktop
    app is installed — so a user's admin default (e.g. VS Code) is honored even
    if they haven't set up the CLI shim.
    """
    p = str(target)
    if editor == "devin":
        if sys.platform == "darwin" and _DEVIN_APP.exists():
            return ["open", "-a", "Devin", p]
        if shutil.which("devin"):
            return ["devin", p]
        return None
    if shutil.which(editor):
        return [editor, p]
    if _editor_app_available(editor):
        app_name = _EDITOR_APP[editor][0]
        return ["open", "-a", app_name, p]
    return None


_LAUNCHER_LABEL = {"devin": "Devin", "code": "VS Code", "cursor": "Cursor", "windsurf": "Windsurf"}


def _org_default_editor() -> Optional[str]:
    ca = _code_assist()
    if not ca:
        return None
    return ENGINE_TO_EDITOR.get(ca.default)


def open_in_ide(path: str, editor: Optional[str] = None) -> OpenIdeResult:
    """Launch a local editor/agent at ``path``.

    Uses the requested editor when provided, else the admin org default; refuses
    to silently substitute a different vendor when the target editor isn't
    installed (e.g. VS Code default with no `code` CLI + no VS Code.app) — the
    caller gets a clear error so the admin choice isn't quietly ignored.
    """
    target = Path(path).expanduser()
    if not target.exists():
        raise ValueError(f"Path does not exist: {target}")

    requested = (editor or "").lower() or _org_default_editor()
    if not requested:
        # No admin config and no explicit pick — fall back to whatever is
        # installed (preserves behavior on a fresh install).
        installed = detect_editors()
        requested = installed[0] if installed else None

    cmd = _editor_command(requested, target) if requested else None
    if cmd is None:
        # Never silently swap vendors: if the org default isn't installed, tell
        # the user rather than opening a different tool.
        if requested and requested in _LAUNCHER_LABEL:
            label = _LAUNCHER_LABEL[requested]
            raise ValueError(
                f"{label} is not installed here — no `{requested}` command on PATH"
                + (f" and no {label}.app in /Applications" if sys.platform == "darwin" else "")
                + f". Install {label}, or set another default in Admin → Code assist tools."
            )
        raise ValueError(
            "No supported editor found (devin/windsurf/cursor/code). "
            "Install the editor's shell command, or set an admin default."
        )
    chosen = requested

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Failed to launch '{chosen}': {e}") from e

    return OpenIdeResult(
        success=True, editor=chosen, command=" ".join(cmd), path=str(target),
        message=f"Opening {target} in {chosen}.",
    )


# ── Streaming actions (shell out to the real CLI) ───────────────────────────--

async def _stream_cli(args: list[str]) -> AsyncGenerator[str, None]:
    cmd = resolve_cli_command() + args
    yield f"$ {' '.join(cmd)}"

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    assert proc.stdout is not None
    while True:
        raw = await proc.stdout.readline()
        if not raw:
            break
        yield raw.decode(errors="replace").rstrip("\n")
    rc = await proc.wait()
    yield f"__EXIT__ {rc}"


def stream_sync_domain(domain: str, persona: str = "tech-lead",
                       graphify: bool = True,
                       tool: str = "generic") -> AsyncGenerator[str, None]:
    """Stream `keel domain sync <domain>` (tech-lead domain-tier assembly).

    ``tool`` is the resolved `code_assist_tool` (e.g. ``devin``) controlling
    where the tech-lead persona skill is written.
    """
    args = ["domain", "sync", domain, "--persona", persona]
    args += ["--graphify"] if graphify else ["--no-graphify"]
    args += ["--code-assist-tool", tool]
    return _stream_cli(args)


def stream_open_workspace(domain: str, repo: str, persona: str = "dev",
                          graphify: bool = False,
                          tool: str = "generic") -> AsyncGenerator[str, None]:
    """Stream `keel workspace open <domain> <repo>` (dev repo-tier worktree).

    ``tool`` is the resolved `code_assist_tool` (e.g. ``devin``) controlling
    where the dev persona skill is written.
    """
    args = ["workspace", "open", domain, repo, "--persona", persona]
    args += ["--graphify"] if graphify else ["--no-graphify"]
    args += ["--code-assist-tool", tool]
    return _stream_cli(args)
