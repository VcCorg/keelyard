"""How the dashboard invokes the CLI — the two Windows bugs, pinned.

Both bugs presented as success: a run that streamed output, exited 0, and did
nothing the user asked for. Neither had any test at all, and the suite has never
run on Windows, so the platform is a parameter here rather than a host fact —
these assertions have to hold on the Linux runner that actually executes them.
"""
from __future__ import annotations

import sys

import pytest

from src.services import cli_invocation as inv
from src.services.cli_service import parse_and_validate


WINDOWS_PATH = r"C:\Users\venkat\projects\acme"


class TestWindowsPathSplitting:
    def test_backslashes_survive(self):
        """The bug: POSIX splitting treats \\ as an escape and eats every one."""
        argv = inv.split_command(
            rf"domain init acme --output {WINDOWS_PATH}", windows=True)
        assert argv[-1] == WINDOWS_PATH

    def test_posix_splitting_is_what_broke_it(self):
        """Kept as the regression's own witness, not as approved behaviour."""
        argv = inv.split_command(
            rf"domain init acme --output {WINDOWS_PATH}", windows=False)
        assert argv[-1] == "C:Usersvenkatprojectsacme"
        assert "\\" not in argv[-1]

    def test_a_quoted_windows_path_with_spaces(self):
        argv = inv.split_command(
            r'code onboard --path "C:\Program Files\my repo"', windows=True)
        assert argv[-1] == r"C:\Program Files\my repo"

    def test_outer_quotes_are_dropped_but_inner_text_is_untouched(self):
        argv = inv.split_command(r'domain init "a b" --tag "x\y"', windows=True)
        assert argv[2:] == ["a b", "--tag", r"x\y"]

    def test_an_unterminated_quote_is_a_bad_request_not_a_crash(self):
        """shlex raises ValueError; unhandled it would surface as a 500."""
        from src.services.cli_service import CommandNotAllowed

        with pytest.raises(ValueError):
            inv.split_command(r'domain init "unclosed', windows=True)
        with pytest.raises(CommandNotAllowed):
            parse_and_validate(r'domain init "unclosed')

    def test_posix_paths_still_split_posix_style(self):
        argv = inv.split_command(
            "domain init acme --output /home/v/projects/acme", windows=False)
        assert argv[-1] == "/home/v/projects/acme"

    def test_the_host_decides_when_nothing_is_passed(self, monkeypatch):
        monkeypatch.setattr(inv.os, "name", "nt")
        assert inv.split_command(rf"x --p {WINDOWS_PATH}")[-1] == WINDOWS_PATH
        monkeypatch.setattr(inv.os, "name", "posix")
        assert inv.split_command(rf"x --p {WINDOWS_PATH}")[-1] != WINDOWS_PATH

    def test_the_validator_uses_it(self, monkeypatch):
        """The whitelist path is where a real user's command arrives."""
        monkeypatch.setattr(inv.os, "name", "nt")
        argv = parse_and_validate(rf"domain init acme --output {WINDOWS_PATH}")
        assert argv == ["domain", "init", "acme", "--output", WINDOWS_PATH]

    def test_the_whitelist_still_bites(self, monkeypatch):
        """A path fix must not become a hole in the safety boundary."""
        from src.services.cli_service import CommandNotAllowed

        monkeypatch.setattr(inv.os, "name", "nt")
        with pytest.raises(CommandNotAllowed):
            parse_and_validate(r"rm -rf C:\Windows")
        with pytest.raises(CommandNotAllowed):
            parse_and_validate(r"domain delete acme")


class TestFrozenSidecar:
    def test_frozen_uses_the_multi_call_dispatch(self, monkeypatch):
        """`-m` is ignored by the exe and starts a second backend instead."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", r"C:\app\keel-backend.exe",
                            raising=False)

        assert inv.resolve_cli_command() == [r"C:\app\keel-backend.exe", "cli"]

    def test_frozen_beats_a_stray_keel_on_path(self, monkeypatch):
        """The bundled CLI matches this backend; something on PATH may not."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", "/app/keel-backend", raising=False)
        monkeypatch.setattr(inv.shutil, "which", lambda name: "/usr/local/bin/keel")

        assert inv.resolve_cli_command() == ["/app/keel-backend", "cli"]

    def test_unfrozen_prefers_the_console_script(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.setattr(inv.shutil, "which", lambda name: "/usr/local/bin/keel")

        assert inv.resolve_cli_command() == ["/usr/local/bin/keel"]

    def test_unfrozen_without_a_console_script_runs_the_module(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.setattr(inv.shutil, "which", lambda name: None)
        monkeypatch.setattr(sys, "executable", "/usr/bin/python3", raising=False)

        assert inv.resolve_cli_command() == [
            "/usr/bin/python3", "-m", "agentic_cli.main"]


class TestOneImplementation:
    def test_every_service_shares_it(self):
        """Eight copies is how a fix in one leaves seven behind."""
        import importlib

        names = ("cli_service", "code_service", "data_service", "domain_service",
                 "eval_service", "kg_ingest_service", "setup_service",
                 "workspace_service")
        for name in names:
            module = importlib.import_module(f"src.services.{name}")
            assert module.resolve_cli_command is inv.resolve_cli_command, name
