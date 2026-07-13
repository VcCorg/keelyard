"""Resolve a signed-in user's *profile* to a persona.

Personas (dev / qa / ba / sm / domain) are the unit of skill governance: a
domain's ``skills.yaml`` says which skills each persona may load/use, and
:mod:`agentic_cli.meta_repo` enforces it. This module is the bridge from
*identity* (a :class:`Principal` resolved by an auth provider) to the persona
that policy is evaluated against, mirroring how roles resolve:

  1. an explicit per-user assignment (``~/.keel/persona-assignments.json``) —
     admin-controlled, authoritative;
  2. an SSO group mapping (``KEEL_PERSONA_MAP='eng:dev,qa-team:qa'``);
  3. a sensible default derived from the user's RBAC role.

Everything is overridable and has a safe least-privilege fallback so a user is
never left without a persona.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional

from agentic_cli.auth.models import (
    ADMIN,
    DEVELOPER,
    MAINTAINER,
    ROLE_ORDER,
    VIEWER,
    Principal,
)

# Built-in personas shipped with the platform (mirrors meta_repo BUILTIN_PERSONA_IDS).
BUILTIN_PERSONAS = ("dev", "qa", "ba", "sm", "domain")

# Least-privilege fallback when nothing else resolves (a read-oriented persona).
DEFAULT_PERSONA = "ba"

# Role → persona default. Builders map to ``dev``; view-only users to ``ba``.
ROLE_PERSONA_DEFAULT: Dict[str, str] = {
    VIEWER: "ba",
    DEVELOPER: "dev",
    MAINTAINER: "dev",
    ADMIN: "dev",
}

ENV_PERSONA_MAP = "KEEL_PERSONA_MAP"  # "group:persona,group:persona"

ASSIGNMENTS_PATH = Path.home() / ".keel" / "persona-assignments.json"


def _split(value: str) -> list[str]:
    return [p.strip() for p in (value or "").replace(";", ",").split(",") if p.strip()]


def _norm(subject: str) -> str:
    return (subject or "").strip().lower()


def persona_map(env: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """Parse ``KEEL_PERSONA_MAP='eng:dev,qa-team:qa'`` → {group: persona}."""
    src = os.environ if env is None else env
    out: Dict[str, str] = {}
    for pair in _split(src.get(ENV_PERSONA_MAP, "")):
        group, _, persona = pair.partition(":")
        if group and persona:
            out[group.strip()] = persona.strip()
    return out


def load_persona_assignments(path: Path = ASSIGNMENTS_PATH) -> Dict[str, str]:
    """Return ``{subject: persona}`` (tolerates a missing/corrupt file)."""
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - never break on a bad file
        return {}
    data = raw.get("assignments", raw) if isinstance(raw, dict) else {}
    out: Dict[str, str] = {}
    for subject, persona in data.items():
        if isinstance(persona, str) and persona.strip():
            out[_norm(subject)] = persona.strip()
    return out


def get_persona(subject: str, path: Path = ASSIGNMENTS_PATH) -> Optional[str]:
    """The explicit persona assigned to ``subject``, if any."""
    return load_persona_assignments(path).get(_norm(subject))


def set_persona(subject: str, persona: str, path: Path = ASSIGNMENTS_PATH) -> Path:
    """Assign ``persona`` to ``subject`` (authoritative override)."""
    if not _norm(subject):
        raise ValueError("subject is required")
    if not (persona or "").strip():
        raise ValueError("persona is required")
    data = load_persona_assignments(path)
    data[_norm(subject)] = persona.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"assignments": {k: data[k] for k in sorted(data)}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def remove(subject: str, path: Path = ASSIGNMENTS_PATH) -> bool:
    """Drop an explicit persona assignment; True if one was removed."""
    data = load_persona_assignments(path)
    if _norm(subject) not in data:
        return False
    del data[_norm(subject)]
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"assignments": {k: data[k] for k in sorted(data)}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def _persona_from_roles(roles: Iterable[str]) -> Optional[str]:
    """Map the most-privileged role a user holds to its default persona."""
    have = {r for r in roles}
    for role in reversed(ROLE_ORDER):  # admin → … → viewer
        if role in have:
            return ROLE_PERSONA_DEFAULT.get(role)
    return None


def persona_for(
    principal: Principal,
    *,
    pmap: Optional[Mapping[str, str]] = None,
    assignments_path: Path = ASSIGNMENTS_PATH,
) -> str:
    """Resolve the persona for a principal (assignment → group map → role → default).

    Precedence, highest first:
      1. explicit per-user assignment,
      2. first SSO group present in the persona map,
      3. role-derived default,
      4. :data:`DEFAULT_PERSONA`.
    """
    explicit = get_persona(principal.subject, assignments_path)
    if explicit:
        return explicit

    resolved_map = dict(pmap) if pmap is not None else persona_map()
    for group in principal.groups:
        if group in resolved_map:
            return resolved_map[group]

    by_role = _persona_from_roles(principal.roles)
    if by_role:
        return by_role

    return DEFAULT_PERSONA
