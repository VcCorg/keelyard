"""Host-agnostic git helpers for submodule management.

Supports repositories hosted on Bitbucket (Server/Data Center & Cloud),
GitLab, GitHub, and any other git remote. Avoids hardcoding default branch
names (e.g. ``main``) which differ across hosts and repos (Bitbucket Server
repos commonly default to ``master`` or ``develop``).
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default network timeout (seconds) for remote git queries.
LS_REMOTE_TIMEOUT = 30


def _is_local_path(url: str) -> bool:
    """Return True if the URL refers to a local filesystem path.

    Local paths (used when linking a locally-created meta-repo) require
    ``protocol.file.allow=always`` for ``git submodule add`` due to the
    CVE-2022-39253 hardening in modern git. Remote HTTPS/SSH URLs
    (bitbucket/gitlab/github) are unaffected.
    """
    if not url:
        return False
    if url.startswith("file://"):
        return True
    # Remote schemes / scp-like SSH syntax are NOT local.
    if "://" in url or url.startswith("git@"):
        return False
    return True


def detect_git_host(url: str) -> str:
    """Identify the git host from a clone URL.

    Args:
        url: Git clone URL (HTTPS or SSH) or local path.

    Returns:
        One of: ``bitbucket``, ``gitlab``, ``github``, or ``unknown``.
    """
    if not url:
        return "unknown"
    u = url.lower()
    if "bitbucket" in u:
        return "bitbucket"
    if "gitlab" in u:
        return "gitlab"
    if "github" in u:
        return "github"
    return "unknown"


def detect_default_branch(url: str) -> Optional[str]:
    """Detect the default branch of a remote repository.

    Uses ``git ls-remote --symref <url> HEAD`` which works uniformly across
    Bitbucket, GitLab, GitHub, and local paths over both HTTPS and SSH.

    Args:
        url: Git clone URL or local path.

    Returns:
        The default branch name (e.g. ``main``, ``master``, ``develop``), or
        ``None`` if detection fails (network/auth error, no symref).
    """
    if not url:
        return None
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--symref", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=LS_REMOTE_TIMEOUT,
        )
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug(f"ls-remote failed for {url}: {e}")
        return None

    if result.returncode != 0:
        logger.debug(f"ls-remote non-zero for {url}: {result.stderr.strip()}")
        return None

    # Expected line: 'ref: refs/heads/<branch>\tHEAD'
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("ref:") and "HEAD" in line:
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith("refs/heads/"):
                branch = parts[1][len("refs/heads/"):]
                logger.debug(f"Detected default branch '{branch}' for {url}")
                return branch
    return None


def add_submodule(
    repo_root: Path,
    url: str,
    path: str,
    branch: Optional[str] = None,
    *,
    check: bool = True,
) -> Optional[str]:
    """Add a git submodule, pinning to the correct default branch per host.

    If ``branch`` is not provided, the remote's default branch is auto-detected
    so the submodule works regardless of host (Bitbucket/GitLab/GitHub) and the
    repo's default branch (``main``/``master``/``develop``). If detection fails,
    the submodule is added without an explicit branch, letting git use the
    remote HEAD.

    Args:
        repo_root: Path to the superproject (where ``.gitmodules`` lives).
        url: Submodule clone URL or local path.
        path: Submodule path relative to ``repo_root``.
        branch: Explicit branch to pin. Auto-detected if ``None``.
        check: Raise on git failure (default True).

    Returns:
        The branch that was used (explicit or detected), or ``None`` if added
        without an explicit branch.

    Raises:
        subprocess.CalledProcessError: If the submodule add fails and ``check``.
    """
    resolved_branch = branch or detect_default_branch(url)

    cmd = ["git"]
    # Local-path submodules require explicit file-protocol opt-in on modern
    # git (CVE-2022-39253). Remote bitbucket/gitlab/github URLs are unaffected.
    if _is_local_path(url):
        cmd += ["-c", "protocol.file.allow=always"]
    cmd += ["submodule", "add"]
    if resolved_branch:
        cmd += ["--branch", resolved_branch]
    cmd += [url, path]

    subprocess.run(
        cmd,
        cwd=str(repo_root),
        check=check,
        capture_output=True,
    )
    logger.debug(
        f"Added submodule {path} -> {url} "
        f"(branch={resolved_branch or 'remote-HEAD'})"
    )
    return resolved_branch
