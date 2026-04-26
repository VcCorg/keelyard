"""Skill Registry - publish, share, and discover skills via Git."""

import json
import shutil
import subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SkillVersion:
    """A specific version of a published skill."""

    version: str
    published: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    quality_score: float = 0.0
    effectiveness: float = 0.0
    accuracy_delta: float = 0.0
    latency_delta: float = 0.0
    helpfulness_delta: float = 0.0
    path: str = ""  # Path in registry


@dataclass
class SkillMetadata:
    """Metadata for a published skill."""

    id: str
    name: str
    description: str
    domain: str
    role: str
    author: str = "unknown"
    organization: str = ""
    tags: List[str] = field(default_factory=list)
    visibility: str = "team"  # private, team, public
    versions: Dict[str, SkillVersion] = field(default_factory=dict)
    latest_version: str = ""
    adopted_by: int = 0
    rating: float = 0.0
    downloads: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "role": self.role,
            "author": self.author,
            "organization": self.organization,
            "tags": self.tags,
            "visibility": self.visibility,
            "versions": {
                v_id: asdict(v) for v_id, v in self.versions.items()
            },
            "latest_version": self.latest_version,
            "adopted_by": self.adopted_by,
            "rating": self.rating,
            "downloads": self.downloads,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillMetadata":
        """Create from dictionary."""
        versions = {
            v_id: SkillVersion(**v) for v_id, v in data.get("versions", {}).items()
        }
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            domain=data["domain"],
            role=data["role"],
            author=data.get("author", "unknown"),
            organization=data.get("organization", ""),
            tags=data.get("tags", []),
            visibility=data.get("visibility", "team"),
            versions=versions,
            latest_version=data.get("latest_version", ""),
            adopted_by=data.get("adopted_by", 0),
            rating=data.get("rating", 0.0),
            downloads=data.get("downloads", 0),
            last_updated=data.get("last_updated", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class RegistryIndex:
    """Registry index - catalog of all skills."""

    repository: str
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    skills: Dict[str, SkillMetadata] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repository": self.repository,
            "created": self.created,
            "updated": self.updated,
            "skills": {
                skill_id: metadata.to_dict()
                for skill_id, metadata in self.skills.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistryIndex":
        """Create from dictionary."""
        skills = {
            skill_id: SkillMetadata.from_dict(metadata)
            for skill_id, metadata in data.get("skills", {}).items()
        }
        return cls(
            repository=data["repository"],
            created=data.get("created", datetime.now(timezone.utc).isoformat()),
            updated=data.get("updated", datetime.now(timezone.utc).isoformat()),
            skills=skills,
        )


class GitSkillRegistry:
    """Manage skills in a Git repository."""

    def __init__(self, repo_url: str, local_path: Optional[Path] = None):
        """Initialize Git skill registry.

        Args:
            repo_url: Git repository URL
            local_path: Local path to clone/use (default: ~/.agentic-cli/registries/<name>)
        """
        self.repo_url = repo_url
        self.repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        if not local_path:
            local_path = Path.home() / ".agentic-cli" / "registries" / self.repo_name

        self.local_path = Path(local_path)
        self.index_file = self.local_path / "registry.json"

    def clone(self) -> bool:
        """Clone registry repository.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.local_path.exists():
                return True

            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", self.repo_url, str(self.local_path)],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone registry: {e.stderr.decode()}")

    def pull(self) -> bool:
        """Update registry from remote.

        Returns:
            True if successful
        """
        try:
            subprocess.run(
                ["git", "pull"],
                cwd=self.local_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def load_index(self) -> RegistryIndex:
        """Load registry index.

        Returns:
            RegistryIndex object
        """
        if not self.index_file.exists():
            return RegistryIndex(repository=self.repo_url)

        data = json.loads(self.index_file.read_text())
        return RegistryIndex.from_dict(data)

    def save_index(self, index: RegistryIndex) -> None:
        """Save registry index.

        Args:
            index: RegistryIndex to save
        """
        self.index_file.write_text(json.dumps(index.to_dict(), indent=2))

    def publish_skill(
        self,
        skill_path: Path,
        metadata: SkillMetadata,
        quality_score: float,
        effectiveness: float,
        deltas: Optional[Dict[str, float]] = None,
    ) -> str:
        """Publish a skill to registry.

        Args:
            skill_path: Path to skill directory
            metadata: Skill metadata
            quality_score: Quality score (0-100)
            effectiveness: Effectiveness score (0-10)
            deltas: Optional metric deltas from evaluation

        Returns:
            Skill ID
        """
        # Create domain/role directory structure
        skill_dir = (
            self.local_path
            / metadata.domain
            / metadata.id
            / metadata.latest_version
        )
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Copy skill files
        for item in skill_path.iterdir():
            dest = skill_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Create skill evaluation metadata
        eval_metadata = {
            "quality_score": quality_score,
            "effectiveness": effectiveness,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(skill_dir.relative_to(self.local_path)),
        }

        if deltas:
            eval_metadata["deltas"] = deltas

        eval_file = skill_dir / "evaluation.json"
        eval_file.write_text(json.dumps(eval_metadata, indent=2))

        # Update registry index
        index = self.load_index()
        version = SkillVersion(
            version=metadata.latest_version,
            quality_score=quality_score,
            effectiveness=effectiveness,
            accuracy_delta=deltas.get("accuracy", 0.0) if deltas else 0.0,
            latency_delta=deltas.get("latency_ms", 0.0) if deltas else 0.0,
            helpfulness_delta=deltas.get("helpfulness", 0.0) if deltas else 0.0,
            path=str(skill_dir.relative_to(self.local_path)),
        )

        if metadata.id not in index.skills:
            index.skills[metadata.id] = metadata
        else:
            # Update existing skill
            existing = index.skills[metadata.id]
            existing.versions[metadata.latest_version] = version
            existing.latest_version = metadata.latest_version
            existing.last_updated = datetime.now(timezone.utc).isoformat()

        metadata.versions[metadata.latest_version] = version
        index.skills[metadata.id] = metadata
        self.save_index(index)

        # Git operations
        self._git_commit_and_push(
            f"Publish {metadata.id} v{metadata.latest_version}"
        )

        return metadata.id

    def get_skill(self, skill_id: str, version: Optional[str] = None) -> Optional[Path]:
        """Get skill directory path.

        Args:
            skill_id: Skill ID
            version: Specific version (default: latest)

        Returns:
            Path to skill directory
        """
        index = self.load_index()
        if skill_id not in index.skills:
            return None

        metadata = index.skills[skill_id]
        version = version or metadata.latest_version

        if version not in metadata.versions:
            return None

        return self.local_path / metadata.versions[version].path

    def search(
        self,
        domain: Optional[str] = None,
        role: Optional[str] = None,
        min_effectiveness: float = 0.0,
        min_quality: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> List[SkillMetadata]:
        """Search registry for skills.

        Args:
            domain: Filter by domain
            role: Filter by role
            min_effectiveness: Minimum effectiveness score
            min_quality: Minimum quality score
            tags: Filter by tags (all must match)

        Returns:
            List of matching skills
        """
        index = self.load_index()
        results = []

        for skill_id, metadata in index.skills.items():
            # Apply filters
            if domain and metadata.domain != domain:
                continue
            if role and metadata.role != role:
                continue
            if (
                metadata.latest_version in metadata.versions
                and metadata.versions[metadata.latest_version].effectiveness
                < min_effectiveness
            ):
                continue
            if (
                metadata.latest_version in metadata.versions
                and metadata.versions[metadata.latest_version].quality_score
                < min_quality
            ):
                continue
            if tags and not all(tag in metadata.tags for tag in tags):
                continue

            results.append(metadata)

        # Sort by effectiveness (descending)
        results.sort(
            key=lambda s: s.versions[s.latest_version].effectiveness
            if s.latest_version in s.versions
            else 0.0,
            reverse=True,
        )

        return results

    def install_skill(self, skill_id: str, dest_path: Path, version: Optional[str] = None) -> bool:
        """Install skill from registry.

        Args:
            skill_id: Skill ID
            dest_path: Destination directory
            version: Specific version (default: latest)

        Returns:
            True if successful
        """
        source = self.get_skill(skill_id, version)
        if not source or not source.exists():
            return False

        dest_path.mkdir(parents=True, exist_ok=True)

        # Copy skill files
        for item in source.iterdir():
            if item.name in ["evaluation.json"]:
                continue  # Skip evaluation metadata
            dest = dest_path / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        return True

    def rate_skill(self, skill_id: str, rating: float, comment: str = "") -> bool:
        """Rate a skill.

        Args:
            skill_id: Skill ID
            rating: Rating (0-5)
            comment: Optional review comment

        Returns:
            True if successful
        """
        index = self.load_index()
        if skill_id not in index.skills:
            return False

        metadata = index.skills[skill_id]

        # Simple average (in production, would track all ratings)
        current_rating = metadata.rating
        metadata.rating = (current_rating + rating) / 2

        self.save_index(index)
        self._git_commit_and_push(f"Rate {skill_id}: {rating}/5")

        return True

    def _git_commit_and_push(self, message: str) -> bool:
        """Commit and push changes.

        Args:
            message: Commit message

        Returns:
            True if successful
        """
        try:
            subprocess.run(
                ["git", "add", "."],
                cwd=self.local_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.local_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "push"],
                cwd=self.local_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
