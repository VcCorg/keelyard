"""Host-agnostic git helpers for submodule management.

Supports repositories hosted on Bitbucket (Server/Data Center & Cloud),
GitLab, GitHub, and any other git remote. Avoids hardcoding default branch
names (e.g. ``main``) which differ across hosts and repos (Bitbucket Server
repos commonly default to ``master`` or ``develop``).
"""

import concurrent.futures
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default network timeout (seconds) for remote git queries.
LS_REMOTE_TIMEOUT = 30

# Parallelism for clone-free SHA resolution across linked repos.
SHA_RESOLVE_WORKERS = 8


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
    depth: Optional[int] = None,
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
        depth: If set, do a shallow clone to this depth (e.g. 1) to avoid
            fetching full history.
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
    if depth:
        cmd += ["--depth", str(depth)]
    cmd += [url, path]

    subprocess.run(
        cmd,
        cwd=str(repo_root),
        check=check,
        capture_output=True,
    )
    logger.debug(
        f"Added submodule {path} -> {url} "
        f"(branch={resolved_branch or 'remote-HEAD'}, depth={depth or 'full'})"
    )
    return resolved_branch


def resolve_remote_sha(
    url: str, branch: Optional[str] = None, *, timeout: int = LS_REMOTE_TIMEOUT
) -> Optional[tuple[str, Optional[str]]]:
    """Resolve a remote ref to its commit SHA *without cloning*.

    Uses ``git ls-remote`` (a cheap refs-only round-trip) instead of a full
    clone. When ``branch`` is given, resolves that branch tip; otherwise
    resolves the remote's default branch (symref HEAD).

    Args:
        url: Git clone URL or local path.
        branch: Branch to resolve. If ``None``, the default branch is used.

    Returns:
        ``(sha, branch)`` where ``branch`` is the resolved/detected branch name
        (may be ``None`` if only HEAD resolved), or ``None`` on failure.
    """
    if not url:
        return None
    try:
        if branch:
            res = subprocess.run(
                ["git", "ls-remote", url, f"refs/heads/{branch}"],
                capture_output=True, text=True, timeout=timeout,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.split()[0], branch
            # Branch ref missing — fall through to HEAD detection.
        res = subprocess.run(
            ["git", "ls-remote", "--symref", url, "HEAD"],
            capture_output=True, text=True, timeout=timeout,
        )
        if res.returncode != 0:
            logger.debug(f"ls-remote non-zero for {url}: {res.stderr.strip()}")
            return None
        sha: Optional[str] = None
        detected: Optional[str] = None
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("ref:") and "HEAD" in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith("refs/heads/"):
                    detected = parts[1][len("refs/heads/"):]
            elif line.endswith("\tHEAD") or line.endswith(" HEAD"):
                sha = line.split()[0]
        if sha:
            return sha, (branch or detected)
        return None
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug(f"ls-remote sha failed for {url}: {e}")
        return None


def resolve_remote_shas(
    items: list[tuple[str, str, Optional[str]]], *, max_workers: int = SHA_RESOLVE_WORKERS
) -> dict[str, Optional[tuple[str, Optional[str]]]]:
    """Resolve SHAs for many remotes in parallel (clone-free).

    Args:
        items: list of ``(key, url, branch)``. ``key`` identifies the result.
        max_workers: thread-pool size for the ``ls-remote`` calls.

    Returns:
        ``{key: (sha, branch)}`` (value is ``None`` for entries that failed).
    """
    out: dict[str, Optional[tuple[str, Optional[str]]]] = {}
    if not items:
        return out
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {
            ex.submit(resolve_remote_sha, url, branch): key
            for key, url, branch in items
        }
        for fut in concurrent.futures.as_completed(futs):
            key = futs[fut]
            try:
                out[key] = fut.result()
            except Exception as e:  # noqa: BLE001
                logger.debug(f"sha resolve failed for {key}: {e}")
                out[key] = None
    return out


def register_submodule(
    repo_root: Path,
    url: str,
    path: str,
    *,
    sha: Optional[str] = None,
    branch: Optional[str] = None,
) -> Optional[str]:
    """Register a submodule WITHOUT cloning it.

    Writes the ``.gitmodules`` entry and, when ``sha`` is provided, stages a
    gitlink (mode 160000) so a later ``git submodule update --init`` clones the
    pinned commit on demand. This mirrors the on-disk state of a freshly-cloned
    superproject and avoids the expensive full clone at scaffold time.

    Args:
        repo_root: Path to the superproject (where ``.gitmodules`` lives).
        url: Submodule clone URL or local path.
        path: Submodule path relative to ``repo_root`` (e.g. ``repos/foo``).
        sha: Pinned commit to record as the gitlink. If ``None`` the pointer is
            recorded in ``.gitmodules`` only (fetch later with ``--remote``).
        branch: Branch to record in ``.gitmodules`` (optional).

    Returns:
        The recorded SHA, or ``None`` if only the ``.gitmodules`` entry was
        written.
    """
    def _cfg(key: str, value: str) -> None:
        subprocess.run(
            ["git", "config", "-f", ".gitmodules", f"submodule.{path}.{key}", value],
            cwd=str(repo_root), check=True, capture_output=True,
        )

    _cfg("path", path)
    _cfg("url", url)
    if branch:
        _cfg("branch", branch)

    if sha:
        # Stage the gitlink so `submodule update --init` knows what to checkout.
        subprocess.run(
            ["git", "update-index", "--add", "--cacheinfo", f"160000,{sha},{path}"],
            cwd=str(repo_root), check=True, capture_output=True,
        )
    logger.debug(
        f"Registered submodule {path} -> {url} "
        f"(sha={sha[:8] if sha else 'deferred'}, branch={branch or 'remote-HEAD'})"
    )
    return sha
