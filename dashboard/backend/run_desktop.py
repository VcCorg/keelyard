"""Desktop entrypoint — frozen by PyInstaller, spawned by the Electron shell.

Runs the FastAPI backend on a caller-provided loopback port. The Electron main
process picks a free port and passes ``--port``, and sets ``KEEL_SERVE_FRONTEND``
to the bundled SPA directory so this single process also serves the UI. Kept as a
top-level module (next to ``src/``) so ``from src.api.main import app`` resolves
both in dev and when frozen.
"""
import argparse
import os
from pathlib import Path


def _bootstrap_home() -> None:
    """Ensure the ~/.keel data dir exists on first run (config is lazy elsewhere)."""
    try:
        (Path.home() / ".keel").mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(prog="keel-backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    _bootstrap_home()
    # Single-user desktop: default to the dev admin principal unless the operator
    # explicitly opts into forward-auth. Never lock the local user out.
    os.environ.setdefault("KEEL_AUTH_MODE", "dev")

    import uvicorn
    from src.api.main import app

    # Loopback only — the sidecar must never be reachable off the machine.
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
