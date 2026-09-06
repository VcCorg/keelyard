"""How the dashboard invokes the `keel` CLI — one answer, not eight.

Two Windows bugs lived here, and both looked like success. A command would run,
the panel would stream its output, the run would exit 0, and nothing the user
asked for would exist. Both are fixed by this module; the point of it being one
module is that the fixes cannot drift back apart.

**Backslashes are not escapes on Windows.** ``shlex.split`` defaults to POSIX
mode, where ``\\`` escapes the next character. Splitting a Windows command that
way silently eats every separator::

    domain init acme --output C:\\Users\\v\\proj
    → ['domain', 'init', 'acme', '--output', 'C:Usersvproj']

The CLI then succeeds against a *relative* path, so the run genuinely completes
and the panel is right to report it. The folder lands beside whatever the
backend's working directory happens to be — for a packaged app, the install
directory — which is why it reads as "the steps ran but did nothing".

**A frozen sidecar is not a Python interpreter.** The old fallback was
``[sys.executable, "-m", "agentic_cli.main"]``. Under PyInstaller
``sys.executable`` is ``keel-backend`` itself, which ignores ``-m`` and starts a
second copy of the backend. The bundle already solves this: ``run_desktop.py``
is a multi-call binary and ``keel-backend cli <args>`` dispatches into the Typer
app, which is what the ``~/.keel/bin`` wrappers invoke. Frozen is checked
*before* the PATH lookup deliberately — a stray pip-installed ``keel`` on PATH
would otherwise shadow the bundled CLI the running backend was built with.

Neither fix is guarded by ``os.name`` at import time. The platform is a
parameter with a live default, so a Linux CI runner can assert the Windows
behaviour instead of discovering it on a user's laptop.
"""
from __future__ import annotations

import os
import shlex
import shutil
import sys

#: Quote characters ``shlex`` leaves attached to a token in non-POSIX mode.
_QUOTES = ('"', "'")


def is_frozen() -> bool:
    """True when running inside the PyInstaller sidecar."""
    return bool(getattr(sys, "frozen", False))


def resolve_cli_command() -> list[str]:
    """The argv prefix that runs the keel CLI from this process.

    Order matters. The frozen bundle ships the CLI that matches this backend, so
    it wins over anything on PATH; only an unfrozen install falls through to a
    console script, and only then to the interpreter.
    """
    if is_frozen():
        # Multi-call dispatch — see run_desktop.py. `-m` would be ignored here
        # and the exe would start a second backend instead.
        return [sys.executable, "cli"]

    keel = shutil.which("keel")
    if keel:
        return [keel]
    return [sys.executable, "-m", "agentic_cli.main"]


def split_command(command: str, *, windows: bool | None = None) -> list[str]:
    """Split a command string into argv, without eating Windows path separators.

    ``windows`` defaults to the host but is a parameter so both behaviours are
    testable anywhere. On Windows the split runs in non-POSIX mode, which keeps
    backslashes intact but leaves quote characters attached to the token, so
    balanced outer quotes are stripped afterwards.
    """
    if windows is None:
        windows = os.name == "nt"

    if not windows:
        return shlex.split(command)

    return [_unquote(token) for token in shlex.split(command, posix=False)]


def _unquote(token: str) -> str:
    """Drop one balanced pair of surrounding quotes, if present.

    Only the outermost pair, and only when balanced: a token like ``--name="a b``
    is malformed input rather than something to silently repair.
    """
    if len(token) >= 2 and token[0] in _QUOTES and token[-1] == token[0]:
        return token[1:-1]
    return token


__all__ = ["is_frozen", "resolve_cli_command", "split_command"]
