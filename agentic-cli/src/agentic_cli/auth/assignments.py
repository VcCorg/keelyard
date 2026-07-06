"""Admin-assigned user → role mappings.

Roles can come from an SSO proxy's groups, but admins often need to grant or
adjust roles per user directly. This store holds ``{subject: [roles]}`` explicit
assignments that **take precedence** over provider-derived roles, so the People
page is the authoritative place to control who has which role.

Stored at ``~/.keel/role-assignments.json`` (the CLI owns it); the dashboard is a
lens that reads it for every request and writes it for admins only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from agentic_cli.auth.models import ROLE_ORDER

ASSIGNMENTS_PATH = Path.home() / ".keel" / "role-assignments.json"

# Valid assignable roles = the auth role model (viewer < developer < ... < admin).
VALID_ROLES = list(ROLE_ORDER)


def _sanitize(roles: List[str]) -> List[str]:
    """Keep only known roles, de-duped, ordered least→most privileged."""
    seen = {r for r in roles if r in VALID_ROLES}
    return [r for r in ROLE_ORDER if r in seen]


def _norm(subject: str) -> str:
    return (subject or "").strip().lower()


def load_assignments(path: Path = ASSIGNMENTS_PATH) -> Dict[str, List[str]]:
    """Return ``{subject: [roles]}`` (tolerates a missing/corrupt file)."""
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - never break on a bad file
        return {}
    data = raw.get("assignments", raw) if isinstance(raw, dict) else {}
    out: Dict[str, List[str]] = {}
    for subject, roles in data.items():
        if isinstance(roles, list):
            clean = _sanitize([str(r) for r in roles])
            if clean:
                out[_norm(subject)] = clean
    return out


def save_assignments(assignments: Dict[str, List[str]], path: Path = ASSIGNMENTS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"assignments": {k: v for k, v in sorted(assignments.items())}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def get_roles(subject: str, path: Path = ASSIGNMENTS_PATH) -> Optional[List[str]]:
    """Explicit roles for ``subject`` (None if unassigned)."""
    return load_assignments(path).get(_norm(subject))


def set_roles(subject: str, roles: List[str], path: Path = ASSIGNMENTS_PATH) -> Dict[str, List[str]]:
    """Assign roles to a user. Empty/invalid roles remove the assignment."""
    data = load_assignments(path)
    clean = _sanitize(roles)
    key = _norm(subject)
    if clean:
        data[key] = clean
    else:
        data.pop(key, None)
    save_assignments(data, path)
    return data


def remove(subject: str, path: Path = ASSIGNMENTS_PATH) -> Dict[str, List[str]]:
    data = load_assignments(path)
    data.pop(_norm(subject), None)
    save_assignments(data, path)
    return data


def effective_roles(subject: str, fallback: List[str], path: Path = ASSIGNMENTS_PATH) -> List[str]:
    """Assigned roles if the subject has an explicit assignment, else ``fallback``."""
    assigned = get_roles(subject, path)
    return assigned if assigned else list(fallback)
