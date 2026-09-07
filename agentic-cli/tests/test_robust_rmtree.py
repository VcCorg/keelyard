"""Removing a tree that contains a git repository, on Windows.

`_robust_rmtree` was written for a macOS symptom — Spotlight recreating
.DS_Store mid-delete — and retried with ignore_errors until a final pass raised.
Retrying cannot help on Windows: git marks everything under .git/objects
read-only, unlink refuses a read-only file outright, and nothing about the file
changes between attempts. Every `--force` re-init died with

    PermissionError: [WinError 5] Access is denied:
    ...\\product-x-meta\\.git\\objects\\08\\a93eac...

The read-only bit has to be cleared. These tests drive the logic directly rather
than through the filesystem, because POSIX lets you unlink a read-only file and
the tests run as root in CI — the failure being fixed cannot be reproduced here.
"""
from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import pytest

from agentic_cli.commands.domain import _on_rmtree_error, _robust_rmtree


class TestReadOnlyHandler:
    def test_it_clears_read_only_then_retries(self, tmp_path):
        """What Windows needs: chmod +w, then the delete that just failed."""
        target = tmp_path / "a93eac"
        target.write_text("x")
        os.chmod(target, stat.S_IRUSR)

        calls = []

        def func(path):
            calls.append(path)
            # Refuses while read-only, exactly as os.unlink does on Windows.
            if not os.stat(path).st_mode & stat.S_IWRITE:
                raise PermissionError(5, "Access is denied")

        _on_rmtree_error(func, str(target), PermissionError(5, "Access is denied"))

        assert calls == [str(target)]
        assert os.stat(target).st_mode & stat.S_IWRITE

    def test_an_unfixable_error_is_swallowed_for_the_caller_to_surface(self, tmp_path):
        """The handler is not the place to decide a tree is undeletable."""
        missing = tmp_path / "gone"

        def func(path):
            raise OSError(1, "nope")

        # Must not raise: _robust_rmtree's final bare attempt reports the real
        # failure, with the path that blocked it.
        _on_rmtree_error(func, str(missing), OSError(1, "nope"))


class TestRobustRmtree:
    def test_it_removes_a_tree_holding_read_only_git_objects(self, tmp_path):
        repo = tmp_path / "product-x-meta"
        objects = repo / ".git" / "objects" / "08"
        objects.mkdir(parents=True)
        blob = objects / "a93eac6867da6da332da8b57313a9aab4a1205"
        blob.write_text("blob")
        os.chmod(blob, stat.S_IRUSR)

        _robust_rmtree(repo)

        assert not repo.exists()

    def test_the_handler_reaches_rmtree(self, tmp_path, monkeypatch):
        """ignore_errors would silently replace it with a no-op — see the source."""
        repo = tmp_path / "repo"
        repo.mkdir()
        seen = {}

        def fake_rmtree(path, **kwargs):
            seen.update(kwargs)
            Path(path).rmdir()

        monkeypatch.setattr(shutil, "rmtree", fake_rmtree)
        _robust_rmtree(repo)

        assert not seen.get("ignore_errors"), "ignore_errors disables the handler"
        assert seen.get("onexc") is _on_rmtree_error or \
            seen.get("onerror") is _on_rmtree_error

    def test_a_tree_that_will_not_die_raises_rather_than_lying(self, tmp_path,
                                                               monkeypatch):
        """A silent no-op would leave the caller writing into a stale repo."""
        repo = tmp_path / "repo"
        repo.mkdir()

        def never_deletes(path, **kwargs):
            if kwargs:
                return          # handler pass: swallows, leaves the tree
            raise PermissionError(5, "Access is denied")

        monkeypatch.setattr(shutil, "rmtree", never_deletes)
        monkeypatch.setattr("time.sleep", lambda _s: None)

        with pytest.raises(PermissionError):
            _robust_rmtree(repo, attempts=2)

    def test_a_clean_tree_needs_only_one_pass(self, tmp_path, monkeypatch):
        repo = tmp_path / "repo"
        (repo / "nested").mkdir(parents=True)
        passes = []

        real = shutil.rmtree

        def counting(path, **kwargs):
            passes.append(1)
            real(path, **kwargs)

        monkeypatch.setattr(shutil, "rmtree", counting)
        _robust_rmtree(repo)

        assert len(passes) == 1
        assert not repo.exists()
