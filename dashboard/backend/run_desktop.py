"""Desktop entrypoint — frozen by PyInstaller, spawned by the Electron shell.

Runs the FastAPI backend on a caller-provided loopback port. The Electron main
process picks a free port and passes ``--port``, and sets ``KEEL_SERVE_FRONTEND``
to the bundled SPA directory so this single process also serves the UI. Kept as a
top-level module (next to ``src/``) so ``from src.api.main import app`` resolves
both in dev and when frozen.

The frozen binary is also a multi-call binary (busybox-style): ``keel-backend
cli <args>`` dispatches straight into the ``keel`` Typer CLI. On startup we drop
thin ``keel`` wrappers into ``~/.keel/bin`` and prepend that to ``PATH``, so
terminal sessions opened inside the desktop app can run ``keel …`` even though
the recipient's machine has no Python at all.
"""
# ─── UTF-8 stdio + file I/O (must run before any Rich / Typer import) ────────
# On Windows the frozen interpreter defaults to cp1252 for both stdio and the
# encoding-less `open()`. That means `console.print("✓ ...")` in the CLI dies
# with `UnicodeEncodeError: 'charmap' codec can't encode character '✓'`,
# and `open(path, "w").write(<text with a checkmark>)` in project scaffolding
# dies with `'charmap' codec can't encode characters in position N`.
#
# Fix it once, at the top of the frozen entry, so every invocation path (the
# uvicorn server AND `keel-backend cli ...` multi-call dispatch) inherits
# UTF-8. Three layers:
#   1. Reconfigure sys.stdout / sys.stderr to UTF-8.
#   2. Force locale.getpreferredencoding to "utf-8" on Windows so `open()`
#      without an explicit encoding uses UTF-8 too (this is what the CLI's
#      project-scaffold and admin-doc writers rely on).
#   3. Set PYTHONIOENCODING / PYTHONUTF8 in os.environ so any subprocess the
#      CLI spawns (git, gh, pip, etc.) inherits UTF-8 as well.
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
_os.environ.setdefault("PYTHONUTF8", "1")
for _name in ("stdout", "stderr"):
    _stream = getattr(_sys, _name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — must never brick startup
            pass
if _sys.platform == "win32":
    import locale as _locale
    # Monkey-patch getpreferredencoding so `open()` defaults to UTF-8. Safer
    # than PYTHONUTF8=1 which only takes effect if set *before* the
    # interpreter starts (we can't guarantee that from Python code).
    _locale.getpreferredencoding = lambda do_setlocale=True: "utf-8"
# ─── /UTF-8 ──────────────────────────────────────────────────────────────────

import argparse
import os
import sys
from pathlib import Path

KEEL_BIN = Path.home() / ".keel" / "bin"


def _bootstrap_home() -> None:
    """Ensure the ~/.keel data dir exists on first run (config is lazy elsewhere)."""
    try:
        (Path.home() / ".keel").mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def _self_exe() -> str:
    """Absolute path of this program (the frozen exe, or this script in dev)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def _install_cli_wrappers() -> None:
    """Write ``keel`` wrappers into ~/.keel/bin pointing at this binary.

    Regenerated on every boot so a moved/updated install self-heals. Wrappers
    exec ``<this-exe> cli "$@"`` — the multi-call dispatch below routes that to
    the real Typer CLI inside the frozen bundle.
    """
    exe = _self_exe()
    try:
        KEEL_BIN.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            (KEEL_BIN / "keel.cmd").write_text(
                f'@echo off\r\n"{exe}" cli %*\r\n', encoding="utf-8")
        else:
            sh = KEEL_BIN / "keel"
            sh.write_text(f'#!/bin/sh\nexec "{exe}" cli "$@"\n', encoding="utf-8")
            sh.chmod(0o755)
    except OSError:
        return
    # Prepend so terminal sessions (which copy os.environ) inherit `keel`.
    os.environ["PATH"] = str(KEEL_BIN) + os.pathsep + os.environ.get("PATH", "")


def run_cli(argv: list[str]) -> None:
    """Dispatch into the keel Typer CLI (multi-call mode)."""
    sys.argv = ["keel", *argv]
    from agentic_cli.main import app as cli_app

    cli_app()


def main() -> None:
    # Multi-call dispatch: `keel-backend cli <args>` == `keel <args>`.
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        run_cli(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(prog="keel-backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    _bootstrap_home()
    _install_cli_wrappers()
    # Single-user desktop: default to the dev admin principal unless the operator
    # explicitly opts into forward-auth. Never lock the local user out.
    os.environ.setdefault("KEEL_AUTH_MODE", "dev")

    import uvicorn
    from src.api.main import app

    # Loopback only — the sidecar must never be reachable off the machine.
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
