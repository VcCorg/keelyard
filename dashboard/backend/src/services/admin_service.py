"""Admin service — app branding + nav visibility, backed by the CLI store.

Reads are open (every user needs branding + their nav); writes are admin-only
(enforced at the route) and audited with the acting principal. The CLI
(``agentic_cli.admin``) owns persistence and validation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel


class BrandingModel(BaseModel):
    app_title: str = "Keel"
    app_name: str = "Agentic Product Development Platform"


class CodeAssistModel(BaseModel):
    """Which code-assist engines users may pick, and the org default."""
    enabled: List[str] = ["devin", "local"]
    default: str = "devin"


class AdminSettingsModel(BaseModel):
    branding: BrandingModel = BrandingModel()
    nav_visibility: Dict[str, List[str]] = {}
    skill_enforcement: str = "off"        # "off" (advisory) | "enforce" (hard)
    # Default for DOMAIN-LESS builds/sessions; domains carry their own dial
    # in governance.yaml. "off" | "warn" | "enforce".
    build_governance_default: str = "warn"
    # Vendor-neutral code-assist tools + org default engine.
    code_assist: CodeAssistModel = CodeAssistModel()


class AdminSettingsUpdate(BaseModel):
    branding: Optional[BrandingModel] = None
    nav_visibility: Optional[Dict[str, List[str]]] = None
    replace_nav: bool = False
    skill_enforcement: Optional[str] = None
    build_governance_default: Optional[str] = None
    code_assist: Optional[CodeAssistModel] = None


def _to_model(s) -> AdminSettingsModel:
    return AdminSettingsModel(
        branding=BrandingModel(app_title=s.branding.app_title, app_name=s.branding.app_name),
        nav_visibility=s.nav_visibility,
        skill_enforcement=s.skill_enforcement,
        build_governance_default=s.build_governance_default,
        code_assist=CodeAssistModel(enabled=s.code_assist.enabled, default=s.code_assist.default),
    )


def get_settings() -> AdminSettingsModel:
    from agentic_cli.admin import load_settings

    return _to_model(load_settings())


# ── Role assignments ─────────────────────────────────────────────────────────

class RoleAssignment(BaseModel):
    subject: str
    roles: List[str]


class RoleAssignmentsModel(BaseModel):
    valid_roles: List[str] = []
    assignments: List[RoleAssignment] = []


class RoleAssignmentUpdate(BaseModel):
    subject: str
    roles: List[str] = []   # empty -> remove the assignment


def _norm(subject: str) -> str:
    return (subject or "").strip().lower()


def get_role_assignments() -> RoleAssignmentsModel:
    from agentic_cli.auth import VALID_ROLES, load_assignments

    data = load_assignments()
    return RoleAssignmentsModel(
        valid_roles=list(VALID_ROLES),
        assignments=[RoleAssignment(subject=s, roles=r) for s, r in sorted(data.items())],
    )


def set_role_assignment(update: RoleAssignmentUpdate, actor: str | None = None) -> RoleAssignmentsModel:
    from agentic_cli.auth import VALID_ROLES, remove_assignment, set_roles

    subject = _norm(update.subject)
    if not subject:
        raise HTTPException(status_code=400, detail="A user subject (email) is required.")
    unknown = [r for r in update.roles if r not in VALID_ROLES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown role(s): {', '.join(unknown)}")

    # Self-lockout guard: an admin may not strip their own admin role.
    if actor and _norm(actor) == subject and "admin" not in update.roles:
        raise HTTPException(status_code=400,
                            detail="You cannot remove your own admin role (self-lockout guard).")

    if update.roles:
        set_roles(subject, update.roles)
    else:
        remove_assignment(subject)

    try:
        from agentic_cli.tracker import record_action

        record_action("admin", "assign_role", entity_type="user", entity_id=subject,
                      source="dashboard", actor=actor, details={"roles": update.roles})
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return get_role_assignments()


# ── Platform reset ───────────────────────────────────────────────────────────

CONFIRM_PHRASE = "RESET"


class ResetScope(BaseModel):
    scope: str
    label: str
    items: int


class ResetPreviewModel(BaseModel):
    scopes: List[ResetScope] = []


class ResetRequest(BaseModel):
    scopes: List[str] = []
    confirm: str = ""            # must equal CONFIRM_PHRASE


class ResetResult(BaseModel):
    reset: List[str] = []
    summary: Dict[str, Any] = {}


def reset_preview() -> ResetPreviewModel:
    from agentic_cli.admin import SCOPES, reset_preview as cli_preview

    prev = cli_preview()
    return ResetPreviewModel(scopes=[
        ResetScope(scope=s, label=prev[s]["label"], items=int(prev[s]["items"])) for s in SCOPES
    ])


def reset_platform(req: ResetRequest, actor: str | None = None) -> ResetResult:
    from agentic_cli.admin import normalize_scopes, reset_platform as cli_reset

    if req.confirm != CONFIRM_PHRASE:
        raise HTTPException(status_code=400,
                            detail=f"Confirmation required: type '{CONFIRM_PHRASE}' to reset.")
    scopes = normalize_scopes(req.scopes)
    if not scopes:
        raise HTTPException(status_code=400, detail="No valid reset scope selected.")

    summary = cli_reset(scopes)
    try:
        from agentic_cli.tracker import record_action

        record_action("admin", "reset", entity_type="platform", entity_id="app",
                      source="dashboard", actor=actor, details={"scopes": scopes})
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return ResetResult(reset=scopes, summary=summary)


def update_settings(update: AdminSettingsUpdate, actor: str | None = None) -> AdminSettingsModel:
    from agentic_cli.admin import update_settings as cli_update

    s = cli_update(
        branding=update.branding.model_dump() if update.branding else None,
        nav_visibility=update.nav_visibility,
        replace_nav=update.replace_nav,
        skill_enforcement=update.skill_enforcement,
        build_governance_default=update.build_governance_default,
        code_assist=update.code_assist.model_dump() if update.code_assist else None,
    )
    try:
        from agentic_cli.tracker import record_action

        record_action("admin", "update_settings", entity_type="app_settings", entity_id="app",
                      source="dashboard", actor=actor,
                      details={"branding": update.branding.model_dump() if update.branding else None,
                               "nav_ids": sorted((update.nav_visibility or {}).keys()),
                               "skill_enforcement": update.skill_enforcement,
                               "build_governance_default": update.build_governance_default,
                               "code_assist": update.code_assist.model_dump() if update.code_assist else None})
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return _to_model(s)
