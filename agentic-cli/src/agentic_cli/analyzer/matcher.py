"""Skill matcher — matches project analysis results against the skills registry to determine which skills to install."""

import json
from pathlib import Path
from typing import Any

from agentic_cli.analyzer.detector import ProjectAnalysis


class SkillMatch:
    """A matched skill from the registry."""

    def __init__(self, name: str, description: str, reason: str, tags: list[str], mcp: dict | None = None):
        self.name = name
        self.description = description
        self.reason = reason
        self.tags = tags
        self.mcp = mcp

    def to_dict(self) -> dict[str, Any]:
        d = {"name": self.name, "description": self.description, "reason": self.reason, "tags": self.tags}
        if self.mcp:
            d["mcp"] = self.mcp
        return d


def load_registry(registry_path: Path) -> dict:
    """Load the skills registry from registry.json."""
    registry_file = registry_path / "registry.json"
    if not registry_file.exists():
        raise FileNotFoundError(f"Registry not found at {registry_file}")
    return json.loads(registry_file.read_text())


def match_skills(
    analysis: ProjectAnalysis,
    registry: dict,
    mcp_servers: list[str] | None = None,
) -> list[SkillMatch]:
    """Match project analysis against registry skills.

    Args:
        analysis: Project analysis results
        registry: Loaded registry.json data
        mcp_servers: List of configured MCP server names (e.g., ["bitbucket", "jira"])

    Returns:
        List of matched skills, sorted by relevance
    """
    mcp_servers = mcp_servers or []
    matches: list[SkillMatch] = []
    dep_lower = [d.lower() for d in analysis.dependencies]

    for skill in registry.get("skills", []):
        name = skill["name"]
        description = skill.get("description", "")
        tags = skill.get("tags", [])
        auto_detect = skill.get("auto_detect", {})
        mcp = skill.get("mcp")

        # Check MCP skills — only match if the MCP server is configured
        if mcp:
            server_name = mcp.get("server", "")
            if server_name in mcp_servers:
                matches.append(SkillMatch(
                    name=name,
                    description=description,
                    reason=f"MCP server '{server_name}' is configured",
                    tags=tags,
                    mcp=mcp,
                ))
            continue

        # Check auto_detect rules
        if not auto_detect:
            continue

        # Check file presence
        detect_files = auto_detect.get("files", [])
        matched_file = None
        for f in detect_files:
            if analysis.project_files.get(f, False):
                matched_file = f
                break

        # Check dependency presence (ANY match)
        detect_deps = auto_detect.get("dependencies", [])
        matched_dep = None
        for dep_pattern in detect_deps:
            if any(dep_pattern.lower() in d for d in dep_lower):
                matched_dep = dep_pattern
                break

        # Check compound dependencies (ALL must match)
        detect_deps_all = auto_detect.get("dependencies_all", [])
        matched_deps_all = None
        if detect_deps_all:
            all_found = []
            for dep_pattern in detect_deps_all:
                if any(dep_pattern.lower() in d for d in dep_lower):
                    all_found.append(dep_pattern)
            if len(all_found) == len(detect_deps_all):
                matched_deps_all = all_found

        # Check source patterns — if specified, at least one must be found
        source_patterns = auto_detect.get("source_patterns", [])
        source_pattern_ok = True
        if source_patterns:
            analysis_patterns = getattr(analysis, "source_patterns", [])
            source_pattern_ok = bool(set(source_patterns) & set(analysis_patterns))

        # A skill matches if EITHER file or dependency matches
        # For dependencies_all, ALL listed deps must be present
        reasons = []
        if matched_file:
            reasons.append(f"Found file '{matched_file}'")
        if matched_dep:
            reasons.append(f"Found dependency '{matched_dep}'")
        if matched_deps_all:
            reasons.append(f"Found all dependencies: {', '.join(matched_deps_all)}")

        if not reasons:
            continue

        # If source_patterns are specified but none found, skip this skill
        if source_patterns and not source_pattern_ok:
            continue

        matches.append(SkillMatch(
            name=name,
            description=description,
            reason=" and ".join(reasons),
            tags=tags,
        ))

    return matches


def get_suggested_skills(
    analysis: ProjectAnalysis,
    registry: dict,
    installed_skills: list[str],
    mcp_servers: list[str] | None = None,
) -> list[SkillMatch]:
    """Get skills that could be relevant but weren't auto-matched.

    Returns skills whose tags overlap with detected languages/frameworks
    but weren't auto-detected.
    """
    mcp_servers = mcp_servers or []
    suggestions: list[SkillMatch] = []

    # Build a set of relevant tags from the analysis
    relevant_tags = set()
    for lang in analysis.languages:
        relevant_tags.add(lang.lower())
    for fw in analysis.frameworks:
        relevant_tags.add(fw.lower().replace(".", ""))
    if analysis.has_docker:
        relevant_tags.add("docker")
    for ci in analysis.ci_cd:
        relevant_tags.add(ci.lower())
    for db in analysis.databases:
        relevant_tags.add(db.lower())

    # Mutual exclusion groups — if one member is installed, don't suggest the others
    _exclusion_groups = [
        {"java-maven", "java-gradle"},
        {"python-fastapi", "python-django", "python-flask"},
        {"ci-jenkins", "ci-github-actions"},
    ]
    excluded_skills: set[str] = set()
    for group in _exclusion_groups:
        if group & set(installed_skills):
            excluded_skills |= group - set(installed_skills)

    for skill in registry.get("skills", []):
        name = skill["name"]
        if name in installed_skills:
            continue
        if name in excluded_skills:
            continue

        tags = skill.get("tags", [])
        mcp = skill.get("mcp")

        # For MCP skills, suggest if not already installed and MCP is available
        if mcp:
            server_name = mcp.get("server", "")
            if server_name in mcp_servers and name not in installed_skills:
                suggestions.append(SkillMatch(
                    name=name,
                    description=skill.get("description", ""),
                    reason=f"MCP server '{server_name}' is available",
                    tags=tags,
                    mcp=mcp,
                ))
            continue

        # Check tag overlap
        tag_overlap = set(t.lower() for t in tags) & relevant_tags
        if tag_overlap:
            suggestions.append(SkillMatch(
                name=name,
                description=skill.get("description", ""),
                reason=f"Related tags: {', '.join(sorted(tag_overlap))}",
                tags=tags,
            ))

    return suggestions


def detect_mcp_servers(project_path: Path) -> list[str]:
    """Detect configured MCP servers by checking known config files."""
    servers: set[str] = set()

    # Check Windsurf config
    windsurf_config = project_path / ".windsurf" / "mcp_config.json"
    if windsurf_config.exists():
        _extract_mcp_names(windsurf_config, "mcpServers", servers)

    # Check OpenCode config
    opencode_config = Path.home() / ".config" / "opencode" / "config.json"
    if opencode_config.exists():
        _extract_mcp_names(opencode_config, "mcp", servers)

    # Check global Windsurf config
    global_windsurf = Path.home() / ".codeium" / "windsurf" / "mcp_config.json"
    if global_windsurf.exists():
        _extract_mcp_names(global_windsurf, "mcpServers", servers)

    return sorted(servers)


def _extract_mcp_names(config_path: Path, key: str, servers: set[str]) -> None:
    """Extract MCP server names from a config file."""
    try:
        data = json.loads(config_path.read_text())
        mcp_section = data.get(key, {})
        for name in mcp_section:
            servers.add(name.lower())
    except (OSError, json.JSONDecodeError):
        pass


# --- Skill Proposals (agent-generated) ---

PROPOSALS_DIR = Path.home() / ".keel" / "proposals"


class SkillProposal:
    """A proposed skill generated by the onboard agent."""

    def __init__(
        self,
        skill_name: str,
        description: str,
        tags: list[str],
        reason: str,
        auto_detect: dict[str, Any],
        content: str = "",
        project: str = "",
    ):
        self.skill_name = skill_name
        self.description = description
        self.tags = tags
        self.reason = reason
        self.auto_detect = auto_detect
        self.content = content
        self.project = project

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "description": self.description,
            "tags": self.tags,
            "reason": self.reason,
            "auto_detect": self.auto_detect,
            "content": self.content,
            "project": self.project,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillProposal":
        return cls(
            skill_name=data["skill_name"],
            description=data.get("description", ""),
            tags=data.get("tags", []),
            reason=data.get("reason", ""),
            auto_detect=data.get("auto_detect", {}),
            content=data.get("content", ""),
            project=data.get("project", ""),
        )


def save_proposals(proposals: list[SkillProposal], project_name: str) -> Path:
    """Save skill proposals to disk for later review.

    Returns:
        Path to the saved proposals file.
    """
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = PROPOSALS_DIR / f"{project_name}.json"
    data = {
        "project": project_name,
        "proposals": [p.to_dict() for p in proposals],
    }
    file_path.write_text(json.dumps(data, indent=2))
    return file_path


def load_proposals(project_name: str | None = None) -> list[SkillProposal]:
    """Load pending skill proposals.

    If project_name is given, load proposals for that project.
    Otherwise, load all proposals across projects.
    """
    if not PROPOSALS_DIR.exists():
        return []

    proposals: list[SkillProposal] = []

    if project_name:
        file_path = PROPOSALS_DIR / f"{project_name}.json"
        if file_path.exists():
            data = json.loads(file_path.read_text())
            for p in data.get("proposals", []):
                p["project"] = data.get("project", project_name)
                proposals.append(SkillProposal.from_dict(p))
    else:
        for file_path in PROPOSALS_DIR.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                proj = data.get("project", file_path.stem)
                for p in data.get("proposals", []):
                    p["project"] = proj
                    proposals.append(SkillProposal.from_dict(p))
            except (json.JSONDecodeError, OSError):
                continue

    return proposals


def accept_proposal(
    proposal: SkillProposal,
    registry_path: Path,
) -> bool:
    """Accept a skill proposal: add to registry.json and create SKILL.md.

    Args:
        proposal: The proposal to accept.
        registry_path: Path to the skills registry root dir.

    Returns:
        True if successful.
    """
    registry_file = registry_path / "registry.json"
    if not registry_file.exists():
        return False

    # 1. Add to registry.json
    registry = json.loads(registry_file.read_text())
    skills = registry.get("skills", [])

    # Check for duplicate
    existing_names = {s["name"] for s in skills}
    if proposal.skill_name in existing_names:
        return False

    entry: dict[str, Any] = {
        "name": proposal.skill_name,
        "description": proposal.description,
        "tags": proposal.tags,
    }
    if proposal.auto_detect:
        entry["auto_detect"] = proposal.auto_detect

    skills.append(entry)
    registry["skills"] = skills
    registry_file.write_text(json.dumps(registry, indent=2) + "\n")

    # 2. Create SKILL.md in skills/<name>/
    skill_dir = registry_path / "skills" / proposal.skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(proposal.content)

    return True


def remove_proposal(project_name: str, skill_name: str) -> bool:
    """Remove a single proposal from the pending list."""
    file_path = PROPOSALS_DIR / f"{project_name}.json"
    if not file_path.exists():
        return False

    data = json.loads(file_path.read_text())
    original_count = len(data.get("proposals", []))
    data["proposals"] = [
        p for p in data.get("proposals", []) if p.get("skill_name") != skill_name
    ]

    if len(data["proposals"]) == original_count:
        return False

    if data["proposals"]:
        file_path.write_text(json.dumps(data, indent=2))
    else:
        file_path.unlink()

    return True
