"""Persona-scoped skill policy evaluation (shared, importable).

The stdlib profiler shipped into each meta-repo (`profile_skills.py`) evaluates
this same logic without any Keel import so it runs on a bare clone. This module
is the in-process twin used by the CLI (`keel code onboard`) and the dashboard,
where the policy decides — per user persona — whether a skill may be installed.

A rule is ``{"allow": [...], "deny": [...]}`` of tokens: tier names
(``persona``, ``agent-skill``, ``domain-validated``, ``linked:<repo>``,
``local``), ``persona:self`` / ``persona:<id>``, skill-name globs, or ``*``.
A specific (non-``*``) deny always wins; ``deny: ['*']`` makes a rule allow-list
only. Statuses: ``permitted`` / ``denied`` / ``out-of-policy``.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, List, Optional

from agentic_cli.meta_repo.config import SkillsConfig

PERMITTED = "permitted"
DENIED = "denied"
OUT_OF_POLICY = "out-of-policy"


def default_policy() -> Dict[str, dict]:
    """The built-in persona policy (used when a domain ships no skills.yaml)."""
    return SkillsConfig().personas


def load_persona_policy(meta_repo_path: Path) -> Dict[str, dict]:
    """Load the ``personas`` policy from a meta-repo's skills.yaml.

    Falls back to :func:`default_policy` when the file is absent or unreadable,
    so enforcement always has a policy to evaluate against.
    """
    cfg = Path(meta_repo_path) / ".platform" / "config" / "skills.yaml"
    if not cfg.is_file():
        return default_policy()
    try:
        import yaml

        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 - never break on a bad policy file
        return default_policy()
    return SkillsConfig.from_dict(data).personas


def resolve_rule(policy: Dict[str, dict], persona: str) -> dict:
    """Effective allow/deny rule for a persona (falls back to ``default``)."""
    rule = policy.get(persona) or policy.get("default") or {
        "allow": ["persona:self", "domain-validated"], "deny": []}
    return {"allow": list(rule.get("allow", [])), "deny": list(rule.get("deny", []))}


def match_token(token: str, name: str, tier: str, persona: str) -> bool:
    """True if a policy token matches a skill (name/tier) for ``persona``."""
    if token == "*":
        return True
    if token == "persona:self":
        return tier == "persona" and name == persona
    if token.startswith("persona:"):
        return tier == "persona" and name == token[len("persona:"):]
    if token == "persona":
        return tier == "persona"
    if token == tier:
        return True
    if token == "linked" and tier.startswith("linked:"):
        return True
    if token.endswith(":*") and tier.startswith(token[:-1]):
        return True
    return fnmatch.fnmatch(name, token)


def status_for(name: str, tier: str, persona: str, rule: dict) -> str:
    """Resolve a skill to permitted / denied / out-of-policy for a persona."""
    allow = any(match_token(t, name, tier, persona) for t in rule.get("allow", []))
    specific_deny = any(
        t != "*" and match_token(t, name, tier, persona) for t in rule.get("deny", []))
    if specific_deny:
        return DENIED
    return PERMITTED if allow else OUT_OF_POLICY


def is_permitted(name: str, tier: str, persona: str, rule: dict) -> bool:
    """True only when the skill is explicitly permitted for the persona."""
    return status_for(name, tier, persona, rule) == PERMITTED


class Enforcer:
    """Bundles a resolved persona rule for repeated install-time decisions."""

    def __init__(self, persona: str, policy: Optional[Dict[str, dict]] = None):
        self.persona = persona
        self.policy = policy if policy is not None else default_policy()
        self.rule = resolve_rule(self.policy, persona)
        self.blocked: List[dict] = []

    def allow(self, name: str, tier: str) -> bool:
        """True if ``name`` (of ``tier``) may be installed; records blocks."""
        status = status_for(name, tier, self.persona, self.rule)
        if status == PERMITTED:
            return True
        self.blocked.append({"name": name, "tier": tier, "status": status})
        return False
