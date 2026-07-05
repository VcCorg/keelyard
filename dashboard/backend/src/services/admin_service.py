"""Admin service — app branding + nav visibility, backed by the CLI store.

Reads are open (every user needs branding + their nav); writes are admin-only
(enforced at the route) and audited with the acting principal. The CLI
(``agentic_cli.admin``) owns persistence and validation.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class BrandingModel(BaseModel):
    app_title: str = "Agent Playground"
    app_name: str = "Agentic Platform"


class AdminSettingsModel(BaseModel):
    branding: BrandingModel = BrandingModel()
    nav_visibility: Dict[str, List[str]] = {}


class AdminSettingsUpdate(BaseModel):
    branding: Optional[BrandingModel] = None
    nav_visibility: Optional[Dict[str, List[str]]] = None
    replace_nav: bool = False


def get_settings() -> AdminSettingsModel:
    from agentic_cli.admin import load_settings

    s = load_settings()
    return AdminSettingsModel(
        branding=BrandingModel(app_title=s.branding.app_title, app_name=s.branding.app_name),
        nav_visibility=s.nav_visibility,
    )


def update_settings(update: AdminSettingsUpdate, actor: str | None = None) -> AdminSettingsModel:
    from agentic_cli.admin import update_settings as cli_update

    s = cli_update(
        branding=update.branding.model_dump() if update.branding else None,
        nav_visibility=update.nav_visibility,
        replace_nav=update.replace_nav,
    )
    try:
        from agentic_cli.tracker import record_action

        record_action("admin", "update_settings", entity_type="app_settings", entity_id="app",
                      source="dashboard", actor=actor,
                      details={"branding": update.branding.model_dump() if update.branding else None,
                               "nav_ids": sorted((update.nav_visibility or {}).keys())})
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return AdminSettingsModel(
        branding=BrandingModel(app_title=s.branding.app_title, app_name=s.branding.app_name),
        nav_visibility=s.nav_visibility,
    )
