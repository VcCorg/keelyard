"""Per-domain build governance — the dial that makes the control plane binding.

Each domain's ``governance.yaml`` (in its meta-repo, produced by the Governance
phase) declares ``build_governance: off | warn | enforce``. The platform reads
it at the two build seams — ``keel code onboard`` and the execution registry's
``create_session`` (which covers Devin AND local engines) — and either tags
ungoverned work (warn), refuses it (enforce), or stays silent (off).

Per-domain by design (adoption-friendly): a team opts its domain into
``enforce`` when ready; a domain set to ``off`` *is* the sandbox — experiments
still run under a domain, so audit/attribution never has holes. Work with NO
domain at all can't consult any domain's dial, so the platform-wide admin
default (``build_governance_default`` in admin settings) applies to it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

LEVELS = ("off", "warn", "enforce")
DEFAULT_LEVEL = "warn"


class GovernanceViolation(Exception):
    """Raised when enforce-level governance refuses an action at a seam."""

    def __init__(self, message: str, violations: Optional[List[str]] = None):
        self.violations = violations or []
        super().__init__(message)


def sanitize_level(level: object) -> str:
    lv = str(level or "").strip().lower()
    return lv if lv in LEVELS else DEFAULT_LEVEL


@dataclass
class BuildPolicy:
    """The resolved governance decision context for one action."""

    level: str                       # off | warn | enforce
    source: str                      # "domain:<slug>" | "default" | "default:<reason>"
    domain: str = ""
    meta_repo: Optional[Path] = None
    violations: List[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.level == "enforce" and bool(self.violations)

    @property
    def tagged(self) -> bool:
        """True when the action should carry governance tags in the audit."""
        return self.level != "off" and bool(self.violations)

    def audit_details(self) -> dict:
        return {"governance_level": self.level, "governance_source": self.source,
                "governance_violations": self.violations}


def find_meta_repo(domain: str, cwd: Optional[Path] = None) -> Optional[Path]:
    """Locate ``domain-<slug>-meta`` by the workspace conventions."""
    if not domain:
        return None
    base = cwd or Path.cwd()
    candidates = [
        base / f"domain-{domain}-meta",
        base.parent / f"domain-{domain}-meta",
        Path.home() / "workspace" / domain / f"domain-{domain}-meta",
    ]
    # Configured code workspace, when set (keel init workspace).
    ws = os.environ.get("KEEL_CODE_WORKSPACE", "")
    if ws:
        candidates.append(Path(ws).expanduser() / domain / f"domain-{domain}-meta")
    for c in candidates:
        if (c / ".platform" / "config" / "governance.yaml").is_file():
            return c
    return None


def default_level() -> str:
    """Platform default for domain-less work (admin-controlled)."""
    try:
        # Read the store path from the module at call time (not a bound default
        # arg) so overrides/monkeypatches of SETTINGS_PATH take effect.
        from agentic_cli.admin import settings as admin_settings

        s = admin_settings.load_settings(admin_settings.SETTINGS_PATH)
        return sanitize_level(s.build_governance_default)
    except Exception:  # noqa: BLE001 - settings unavailable => safe default
        return DEFAULT_LEVEL


def domain_level(meta_repo: Path) -> str:
    """Read a domain's dial from its governance.yaml."""
    try:
        import yaml

        cfg = meta_repo / ".platform" / "config" / "governance.yaml"
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        return sanitize_level(data.get("build_governance", DEFAULT_LEVEL))
    except Exception:  # noqa: BLE001 - unreadable config => default
        return DEFAULT_LEVEL


def resolve(domain: str = "", cwd: Optional[Path] = None) -> BuildPolicy:
    """Resolve the applicable level for an action in ``domain`` (may be '')."""
    domain = (domain or "").strip()
    if not domain:
        return BuildPolicy(level=default_level(), source="default")
    meta = find_meta_repo(domain, cwd=cwd)
    if meta is None:
        # Domain named but no meta-repo found — the domain itself is
        # ungoverned; the platform default decides how hard that bites.
        return BuildPolicy(level=default_level(), source="default:meta-repo-missing",
                           domain=domain)
    return BuildPolicy(level=domain_level(meta), source=f"domain:{domain}",
                       domain=domain, meta_repo=meta)


def registered_repos(meta_repo: Path) -> list[dict]:
    """The repos a domain registers in repos.yaml: [{slug, clone_url}]."""
    try:
        import yaml

        cfg = meta_repo / ".platform" / "config" / "repos.yaml"
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        return [{"slug": str(r.get("slug", "")),
                 "clone_url": str(r.get("clone_url", ""))}
                for r in (data.get("repos") or []) if r.get("slug")]
    except Exception:  # noqa: BLE001
        return []


def _domain_repo_slugs(meta_repo: Path) -> list[str]:
    return [r["slug"] for r in registered_repos(meta_repo)]


def check_session(domain: str = "", cwd: Optional[Path] = None) -> BuildPolicy:
    """Gate for engine sessions (Devin/local/…): governed = domain + meta-repo."""
    policy = resolve(domain, cwd=cwd)
    if not policy.domain:
        policy.violations.append("session has no domain (ungoverned)")
    elif policy.meta_repo is None:
        policy.violations.append(
            f"domain '{policy.domain}' has no meta-repo (run the governance "
            "phase: keel domain scaffold)")
    return policy


def check_onboard(domain: str = "", repo_slug: str = "",
                  project_name: str = "", cwd: Optional[Path] = None) -> BuildPolicy:
    """Gate for code onboarding: governed = domain + repo registered in repos.yaml."""
    policy = resolve(domain, cwd=cwd)
    if not policy.domain:
        policy.violations.append("onboard has no --domain (ungoverned)")
        return policy
    if policy.meta_repo is None:
        policy.violations.append(
            f"domain '{policy.domain}' has no meta-repo (run the governance "
            "phase: keel domain scaffold)")
        return policy
    slugs = _domain_repo_slugs(policy.meta_repo)
    if slugs:  # only meaningful when the domain registers repos at all
        candidate = (repo_slug or project_name or "").strip()
        if candidate and candidate not in slugs:
            policy.violations.append(
                f"repo '{candidate}' is not registered in the domain's repos.yaml "
                f"(registered: {', '.join(slugs[:8])})")
    return policy


def enforce_or_raise(policy: BuildPolicy, action: str) -> None:
    """Raise :class:`GovernanceViolation` when the policy blocks ``action``."""
    if policy.blocked:
        raise GovernanceViolation(
            f"{action} blocked by build governance "
            f"({policy.source}, level=enforce):\n  - "
            + "\n  - ".join(policy.violations)
            + "\nUse a governed domain, or a sandbox domain "
            "(build_governance: off in its governance.yaml).",
            violations=policy.violations,
        )
