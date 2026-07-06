"""Admin-controlled application settings (branding + nav visibility)."""

from agentic_cli.admin.settings import (
    AppSettings,
    Branding,
    UI_ROLES,
    clear_nav_override,
    load_settings,
    save_settings,
    set_branding,
    set_nav_visibility,
    update_settings,
)
from agentic_cli.admin.reset import (
    SCOPES,
    SCOPE_LABELS,
    normalize_scopes,
    preview as reset_preview,
    reset as reset_platform,
)

__all__ = [
    "AppSettings",
    "Branding",
    "UI_ROLES",
    "load_settings",
    "save_settings",
    "set_branding",
    "set_nav_visibility",
    "clear_nav_override",
    "update_settings",
    "SCOPES",
    "SCOPE_LABELS",
    "normalize_scopes",
    "reset_preview",
    "reset_platform",
]
