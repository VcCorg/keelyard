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
