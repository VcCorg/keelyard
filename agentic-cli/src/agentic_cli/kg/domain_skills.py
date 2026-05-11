"""Domain skills management — discover, inject, validate, and evolve skills.

This module handles:
  - Discovering skills from the superpowers repo (or any skills source)
  - Injecting skills into a domain-context repo as git submodule or copy
  - Generating skills manifest (tracking validation status)
  - Skill validation recording
  - Skill forking for domain customization
  - Loading domain-validated skills for code onboard
"""

import json
import logging
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default superpowers repo
DEFAULT_SUPERPOWERS_URL = "https://github.com/venkatchinta/superpowers.git"

# Skills that are available in superpowers
# (auto-discovered at runtime, but listed here for reference)
SUPERPOWERS_SKILLS = [
    "brainstorming",
    "dispatching-parallel-agents",
    "executing-plans",
    "finishing-a-development-branch",
    "receiving-code-review",
    "requesting-code-review",
    "subagent-driven-development",
    "systematic-debugging",
    "test-driven-development",
    "using-git-worktrees",
    "using-superpowers",
    "verification-before-completion",
    "writing-plans",
    "writing-skills",
]


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------

def discover_skills(skills_source: Path) -> list[dict[str, Any]]:
    """Discover skills in a skills source directory.

    Each skill is a directory under ``skills/`` containing at least a
    ``SKILL.md`` file.

    Args:
        skills_source: Path to superpowers repo or any skills repo.

    Returns:
        List of skill dicts with name, path, description, files.
    """
    skills_dir = skills_source / "skills"
    if not skills_dir.is_dir():
        logger.warning(f"No skills/ directory in {skills_source}")
        return []

    skills = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue

        description = _extract_skill_description(skill_md)
        files = [f.name for f in entry.iterdir() if f.is_file()]

        skills.append({
            "name": entry.name,
            "path": str(entry),
            "description": description,
            "files": files,
            "has_skill_md": True,
        })

    return skills


def _extract_skill_description(skill_md: Path) -> str:
    """Extract a short description from SKILL.md (first paragraph after title)."""
    try:
        text = skill_md.read_text(encoding="utf-8")
        # Skip frontmatter
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                text = text[end + 3:].strip()
        # Skip title
        lines = text.split("\n")
        desc_lines = []
        past_title = False
        for line in lines:
            stripped = line.strip()
            if not past_title:
                if stripped.startswith("#"):
                    past_title = True
                    continue
                if not stripped:
                    continue
                # No title found, treat as description
                past_title = True
            if past_title:
                if not stripped:
                    if desc_lines:
                        break
                    continue
                desc_lines.append(stripped)
        return " ".join(desc_lines)[:200] if desc_lines else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Skill injection into domain-context repo
# ---------------------------------------------------------------------------

def clone_superpowers(
    target_dir: Path,
    url: str = DEFAULT_SUPERPOWERS_URL,
    branch: str = "main",
    depth: int = 1,
) -> Path:
    """Clone superpowers repo to target directory.

    Args:
        target_dir: Where to clone (parent dir).
        url: Git URL.
        branch: Branch to clone.
        depth: Git clone depth.

    Returns:
        Path to cloned repo.
    """
    clone_path = target_dir / "superpowers"
    if clone_path.exists():
        logger.info(f"Superpowers already cloned at {clone_path}")
        return clone_path

    subprocess.run(
        ["git", "clone", "--depth", str(depth), "--branch", branch, url, str(clone_path)],
        capture_output=True, check=True,
    )
    return clone_path


def inject_skills_as_submodule(
    domain_context_dir: Path,
    superpowers_url: str = DEFAULT_SUPERPOWERS_URL,
    branch: str = "main",
) -> Path:
    """Add superpowers as a git submodule under .skills/superpowers/.

    Args:
        domain_context_dir: The domain-context repo path.
        superpowers_url: Git URL for superpowers.
        branch: Branch to track.

    Returns:
        Path to the submodule.
    """
    submodule_path = domain_context_dir / ".skills" / "superpowers"
    if submodule_path.exists():
        logger.info("Superpowers submodule already exists")
        return submodule_path

    (domain_context_dir / ".skills").mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "submodule", "add", "--branch", branch,
         superpowers_url, ".skills/superpowers"],
        cwd=str(domain_context_dir),
        capture_output=True, check=True,
    )
    return submodule_path


def inject_skills_copy(
    domain_context_dir: Path,
    superpowers_path: Path,
    skills_to_inject: Optional[list[str]] = None,
) -> list[str]:
    """Copy superpowers skills into domain-context repo.

    Args:
        domain_context_dir: The domain-context repo path.
        superpowers_path: Path to cloned superpowers repo.
        skills_to_inject: List of skill names to inject (None = all).

    Returns:
        List of injected skill names.
    """
    discovered = discover_skills(superpowers_path)
    if skills_to_inject:
        discovered = [s for s in discovered if s["name"] in skills_to_inject]

    injected = []
    skills_dir = domain_context_dir / ".skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    for skill in discovered:
        src = Path(skill["path"])
        dest = skills_dir / skill["name"]
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        injected.append(skill["name"])

    return injected


# ---------------------------------------------------------------------------
# Skills manifest
# ---------------------------------------------------------------------------

def generate_skills_manifest(
    domain_context_dir: Path,
    domain: str,
    skills: list[dict[str, Any]],
    superpowers_url: str = DEFAULT_SUPERPOWERS_URL,
    superpowers_commit: str = "main",
) -> Path:
    """Generate .domain/skills-manifest.json tracking all injected skills.

    Args:
        domain_context_dir: Domain-context repo path.
        domain: Domain slug.
        skills: List of skill dicts from discover_skills().
        superpowers_url: URL of the superpowers repo.
        superpowers_commit: Commit/branch of superpowers used.

    Returns:
        Path to the generated manifest.
    """
    domain_dir = domain_context_dir / ".domain"
    domain_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    manifest = {
        "domain": domain,
        "created_at": now,
        "updated_at": now,
        "superpowers_url": superpowers_url,
        "superpowers_version": superpowers_commit,
        "skills": {},
    }

    for skill in skills:
        manifest["skills"][skill["name"]] = {
            "source": "superpowers",
            "status": "injected",
            "validated": False,
            "validation_date": None,
            "customized": False,
            "description": skill.get("description", ""),
            "files": skill.get("files", []),
            "notes": "",
        }

    manifest_path = domain_dir / "skills-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path


def load_skills_manifest(domain_context_dir: Path) -> dict[str, Any]:
    """Load the skills manifest from a domain-context repo."""
    manifest_path = domain_context_dir / ".domain" / "skills-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def update_skill_status(
    domain_context_dir: Path,
    skill_name: str,
    status: str,
    validated: Optional[bool] = None,
    notes: Optional[str] = None,
) -> bool:
    """Update a skill's status in the manifest.

    Args:
        domain_context_dir: Domain-context repo path.
        skill_name: Skill to update.
        status: New status (injected, validated, needs-tuning, broken, forked).
        validated: Override validated flag.
        notes: Notes about the change.

    Returns:
        True if updated, False if skill not found.
    """
    manifest = load_skills_manifest(domain_context_dir)
    if not manifest or skill_name not in manifest.get("skills", {}):
        return False

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    skill = manifest["skills"][skill_name]
    skill["status"] = status
    if validated is not None:
        skill["validated"] = validated
        if validated:
            skill["validation_date"] = now
    if notes is not None:
        skill["notes"] = notes
    manifest["updated_at"] = now

    manifest_path = domain_context_dir / ".domain" / "skills-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return True


# ---------------------------------------------------------------------------
# Skills evolution log
# ---------------------------------------------------------------------------

def log_skill_event(
    domain_context_dir: Path,
    skill_name: str,
    event: str,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Append an event to the skills evolution log.

    Args:
        domain_context_dir: Domain-context repo path.
        skill_name: Skill name.
        event: Event type (injected, validated, forked, customized, contributed).
        details: Additional event details.
    """
    domain_dir = domain_context_dir / ".domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    log_path = domain_dir / "skills-evolution.json"

    if log_path.exists():
        try:
            log_data = json.loads(log_path.read_text())
        except (json.JSONDecodeError, OSError):
            log_data = {}
    else:
        log_data = {}

    if skill_name not in log_data:
        log_data[skill_name] = []

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry = {"timestamp": now, "event": event}
    if details:
        entry.update(details)

    log_data[skill_name].append(entry)
    log_path.write_text(json.dumps(log_data, indent=2))


# ---------------------------------------------------------------------------
# Skill forking (domain customization)
# ---------------------------------------------------------------------------

def fork_skill(
    domain_context_dir: Path,
    skill_name: str,
    domain: str,
    reason: str = "",
) -> Optional[Path]:
    """Fork a superpowers skill for domain-specific customization.

    Copies the skill to a ``<skill>-<domain>`` directory and updates
    the manifest and evolution log.

    Args:
        domain_context_dir: Domain-context repo path.
        skill_name: Name of the superpowers skill to fork.
        domain: Domain slug.
        reason: Reason for forking.

    Returns:
        Path to the forked skill directory, or None on failure.
    """
    # Find source skill
    source = domain_context_dir / ".skills" / skill_name
    if not source.exists():
        # Try superpowers submodule
        source = domain_context_dir / ".skills" / "superpowers" / "skills" / skill_name
    if not source.exists():
        logger.warning(f"Skill '{skill_name}' not found")
        return None

    forked_name = f"{skill_name}-{domain}"
    dest = domain_context_dir / ".skills" / forked_name
    if dest.exists():
        shutil.rmtree(dest)

    shutil.copytree(source, dest)

    # Add customization notes
    notes_path = dest / "CUSTOMIZATION_NOTES.md"
    notes_path.write_text(
        f"# Customization Notes: {forked_name}\n\n"
        f"**Forked from**: {skill_name} (superpowers)\n"
        f"**Domain**: {domain}\n"
        f"**Reason**: {reason or 'Domain-specific customization'}\n"
        f"**Date**: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"## Changes\n\n"
        f"_Document changes from the upstream skill here._\n"
    )

    # Update manifest
    manifest = load_skills_manifest(domain_context_dir)
    if manifest and "skills" in manifest:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest["skills"][forked_name] = {
            "source": "superpowers",
            "status": "forked",
            "validated": False,
            "validation_date": None,
            "customized": True,
            "customization_reason": reason,
            "upstream_skill": skill_name,
            "description": manifest["skills"].get(skill_name, {}).get("description", ""),
            "files": [f.name for f in dest.iterdir() if f.is_file()],
            "notes": "",
        }
        manifest["updated_at"] = now
        manifest_path = domain_context_dir / ".domain" / "skills-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

    # Log event
    log_skill_event(domain_context_dir, forked_name, "forked", {
        "upstream": skill_name,
        "reason": reason,
    })

    return dest


# ---------------------------------------------------------------------------
# Loading domain skills for code onboard
# ---------------------------------------------------------------------------

def load_domain_skills(domain_context_dir: Path) -> dict[str, dict[str, Any]]:
    """Load domain-validated and domain-customized skills for onboard.

    Args:
        domain_context_dir: Path to domain-context repo.

    Returns:
        Dict of skill_name -> skill info (path, validated, metadata).
    """
    manifest = load_skills_manifest(domain_context_dir)
    if not manifest:
        return {}

    skills = {}
    skills_dir = domain_context_dir / ".skills"

    for skill_name, skill_info in manifest.get("skills", {}).items():
        # Check direct .skills/<name>
        skill_path = skills_dir / skill_name
        if not skill_path.exists():
            # Try superpowers submodule
            skill_path = skills_dir / "superpowers" / "skills" / skill_name
        if not skill_path.exists():
            continue

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        skills[skill_name] = {
            "name": skill_name,
            "path": skill_path,
            "validated": skill_info.get("validated", False),
            "customized": skill_info.get("customized", False),
            "status": skill_info.get("status", "injected"),
            "description": skill_info.get("description", ""),
            "source": skill_info.get("source", "superpowers"),
        }

    return skills


def install_domain_skill(
    skill_name: str,
    skill_path: Path,
    target_project: Path,
) -> bool:
    """Install a domain skill into a project's .skills/ directory.

    Args:
        skill_name: Name of the skill.
        skill_path: Source path in domain-context repo.
        target_project: Target project path.

    Returns:
        True if installed successfully.
    """
    dest = target_project / ".skills" / skill_name
    if dest.exists():
        shutil.rmtree(dest)

    try:
        shutil.copytree(skill_path, dest)
        return True
    except Exception as e:
        logger.warning(f"Failed to install skill {skill_name}: {e}")
        return False


# ---------------------------------------------------------------------------
# Bootstrap domain from superpowers (full pipeline)
# ---------------------------------------------------------------------------

def bootstrap_domain_skills(
    domain_context_dir: Path,
    domain: str,
    superpowers_url: str = DEFAULT_SUPERPOWERS_URL,
    use_submodule: bool = True,
    skills_to_inject: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Full pipeline: inject superpowers skills into a domain-context repo.

    This is the main entry point for Phase 1 skill injection.

    Args:
        domain_context_dir: Domain-context repo path (must be git-initialized).
        domain: Domain slug.
        superpowers_url: Git URL for superpowers.
        use_submodule: If True, add as git submodule; else copy skills.
        skills_to_inject: Specific skill names to inject (None = all).

    Returns:
        Dict with injected skills info, manifest path, etc.
    """
    import tempfile

    injected_skills = []

    if use_submodule:
        # Add as git submodule
        try:
            submodule_path = inject_skills_as_submodule(
                domain_context_dir, superpowers_url,
            )
            # Discover skills from the submodule
            superpowers_root = submodule_path
            if (submodule_path / "skills").is_dir():
                superpowers_root = submodule_path
            discovered = discover_skills(superpowers_root)

            if skills_to_inject:
                discovered = [s for s in discovered if s["name"] in skills_to_inject]

            injected_skills = discovered
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git submodule failed: {e}, falling back to copy")
            use_submodule = False

    if not use_submodule:
        # Clone to temp and copy
        with tempfile.TemporaryDirectory() as tmp:
            clone_path = clone_superpowers(Path(tmp), superpowers_url)
            discovered = discover_skills(clone_path)
            injected_names = inject_skills_copy(
                domain_context_dir, clone_path, skills_to_inject,
            )
            injected_skills = [s for s in discovered if s["name"] in injected_names]

    # Generate manifest
    manifest_path = generate_skills_manifest(
        domain_context_dir, domain, injected_skills,
        superpowers_url=superpowers_url,
    )

    # Log injection events
    for skill in injected_skills:
        log_skill_event(domain_context_dir, skill["name"], "injected", {
            "source": "superpowers",
            "url": superpowers_url,
        })

    # Generate SKILLS_MANIFEST.md (human-readable)
    manifest_md = _generate_skills_manifest_md(domain, injected_skills)
    md_path = domain_context_dir / "SKILLS_MANIFEST.md"
    md_path.write_text(manifest_md)

    return {
        "injected_skills": [s["name"] for s in injected_skills],
        "skill_count": len(injected_skills),
        "manifest_path": manifest_path,
        "manifest_md_path": md_path,
        "use_submodule": use_submodule,
        "superpowers_url": superpowers_url,
    }


def _generate_skills_manifest_md(domain: str, skills: list[dict]) -> str:
    """Generate a human-readable SKILLS_MANIFEST.md."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"# Skills Manifest — {domain}\n",
        f"> Generated: {now}\n",
        f"## Superpowers Skills (Injected)\n",
        "| Skill | Description | Status | Validated |",
        "|-------|-------------|--------|-----------|",
    ]

    for skill in sorted(skills, key=lambda s: s["name"]):
        desc = skill.get("description", "")[:60]
        lines.append(f"| `{skill['name']}` | {desc} | Injected | — |")

    lines.extend([
        "",
        "## Domain-Customized Skills\n",
        "_None yet. Use `dva domain fork-skill` to customize a skill._\n",
        "## Validation Checklist\n",
        "For each skill, validate against real development tasks:\n",
        "```bash",
        f'dva domain validate-skills {domain} --skill <name> --feedback works',
        "```\n",
        "| Skill | Tested On | Feedback | Status |",
        "|-------|-----------|----------|--------|",
    ])

    for skill in sorted(skills, key=lambda s: s["name"]):
        lines.append(f"| `{skill['name']}` | — | — | Pending |")

    lines.append("")
    return "\n".join(lines)
