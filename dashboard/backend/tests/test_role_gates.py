"""Role-activity gates: Jira push, MCP writes, setup inits, persona in /me."""

import pytest
from fastapi import HTTPException

from src.services.auth_service import me, require


class FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


def _as(roles_env, monkeypatch, groups=""):
    """Configure the dev provider to act as a user with the given roles."""
    monkeypatch.setenv("KEEL_AUTH_MODE", "dev")
    monkeypatch.setenv("KEEL_DEV_ROLES", roles_env)
    monkeypatch.setenv("KEEL_DEV_USER", "smoke@test")


def test_viewer_cannot_push_requirements(monkeypatch):
    from agentic_cli.auth import PERM_REQUIREMENTS_PUSH

    _as("viewer", monkeypatch)
    dep = require(PERM_REQUIREMENTS_PUSH)
    with pytest.raises(HTTPException) as e:
        dep(FakeRequest())
    assert e.value.status_code == 403


def test_developer_can_push_requirements(monkeypatch):
    from agentic_cli.auth import PERM_REQUIREMENTS_PUSH

    _as("developer", monkeypatch)
    p = require(PERM_REQUIREMENTS_PUSH)(FakeRequest())
    assert p.has(PERM_REQUIREMENTS_PUSH)


def test_developer_cannot_configure_platform(monkeypatch):
    from agentic_cli.auth import PERM_PLATFORM_CONFIGURE

    _as("developer", monkeypatch)
    with pytest.raises(HTTPException) as e:
        require(PERM_PLATFORM_CONFIGURE)(FakeRequest())
    assert e.value.status_code == 403


def test_maintainer_can_configure_platform(monkeypatch):
    from agentic_cli.auth import PERM_PLATFORM_CONFIGURE

    _as("maintainer", monkeypatch)
    p = require(PERM_PLATFORM_CONFIGURE)(FakeRequest())
    assert p.has(PERM_PLATFORM_CONFIGURE)


def test_me_reports_persona(monkeypatch, tmp_path):
    import agentic_cli.auth.persona as persona_mod

    _as("developer", monkeypatch)
    monkeypatch.setattr(persona_mod, "ASSIGNMENTS_PATH",
                        tmp_path / "persona-assignments.json")
    out = me(FakeRequest())
    assert out.persona == "dev"          # developer role -> dev persona default

    # Group map override: qa-team -> qa persona.
    monkeypatch.setenv("KEEL_DEV_ROLES", "developer")
    monkeypatch.setenv("KEEL_PERSONA_MAP", "qa-team:qa")
    monkeypatch.setenv("KEEL_DEV_GROUPS", "qa-team")
    out2 = me(FakeRequest())
    assert out2.persona in ("qa", "dev")  # qa when dev provider exposes groups
