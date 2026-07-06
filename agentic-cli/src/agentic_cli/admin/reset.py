"""Platform data reset — admin-controlled, scoped, auditable.

The dashboard grows a lot of ingested/loaded state (activity history, the
repo/project/domain catalog, Devin sessions, admin settings). Individual deletes
exist per item; this provides an *app-level* reset by scope, so an operator can
return the platform to a clean state without hand-deleting each entity.

Destructive by nature — callers must confirm. The CLI owns the logic; the
dashboard is a lens that gates it behind ``admin:*`` and audits the actor.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# Scopes an operator can reset.
SCOPES = ["activity", "catalog", "sessions", "settings"]

SCOPE_LABELS = {
    "activity": "Activity / audit history",
    "catalog": "Catalog (repos, projects, products, domains, workspaces)",
    "sessions": "Local Devin session records",
    "settings": "Admin settings (branding, nav) + role assignments",
}

_DEVIN_SESSIONS = Path.home() / ".dva" / "devin" / "sessions.json"


def _settings_files() -> List[Path]:
    from agentic_cli.admin.settings import SETTINGS_PATH
    from agentic_cli.auth.assignments import ASSIGNMENTS_PATH

    return [SETTINGS_PATH, ASSIGNMENTS_PATH]


def normalize_scopes(scopes: List[str]) -> List[str]:
    """Expand ``all`` and keep only known scopes, in canonical order."""
    req = {s.strip().lower() for s in scopes if s and s.strip()}
    if "all" in req:
        return list(SCOPES)
    return [s for s in SCOPES if s in req]


def preview() -> Dict[str, Dict]:
    """Report what each scope currently holds (counts / file presence)."""
    from agentic_cli.tracker import RESET_TABLE_GROUPS, table_counts

    activity = table_counts(RESET_TABLE_GROUPS["activity"])
    catalog = table_counts(RESET_TABLE_GROUPS["catalog"])
    return {
        "activity": {"label": SCOPE_LABELS["activity"], "items": sum(activity.values()),
                     "detail": activity},
        "catalog": {"label": SCOPE_LABELS["catalog"], "items": sum(catalog.values()),
                    "detail": catalog},
        "sessions": {"label": SCOPE_LABELS["sessions"],
                     "items": 1 if _DEVIN_SESSIONS.is_file() else 0,
                     "detail": {"sessions.json": _DEVIN_SESSIONS.is_file()}},
        "settings": {"label": SCOPE_LABELS["settings"],
                     "items": sum(1 for p in _settings_files() if p.is_file()),
                     "detail": {p.name: p.is_file() for p in _settings_files()}},
    }


def _reset_activity() -> Dict:
    from agentic_cli.tracker import RESET_TABLE_GROUPS, clear_tables

    return {"cleared": clear_tables(RESET_TABLE_GROUPS["activity"])}


def _reset_catalog() -> Dict:
    from agentic_cli.tracker import RESET_TABLE_GROUPS, clear_tables

    return {"cleared": clear_tables(RESET_TABLE_GROUPS["catalog"])}


def _remove(path: Path) -> bool:
    try:
        if path.is_file():
            path.unlink()
            return True
    except OSError:
        pass
    return False


def _reset_sessions() -> Dict:
    return {"removed": {_DEVIN_SESSIONS.name: _remove(_DEVIN_SESSIONS)}}


def _reset_settings() -> Dict:
    return {"removed": {p.name: _remove(p) for p in _settings_files()}}


_HANDLERS = {
    "activity": _reset_activity,
    "catalog": _reset_catalog,
    "sessions": _reset_sessions,
    "settings": _reset_settings,
}


def reset(scopes: List[str]) -> Dict[str, Dict]:
    """Reset the requested scopes. Returns a per-scope summary of what changed."""
    result: Dict[str, Dict] = {}
    for scope in normalize_scopes(scopes):
        result[scope] = _HANDLERS[scope]()
    return result
