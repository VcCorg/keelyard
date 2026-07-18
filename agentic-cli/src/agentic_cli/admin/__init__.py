"""Admin-controlled application settings (branding + nav visibility)."""

from agentic_cli.admin.settings import (
    AppSettings,
    Branding,
    BUILD_GOVERNANCE_LEVELS,
    ENFORCEMENT_MODES,
    UI_ROLES,
    clear_nav_override,
    enforcement_enabled,
    set_build_governance_default,
    load_settings,
    save_settings,
    set_branding,
    set_nav_visibility,
    set_skill_enforcement,
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
    "ENFORCEMENT_MODES",
    "BUILD_GOVERNANCE_LEVELS",
    "load_settings",
    "save_settings",
    "set_branding",
    "set_nav_visibility",
    "clear_nav_override",
    "set_skill_enforcement",
    "enforcement_enabled",
    "set_build_governance_default",
    "update_settings",
    "SCOPES",
    "SCOPE_LABELS",
    "normalize_scopes",
    "reset_preview",
    "reset_platform",
]
