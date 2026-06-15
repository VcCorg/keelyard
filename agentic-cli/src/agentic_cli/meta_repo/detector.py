"""Detect domain meta-repos by standard naming convention."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_domain_meta_repo(domain_slug: str, search_paths: list[Path] = None) -> Path | None:
    """Find domain-meta-repo by standard naming convention.

    Searches in standard locations:
    1. CWD / domain-<slug>-meta
    2. CWD parent / domain-<slug>-meta
    3. Configured workspace / domain-<slug>-meta
    4. Custom search paths (if provided)

    Args:
        domain_slug: Domain slug (e.g., "cwow-facility")
        search_paths: Optional list of additional paths to search

    Returns:
        Path to domain-meta-repo if found, None otherwise.
    """
    meta_repo_name = f"domain-{domain_slug}-meta"

    candidates = [
        Path.cwd() / meta_repo_name,
        Path.cwd().parent / meta_repo_name,
    ]

    # Search the configured code workspace, where `dva domain init-meta`
    # creates meta-repos: <workspace>/<domain>/domain-<domain>-meta
    workspace = _get_code_workspace()
    if workspace:
        candidates.append(workspace / domain_slug / meta_repo_name)
        candidates.append(workspace / meta_repo_name)

    # Add custom search paths. Each path is treated both as a direct
    # candidate and as a parent directory that may contain the meta-repo.
    if search_paths:
        for sp in search_paths:
            candidates.append(sp)
            candidates.append(sp / meta_repo_name)

    for candidate in candidates:
        if _is_valid_meta_repo(candidate):
            logger.debug(f"Found domain meta-repo at {candidate}")
            return candidate

    logger.debug(f"No domain meta-repo found for '{domain_slug}'")
    return None


def _get_code_workspace() -> Path | None:
    """Return the configured code workspace directory, if any.

    Reads the same global CLI config used by `dva code onboard` /
    `dva domain init-meta` so detection matches creation location.
    """
    config_file = Path.home() / ".agent-cli-agentic" / "config.json"
    if not config_file.exists():
        return None
    try:
        import json

        data = json.loads(config_file.read_text())
        workspace = data.get("code_workspace")
        return Path(workspace) if workspace else None
    except (json.JSONDecodeError, OSError):
        return None


def _is_valid_meta_repo(path: Path) -> bool:
    """Check if a directory is a valid domain meta-repo.

    A valid meta-repo must have:
    - .platform/ directory
    - .platform/config/ directory
    - .gitmodules file (if git-initialized)

    Args:
        path: Path to check

    Returns:
        True if valid meta-repo structure, False otherwise.
    """
    if not path.exists() or not path.is_dir():
        return False

    platform_dir = path / ".platform"
    config_dir = platform_dir / "config"

    # Minimum requirement: .platform/config/ exists
    if not config_dir.exists():
        return False

    return True


def is_git_initialized(meta_repo_path: Path) -> bool:
    """Check if meta-repo is a git repository.

    Args:
        meta_repo_path: Path to meta-repo

    Returns:
        True if .git directory exists, False otherwise.
    """
    return (meta_repo_path / ".git").exists()


def has_submodules(meta_repo_path: Path) -> bool:
    """Check if meta-repo has git submodules configured.

    Args:
        meta_repo_path: Path to meta-repo

    Returns:
        True if .gitmodules file exists, False otherwise.
    """
    return (meta_repo_path / ".gitmodules").exists()
