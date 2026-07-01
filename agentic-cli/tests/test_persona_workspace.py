"""Regression tests for persona_workspace worktree base resolution.

Covers the bug where a canonical store clone whose remote default branch is
``develop`` (not ``main``) — and which has an *unborn* local HEAD with no local
branch — caused ``git worktree add ... main`` to fail with
``fatal: not a valid object name: 'main'``.
"""
import subprocess
from pathlib import Path

import pytest

from agentic_cli import persona_workspace as pw


def _git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    )


def _make_remote_on_develop(tmp_path: Path) -> Path:
    """A real repo whose default branch is ``develop`` (no ``main``)."""
    remote = tmp_path / "remote"
    remote.mkdir()
    _git(["init", "-b", "develop"], remote)
    _git(["config", "user.email", "t@example.com"], remote)
    _git(["config", "user.name", "T"], remote)
    (remote / "README.md").write_text("hi\n")
    _git(["add", "-A"], remote)
    _git(["commit", "-m", "init"], remote)
    return remote


def test_detect_default_branch_local_develop(tmp_path):
    """A normal clone checked out on ``develop`` resolves to ``develop``."""
    remote = _make_remote_on_develop(tmp_path)
    store = tmp_path / "store"
    _git(["clone", str(remote), str(store)], tmp_path)
    assert pw.detect_default_branch(store) == "develop"


def test_detect_default_branch_unborn_head_falls_back_to_origin(tmp_path):
    """Unborn local HEAD (no local branch) + origin/develop -> origin/develop.

    This is the exact state that produced ``not a valid object name: 'main'``.
    """
    remote = _make_remote_on_develop(tmp_path)
    store = tmp_path / "store"
    store.mkdir()
    _git(["init", "-b", "main"], store)  # unborn local 'main', no commits
    _git(["remote", "add", "origin", str(remote)], store)
    _git(["fetch", "origin"], store)

    base = pw.detect_default_branch(store)
    assert base == "origin/develop"
    # The resolved base must name a real commit so a worktree can branch from it.
    assert pw._ref_resolves(store, base)


def test_add_worktree_from_unborn_store(tmp_path, monkeypatch):
    """add_worktree succeeds against a store clone with an unborn local HEAD."""
    remote = _make_remote_on_develop(tmp_path)
    store = tmp_path / "store" / "myrepo"
    store.mkdir(parents=True)
    _git(["init", "-b", "main"], store)
    _git(["remote", "add", "origin", str(remote)], store)
    _git(["fetch", "origin"], store)

    monkeypatch.setattr(pw, "store_repo_path", lambda slug: store)

    dest = tmp_path / "wt" / "myrepo"
    out = pw.add_worktree("myrepo", dest, "ws/dev/myrepo")
    assert out == dest
    assert (dest / "README.md").exists()
    # Worktree is on the requested branch, based off the remote default commit.
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(dest), capture_output=True, text=True,
    ).stdout.strip()
    assert branch == "ws/dev/myrepo"
