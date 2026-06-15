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


@dataclass
class GovernanceConfig:
    """Configuration for domain governance rules."""

    branch_pattern: str = "^(feat|fix|docs|style|refactor|test|chore)/[A-Z]+-[0-9]+-.*$"
    require_pre_push_hook: bool = True
    require_ci_gates: bool = True
    require_code_review: bool = True
    min_reviewers: int = 1
    require_tests: bool = True
    test_coverage_min: float = 80.0

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
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "validation_required": self.validation_required,
            "auto_inject_superpowers": self.auto_inject_superpowers,
            "allow_custom_skills": self.allow_custom_skills,
            "skill_priority_order": self.skill_priority_order,
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

        self._load_all()

    def _load_all(self) -> None:
        """Load all configuration files."""
        self._load_domain_config()
        self._load_repos_config()
        self._load_governance_config()
        self._load_skills_config()

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
        }

    def to_json(self) -> str:
        """Convert all configs to JSON.

        Returns:
            JSON string representation of all configs.
        """
        return json.dumps(self.to_dict(), indent=2)
