"""Tests for resolving a user profile to a persona (auth.persona)."""

from pathlib import Path

from agentic_cli.auth.models import Principal
from agentic_cli.auth.persona import (
    DEFAULT_PERSONA,
    get_persona,
    persona_for,
    persona_map,
    remove,
    set_persona,
)

_NOFILE = Path("/nonexistent/persona-assignments.json")


def _p(subject="u@x.com", roles=None, groups=None):
    return Principal(subject=subject, roles=roles or [], groups=groups or [])


def test_role_derived_persona_defaults():
    assert persona_for(_p(roles=["developer"]), assignments_path=_NOFILE) == "dev"
    assert persona_for(_p(roles=["maintainer"]), assignments_path=_NOFILE) == "dev"
    assert persona_for(_p(roles=["admin"]), assignments_path=_NOFILE) == "dev"
    assert persona_for(_p(roles=["viewer"]), assignments_path=_NOFILE) == "ba"


def test_no_role_falls_back_to_default_persona():
    assert persona_for(_p(roles=[]), assignments_path=_NOFILE) == DEFAULT_PERSONA


def test_most_privileged_role_wins():
    # Holds both viewer and developer -> developer's persona.
    assert persona_for(
        _p(roles=["viewer", "developer"]), assignments_path=_NOFILE) == "dev"


def test_group_map_overrides_role_default():
    p = _p(roles=["developer"], groups=["qa-team"])
    assert persona_for(
        p, pmap={"qa-team": "qa"}, assignments_path=_NOFILE) == "qa"


def test_persona_map_parsing():
    m = persona_map({"KEEL_PERSONA_MAP": "eng:dev, qa-team:qa ;ba-guild:ba"})
    assert m == {"eng": "dev", "qa-team": "qa", "ba-guild": "ba"}


def test_explicit_assignment_beats_everything(tmp_path):
    path = tmp_path / "persona-assignments.json"
    set_persona("U@X.com", "sm", path=path)
    assert get_persona("u@x.com", path=path) == "sm"
    # Even a group map + role default lose to the explicit assignment.
    p = _p(subject="u@x.com", roles=["developer"], groups=["qa-team"])
    assert persona_for(p, pmap={"qa-team": "qa"}, assignments_path=path) == "sm"


def test_assignment_remove(tmp_path):
    path = tmp_path / "persona-assignments.json"
    set_persona("u@x.com", "qa", path=path)
    assert remove("u@x.com", path=path) is True
    assert get_persona("u@x.com", path=path) is None
    assert remove("u@x.com", path=path) is False
