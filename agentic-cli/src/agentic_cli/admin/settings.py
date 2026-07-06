"""Admin-controlled application settings — branding + nav visibility.

The org's admins control app-level presentation (title/name shown top-left) and
which UI roles may see which navigation entries, instead of those being
hard-coded. The CLI owns the store (``~/.dva/admin-settings.json``); the
dashboard is a lens that reads it for every user and writes it for admins only.

Nav visibility is stored as ``{nav_id: [roles...]}`` overrides. The *catalogue*
of nav ids and their defaults lives in the frontend (it owns the nav shape); the
store is intentionally generic — it just persists the override map, so the nav
can evolve without a schema change here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

# UI roles the sidebar understands (least → most privileged).
UI_ROLES = ["member", "lead", "admin"]

SETTINGS_PATH = Path.home() / ".dva" / "admin-settings.json"

DEFAULT_APP_TITLE = "Keel"
DEFAULT_APP_NAME = "Agentic Product Development Platform"


@dataclass
class Branding:
    app_title: str = DEFAULT_APP_TITLE   # top-left heading
    app_name: str = DEFAULT_APP_NAME     # top-left subtitle


@dataclass
class AppSettings:
    branding: Branding = field(default_factory=Branding)
    # nav_id -> allowed UI roles. Absent id => frontend default (from minRole).
    nav_visibility: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"branding": asdict(self.branding), "nav_visibility": self.nav_visibility}


def _sanitize_roles(roles: List[str]) -> List[str]:
    """Keep only known UI roles, de-duped and ordered; always allow admin."""
    seen = {r for r in roles if r in UI_ROLES}
    seen.add("admin")  # admins never lose access to anything
    return [r for r in UI_ROLES if r in seen]


def load_settings(path: Path = SETTINGS_PATH) -> AppSettings:
    """Load settings, tolerating a missing/corrupt file (returns defaults)."""
    if not path.is_file():
        return AppSettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - never break on a bad settings file
        return AppSettings()
    b = raw.get("branding", {}) if isinstance(raw, dict) else {}
    branding = Branding(
        app_title=str(b.get("app_title") or DEFAULT_APP_TITLE),
        app_name=str(b.get("app_name") or DEFAULT_APP_NAME),
    )
    nav = {}
    for nav_id, roles in (raw.get("nav_visibility", {}) or {}).items():
        if isinstance(roles, list):
            nav[str(nav_id)] = _sanitize_roles([str(r) for r in roles])
    return AppSettings(branding=branding, nav_visibility=nav)


def save_settings(settings: AppSettings, path: Path = SETTINGS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_dict(), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def set_branding(app_title: Optional[str] = None, app_name: Optional[str] = None,
                 path: Path = SETTINGS_PATH) -> AppSettings:
    s = load_settings(path)
    if app_title is not None and app_title.strip():
        s.branding.app_title = app_title.strip()
    if app_name is not None and app_name.strip():
        s.branding.app_name = app_name.strip()
    save_settings(s, path)
    return s


def set_nav_visibility(nav_id: str, roles: List[str], path: Path = SETTINGS_PATH) -> AppSettings:
    s = load_settings(path)
    s.nav_visibility[nav_id] = _sanitize_roles(roles)
    save_settings(s, path)
    return s


def clear_nav_override(nav_id: str, path: Path = SETTINGS_PATH) -> AppSettings:
    """Remove an override so the frontend default (minRole) applies again."""
    s = load_settings(path)
    s.nav_visibility.pop(nav_id, None)
    save_settings(s, path)
    return s


def update_settings(branding: Optional[dict] = None,
                    nav_visibility: Optional[Dict[str, List[str]]] = None,
                    replace_nav: bool = False,
                    path: Path = SETTINGS_PATH) -> AppSettings:
    """Apply a partial update (used by the dashboard PUT)."""
    s = load_settings(path)
    if branding:
        if branding.get("app_title", "").strip():
            s.branding.app_title = branding["app_title"].strip()
        if branding.get("app_name", "").strip():
            s.branding.app_name = branding["app_name"].strip()
    if nav_visibility is not None:
        cleaned = {str(k): _sanitize_roles([str(r) for r in v])
                   for k, v in nav_visibility.items() if isinstance(v, list)}
        s.nav_visibility = cleaned if replace_nav else {**s.nav_visibility, **cleaned}
    save_settings(s, path)
    return s
