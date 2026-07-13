"""Load and validate domain meta-repo configurations."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class RepoConfig:
    """Configuration for a linked domain repo."""

    slug: str
    clone_url: str
    description: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    status: str = "active"  # active, archived, deprecated
    # Default branch to pin the submodule to. If None, it is auto-detected
    # from the remote (host-agnostic: bitbucket/gitlab/github).
    branch: Optional[str] = None
    # Git host: bitbucket, gitlab, github, or unknown (informational).
    host: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "RepoConfig":
        """Create from dictionary."""
        return cls(
            slug=data.get("slug", ""),
            clone_url=data.get("clone_url", ""),
            description=data.get("description", ""),
            languages=data.get("languages", []),
            frameworks=data.get("frameworks", []),
            status=data.get("status", "active"),
            branch=data.get("branch"),
            host=data.get("host", ""),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "slug": self.slug,
            "clone_url": self.clone_url,
            "description": self.description,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "status": self.status,
        }
        # Only emit optional fields when set to keep repos.yaml clean.
        if self.branch:
            result["branch"] = self.branch
        if self.host:
            result["host"] = self.host
        return result


@dataclass
class DomainConfig:
    """Configuration for a domain."""

    domain: str
    product: str
    description: str = ""
    owner: str = ""
    created_at: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "DomainConfig":
        """Create from dictionary."""
        return cls(
            domain=data.get("domain", ""),
            product=data.get("product", ""),
            description=data.get("description", ""),
            owner=data.get("owner", ""),
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "product": self.product,
            "description": self.description,
            "owner": self.owner,
            "created_at": self.created_at,
            "tags": self.tags,
        }


def _default_promotion_path() -> list[str]:
    """Default environment promotion path (outer-loop)."""
    return ["dev", "qa", "uat", "prd"]


def _default_checkpoint_gate_map() -> list[dict]:
    """Default inner↔outer crosswalk: methodology checkpoints → promotion gates.

    Each entry maps an inner-loop engineering checkpoint to the outer-loop
    environment gate it reinforces. This is the product-level "crosswalk".
    """
    return [
        {"checkpoint": "spec-approved", "gate": "dev", "blocking": True},
        {"checkpoint": "tests-green", "gate": "qa", "blocking": True},
        {"checkpoint": "code-review-passed", "gate": "uat", "blocking": True},
        {"checkpoint": "governance-gates-passed", "gate": "prd", "blocking": True},
    ]


@dataclass
class GovernanceConfig:
    """Configuration for governance rules (domain or product scope).

    Extended for the methodology+governance integration with the outer-loop
    promotion path and the inner↔outer crosswalk (checkpoint_gate_map).
    """

    branch_pattern: str = "^(feat|fix|docs|style|refactor|test|chore)/[A-Z]+-[0-9]+-.*$"
    require_pre_push_hook: bool = True
    require_ci_gates: bool = True
    require_code_review: bool = True
    min_reviewers: int = 1
    require_tests: bool = True
    test_coverage_min: float = 80.0
    # Outer-loop environment promotion path (progressively stricter gates).
    promotion_path: list[str] = field(default_factory=_default_promotion_path)
    # Inner↔outer crosswalk: methodology checkpoints mapped to promotion gates.
    checkpoint_gate_map: list[dict] = field(default_factory=_default_checkpoint_gate_map)
    # Inner-loop floor: rules that may only be tightened, never loosened,
    # without a recorded exception (see ExceptionEntry).
    inner_loop_floor: list[str] = field(
        default_factory=lambda: ["spec-first", "tdd", "two-stage-review"]
    )

    @classmethod
    def from_dict(cls, data: dict) -> "GovernanceConfig":
        """Create from dictionary."""
        return cls(
            branch_pattern=data.get("branch_pattern", cls.branch_pattern),
            require_pre_push_hook=data.get("require_pre_push_hook", True),
            require_ci_gates=data.get("require_ci_gates", True),
            require_code_review=data.get("require_code_review", True),
            min_reviewers=data.get("min_reviewers", 1),
            require_tests=data.get("require_tests", True),
            test_coverage_min=data.get("test_coverage_min", 80.0),
            promotion_path=data.get("promotion_path", _default_promotion_path()),
            checkpoint_gate_map=data.get(
                "checkpoint_gate_map", _default_checkpoint_gate_map()
            ),
            inner_loop_floor=data.get(
                "inner_loop_floor", ["spec-first", "tdd", "two-stage-review"]
            ),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "branch_pattern": self.branch_pattern,
            "require_pre_push_hook": self.require_pre_push_hook,
            "require_ci_gates": self.require_ci_gates,
            "require_code_review": self.require_code_review,
            "min_reviewers": self.min_reviewers,
            "require_tests": self.require_tests,
            "test_coverage_min": self.test_coverage_min,
            "promotion_path": self.promotion_path,
            "checkpoint_gate_map": self.checkpoint_gate_map,
            "inner_loop_floor": self.inner_loop_floor,
        }


@dataclass
class ProductConfig:
    """Configuration for a product (top-level grouping over domains)."""

    product: str
    description: str = ""
    owner: str = ""
    created_at: str = ""
    tags: list[str] = field(default_factory=list)
    # Pinned org-wide methodology (inner-loop) reference.
    org_methodology_url: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ProductConfig":
        return cls(
            product=data.get("product", ""),
            description=data.get("description", ""),
            owner=data.get("owner", ""),
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
            org_methodology_url=data.get("org_methodology_url", ""),
        )

    def to_dict(self) -> dict:
        return {
            "product": self.product,
            "description": self.description,
            "owner": self.owner,
            "created_at": self.created_at,
            "tags": self.tags,
            "org_methodology_url": self.org_methodology_url,
        }


@dataclass
class ExceptionEntry:
    """A recorded, auditable waiver that loosens an inner-loop/product rule.

    Domains/products may *tighten* governance freely; *loosening* requires one
    of these entries ("override with justification"). Stored as
    ``exceptions/<id>.yaml`` in the product meta-repo.
    """

    id: str
    rule: str
    reason: str
    scope: str  # e.g. "domain:cwow-facility" or "repo:cwow-facility-ui"
    owner: str
    created_at: str = ""
    expires_at: str = ""  # ISO date; empty = no expiry (discouraged)
    status: str = "active"  # active | expired | revoked

    @classmethod
    def from_dict(cls, data: dict) -> "ExceptionEntry":
        return cls(
            id=data.get("id", ""),
            rule=data.get("rule", ""),
            reason=data.get("reason", ""),
            scope=data.get("scope", ""),
            owner=data.get("owner", ""),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at", ""),
            status=data.get("status", "active"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule": self.rule,
            "reason": self.reason,
            "scope": self.scope,
            "owner": self.owner,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
        }

    def is_effective(self, today: Optional[str] = None) -> bool:
        """True if the waiver is active and not past its expiry date."""
        if self.status != "active":
            return False
        if not self.expires_at:
            return True
        from datetime import date
        ref = today or date.today().isoformat()
        return ref <= self.expires_at


def _default_persona_skill_policy() -> dict:
    """Least-privilege persona→skill governance.

    Maps a user's persona to the skills they may load/use. Each rule has an
    ``allow`` and ``deny`` list; tokens are tier names (``persona``,
    ``agent-skill``, ``domain-validated``, ``linked:<repo>``, ``local``),
    ``persona:self`` / ``persona:<id>``, skill-name globs, or ``*``. A specific
    (non-``*``) deny always wins; ``deny: ['*']`` makes a persona allow-list
    only. ``default`` applies to any persona without an explicit rule and is
    deliberately least-privilege: own persona skill + domain-validated only.
    """
    return {
        # Everyone may read persona guidance + domain-validated skills.
        "default": {"allow": ["persona", "domain-validated"], "deny": []},
        # Builders get everything; tighten with explicit denies per domain.
        "dev": {"allow": ["*"], "deny": []},
        "domain": {"allow": ["*"], "deny": []},
        # Non-builder personas are allow-list only (deny: ['*'] is the baseline):
        # they see guidance + validated skills and, for QA, testing tools —
        # everything else is out-of-policy (not granted), not a hard violation.
        "qa": {"allow": ["persona", "domain-validated", "testing-*"], "deny": ["*"]},
        "ba": {"allow": ["persona", "domain-validated"], "deny": ["*"]},
        "sm": {"allow": ["persona", "domain-validated"], "deny": ["*"]},
    }


@dataclass
class SkillsConfig:
    """Configuration for domain skills."""

    validation_required: bool = True
    auto_inject_superpowers: bool = True
    allow_custom_skills: bool = True
    skill_priority_order: list[str] = field(
        default_factory=lambda: ["validated", "customized", "injected"]
    )
    # Persona-scoped governance: {persona_id: {"allow": [...], "deny": [...]}}.
    personas: dict = field(default_factory=_default_persona_skill_policy)

    @classmethod
    def from_dict(cls, data: dict) -> "SkillsConfig":
        """Create from dictionary."""
        return cls(
            validation_required=data.get("validation_required", True),
            auto_inject_superpowers=data.get("auto_inject_superpowers", True),
            allow_custom_skills=data.get("allow_custom_skills", True),
            skill_priority_order=data.get(
                "skill_priority_order", ["validated", "customized", "injected"]
            ),
            personas=data.get("personas") or _default_persona_skill_policy(),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "validation_required": self.validation_required,
            "auto_inject_superpowers": self.auto_inject_superpowers,
            "allow_custom_skills": self.allow_custom_skills,
            "skill_priority_order": self.skill_priority_order,
            "personas": self.personas,
        }

    def policy_for(self, persona: str) -> dict:
        """Resolve the effective allow/deny policy for a persona id."""
        rule = self.personas.get(persona)
        if rule is None:
            rule = self.personas.get("default",
                                     {"allow": ["persona:self"], "deny": []})
        return {"allow": list(rule.get("allow", [])),
                "deny": list(rule.get("deny", []))}


# Built-in persona ids shipped with the platform. Product teams toggle these
# via ``defaults_enabled`` and add their own under ``personas`` in personas.yaml.
BUILTIN_PERSONA_IDS = ("domain", "dev", "qa", "sm", "ba")


@dataclass
class PersonaSection:
    """A titled content block within a persona skill document."""

    title: str
    body: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PersonaSection":
        return cls(title=data.get("title", ""), body=data.get("body", ""))

    def to_dict(self) -> dict:
        return {"title": self.title, "body": self.body}


@dataclass
class PersonaSpec:
    """Declarative definition of a single persona (role-based skill).

    Built-in personas (``builtin=True``) render via the platform's rich
    generators. Custom personas render their ``sections`` deterministically and,
    when ``ai_enrich`` is set and a model is available, may be AI-enriched.
    """

    id: str
    label: str
    description: str = ""
    sections: list[PersonaSection] = field(default_factory=list)
    ai_enrich: bool = False
    builtin: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "PersonaSpec":
        return cls(
            id=data.get("id", ""),
            label=data.get("label", data.get("id", "")),
            description=data.get("description", ""),
            sections=[PersonaSection.from_dict(s) for s in (data.get("sections") or [])],
            ai_enrich=bool(data.get("ai_enrich", False)),
            builtin=bool(data.get("builtin", False)),
        )

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "description": self.description,
        }
        if self.sections:
            result["sections"] = [s.to_dict() for s in self.sections]
        if self.ai_enrich:
            result["ai_enrich"] = True
        return result


@dataclass
class PersonasConfig:
    """Product-tier persona catalog (``.platform/config/personas.yaml``).

    ``defaults_enabled`` selects which built-in personas to generate; ``personas``
    holds product-specific additions (e.g. tech-lead, product-owner).
    """

    version: int = 1
    defaults_enabled: list[str] = field(
        default_factory=lambda: list(BUILTIN_PERSONA_IDS)
    )
    personas: list[PersonaSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PersonasConfig":
        return cls(
            version=int(data.get("version", 1)),
            defaults_enabled=data.get("defaults_enabled", list(BUILTIN_PERSONA_IDS)),
            personas=[PersonaSpec.from_dict(p) for p in (data.get("personas") or [])],
        )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "defaults_enabled": self.defaults_enabled,
            "personas": [p.to_dict() for p in self.personas],
        }


class MetaRepoConfig:
    """Load and manage domain meta-repo configurations."""

    def __init__(self, meta_repo_path: Path):
        """Initialize config loader.

        Args:
            meta_repo_path: Path to domain meta-repo
        """
        self.meta_repo_path = meta_repo_path
        self.config_dir = meta_repo_path / ".platform" / "config"

        self.domain: Optional[DomainConfig] = None
        self.repos: list[RepoConfig] = []
        self.governance: Optional[GovernanceConfig] = None
        self.skills: Optional[SkillsConfig] = None
        self.personas: Optional[PersonasConfig] = None

        self._load_all()

    def _load_all(self) -> None:
        """Load all configuration files."""
        self._load_domain_config()
        self._load_repos_config()
        self._load_governance_config()
        self._load_skills_config()
        self._load_personas_config()

    def _load_domain_config(self) -> None:
        """Load domain.yaml configuration."""
        config_file = self.config_dir / "domain.yaml"
        if not config_file.exists():
            logger.warning(f"domain.yaml not found at {config_file}")
            return

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            self.domain = DomainConfig.from_dict(data)
            logger.debug(f"Loaded domain config: {self.domain.domain}")
        except Exception as e:
            logger.error(f"Failed to load domain.yaml: {e}")

    def _load_repos_config(self) -> None:
        """Load repos.yaml configuration."""
        config_file = self.config_dir / "repos.yaml"
        if not config_file.exists():
            logger.debug(f"repos.yaml not found at {config_file}")
            return

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            repos_list = data.get("repos", [])
            self.repos = [RepoConfig.from_dict(r) for r in repos_list]
            logger.debug(f"Loaded {len(self.repos)} repo configs")
        except Exception as e:
            logger.error(f"Failed to load repos.yaml: {e}")

    def _load_governance_config(self) -> None:
        """Load governance.yaml configuration."""
        config_file = self.config_dir / "governance.yaml"
        if not config_file.exists():
            logger.debug(f"governance.yaml not found at {config_file}")
            self.governance = GovernanceConfig()
            return

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            self.governance = GovernanceConfig.from_dict(data)
            logger.debug("Loaded governance config")
        except Exception as e:
            logger.error(f"Failed to load governance.yaml: {e}")
            self.governance = GovernanceConfig()

    def _load_skills_config(self) -> None:
        """Load skills.yaml configuration."""
        config_file = self.config_dir / "skills.yaml"
        if not config_file.exists():
            logger.debug(f"skills.yaml not found at {config_file}")
            self.skills = SkillsConfig()
            return

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            self.skills = SkillsConfig.from_dict(data)
            logger.debug("Loaded skills config")
        except Exception as e:
            logger.error(f"Failed to load skills.yaml: {e}")
            self.skills = SkillsConfig()

    def _load_personas_config(self) -> None:
        """Load personas.yaml configuration (optional)."""
        config_file = self.config_dir / "personas.yaml"
        if not config_file.exists():
            logger.debug(f"personas.yaml not found at {config_file}")
            return

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            self.personas = PersonasConfig.from_dict(data)
            logger.debug("Loaded personas config")
        except Exception as e:
            logger.error(f"Failed to load personas.yaml: {e}")

    def get_repo(self, slug: str) -> Optional[RepoConfig]:
        """Get repo config by slug.

        Args:
            slug: Repo slug

        Returns:
            RepoConfig if found, None otherwise.
        """
        for repo in self.repos:
            if repo.slug == slug:
                return repo
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert all configs to dictionary.

        Returns:
            Dictionary representation of all configs.
        """
        return {
            "domain": self.domain.to_dict() if self.domain else None,
            "repos": [r.to_dict() for r in self.repos],
            "governance": self.governance.to_dict() if self.governance else None,
            "skills": self.skills.to_dict() if self.skills else None,
            "personas": self.personas.to_dict() if self.personas else None,
        }

    def to_json(self) -> str:
        """Convert all configs to JSON.

        Returns:
            JSON string representation of all configs.
        """
        return json.dumps(self.to_dict(), indent=2)
