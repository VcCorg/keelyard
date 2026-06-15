"""Tests for host-agnostic git submodule helpers.

Uses real local git repositories (no network) to validate default-branch
detection across repos that default to `main`, `master`, or `develop` —
covering Bitbucket (often master/develop), GitLab, and GitHub.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from agentic_cli.meta_repo.git_utils import (
    add_submodule,
    detect_default_branch,
    detect_git_host,
)


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True)


def _make_repo_with_default_branch(path: Path, branch: str) -> Path:
    """Create a bare-backed local repo whose default branch is `branch`."""
    work = path / f"{branch}-work"
    work.mkdir(parents=True)
    _run(["git", "init", f"--initial-branch={branch}"], work)
    _run(["git", "config", "user.email", "test@test.com"], work)
    _run(["git", "config", "user.name", "Test"], work)
    (work / "README.md").write_text("# test\n")
    _run(["git", "add", "."], work)
    _run(["git", "commit", "-m", "init"], work)

    # Create a bare clone to act as the "remote" (HEAD symref points to branch)
    bare = path / f"{branch}.git"
    _run(["git", "clone", "--bare", str(work), str(bare)], path)
    return bare


# ---------------------------------------------------------------------------
# detect_git_host
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://bitbucket.example.com/scm/CGP/my-repo.git", "bitbucket"),
        ("git@bitbucket.org:team/repo.git", "bitbucket"),
        ("https://gitlab.com/group/project.git", "gitlab"),
        ("git@gitlab.example.com:group/project.git", "gitlab"),
        ("https://github.com/org/repo.git", "github"),
        ("git@github.com:org/repo.git", "github"),
        ("https://example.com/scm/repo.git", "unknown"),
        ("", "unknown"),
    ],
)
def test_detect_git_host(url, expected):
    assert detect_git_host(url) == expected


# ---------------------------------------------------------------------------
# detect_default_branch
# ---------------------------------------------------------------------------

def test_detect_default_branch_main():
    with tempfile.TemporaryDirectory() as tmp:
        bare = _make_repo_with_default_branch(Path(tmp), "main")
        assert detect_default_branch(str(bare)) == "main"


def test_detect_default_branch_master():
    """Simulates a Bitbucket Server repo defaulting to master."""
    with tempfile.TemporaryDirectory() as tmp:
        bare = _make_repo_with_default_branch(Path(tmp), "master")
        assert detect_default_branch(str(bare)) == "master"


def test_detect_default_branch_develop():
    with tempfile.TemporaryDirectory() as tmp:
        bare = _make_repo_with_default_branch(Path(tmp), "develop")
        assert detect_default_branch(str(bare)) == "develop"


def test_detect_default_branch_invalid_url():
    assert detect_default_branch("/nonexistent/path/to/repo.git") is None
    assert detect_default_branch("") is None


# ---------------------------------------------------------------------------
# add_submodule (host-agnostic branch handling)
# ---------------------------------------------------------------------------

def test_add_submodule_autodetects_master():
    """add_submodule must pin to the remote's actual default branch (master),
    not a hardcoded 'main' — otherwise Bitbucket repos would fail."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        remote = _make_repo_with_default_branch(tmp_path, "master")

        # Superproject
        super_repo = tmp_path / "super"
        super_repo.mkdir()
        _run(["git", "init", "--initial-branch=main"], super_repo)
        _run(["git", "config", "user.email", "test@test.com"], super_repo)
        _run(["git", "config", "user.name", "Test"], super_repo)

        used = add_submodule(super_repo, str(remote), "vendor/dep")

        assert used == "master"
        assert (super_repo / "vendor" / "dep" / "README.md").exists()
        gitmodules = (super_repo / ".gitmodules").read_text()
        assert "branch = master" in gitmodules


def test_add_submodule_explicit_branch_overrides_detection():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Remote has both main (default) and a feature branch
        remote_work = tmp_path / "work"
        remote_work.mkdir()
        _run(["git", "init", "--initial-branch=main"], remote_work)
        _run(["git", "config", "user.email", "t@t.com"], remote_work)
        _run(["git", "config", "user.name", "T"], remote_work)
        (remote_work / "f.txt").write_text("x")
        _run(["git", "add", "."], remote_work)
        _run(["git", "commit", "-m", "init"], remote_work)
        _run(["git", "branch", "release"], remote_work)
        bare = tmp_path / "remote.git"
        _run(["git", "clone", "--bare", str(remote_work), str(bare)], tmp_path)

        super_repo = tmp_path / "super"
        super_repo.mkdir()
        _run(["git", "init", "--initial-branch=main"], super_repo)
        _run(["git", "config", "user.email", "t@t.com"], super_repo)
        _run(["git", "config", "user.name", "T"], super_repo)

        used = add_submodule(super_repo, str(bare), "vendor/dep", branch="release")

        assert used == "release"
        gitmodules = (super_repo / ".gitmodules").read_text()
        assert "branch = release" in gitmodules
