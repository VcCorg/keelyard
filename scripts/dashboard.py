#!/usr/bin/env python3
"""Cross-platform launcher for the Agentic dashboard (backend :8000 + frontend :5173).

ONE command for macOS, Linux, and Windows. The OS is detected internally, so the
exact same invocation works everywhere:

    python scripts/dashboard.py start                 # start both (prompt on busy ports)
    python scripts/dashboard.py start --force-restart # reclaim busy ports, no prompt
    python scripts/dashboard.py start --backend       # backend only
    python scripts/dashboard.py stop
    python scripts/dashboard.py status
    python scripts/dashboard.py restart

Each service runs in the background, logging to dashboard/backend.log and
dashboard/frontend.log; PIDs are recorded in dashboard/.backend.pid /
dashboard/.frontend.pid. If a port is already in use, the launcher WARNS (showing
the owning process) and asks before killing it — unless --force-restart is given
(or the shell is non-interactive, in which case it skips).

Integration tokens are read by the backend itself from ~/.keel/.env
(%USERPROFILE%\\.keel\\.env on Windows), so no shell exports are needed.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

IS_WINDOWS = os.name == "nt"
ROOT = Path(__file__).resolve().parents[1]          # scripts/ -> repo root
BACKEND_DIR = ROOT / "dashboard" / "backend"
FRONTEND_DIR = ROOT / "dashboard" / "frontend"
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 5173

if IS_WINDOWS:
    os.system("")  # enable ANSI escape processing on modern Windows consoles

_BLUE, _GREEN, _YELLOW, _RED, _NC = (
    "\033[0;34m", "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0m"
)


def info(m: str) -> None: print(f"{_BLUE}>{_NC} {m}")
def ok(m: str) -> None:   print(f"{_GREEN}OK{_NC} {m}")
def warn(m: str) -> None: print(f"{_YELLOW}!{_NC} {m}")
def err(m: str) -> None:  print(f"{_RED}x{_NC} {m}")


# ── Port discovery / process control (OS-aware) ──────────────────────────────

def port_pids(port: int) -> list[int]:
    """PIDs listening on ``port`` (empty if free)."""
    pids: set[int] = set()
    if IS_WINDOWS:
        try:
            out = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True, text=True, check=False,
            ).stdout
        except Exception:
            out = ""
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
                if parts[1].endswith(f":{port}"):
                    try:
                        pids.add(int(parts[4]))
                    except ValueError:
                        pass
    else:
        try:
            out = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
                capture_output=True, text=True, check=False,
            ).stdout
            for tok in out.split():
                try:
                    pids.add(int(tok))
                except ValueError:
                    pass
        except FileNotFoundError:
            pass  # lsof not present; treat as free
    return sorted(p for p in pids if p not in (0, 4))


def proc_desc(pid: int) -> str:
    try:
        if IS_WINDOWS:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, check=False,
            ).stdout.strip()
            return out or str(pid)
        out = subprocess.run(
            ["ps", "-p", str(pid), "-o", "pid=,comm="],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        return out or str(pid)
    except Exception:
        return str(pid)


def kill_pids(pids: list[int]) -> None:
    for pid in pids:
        try:
            if IS_WINDOWS:
                subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"],
                               capture_output=True, check=False)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    time.sleep(1)
    if not IS_WINDOWS:
        for pid in pids:
            try:
                os.kill(pid, 0)          # still alive?
            except OSError:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass


def ensure_port_free(port: int, label: str, force: bool) -> bool:
    """Warn before killing whoever owns ``port``. Returns True if free/cleared."""
    pids = port_pids(port)
    if not pids:
        return True

    warn(f"{label} port {port} is already in use by PID(s): {', '.join(map(str, pids))}")
    for pid in pids:
        print(f"    {proc_desc(pid)}")

    if not force:
        if not sys.stdin.isatty():
            warn(f"Non-interactive shell and no --force-restart: leaving existing {label}; skipping.")
            return False
        try:
            ans = input(f"Kill the above process(es) on port {port} and restart {label}? [y/N] ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            info(f"Leaving existing {label} running; skipping start.")
            return False

    warn(f"Stopping process(es) on port {port} ...")
    kill_pids(pids)
    if port_pids(port):
        err(f"Could not free port {port}; skipping {label}.")
        return False
    return True


# ── Launch ────────────────────────────────────────────────────────────────────

def _venv_python() -> str:
    sub = "Scripts" if IS_WINDOWS else "bin"
    exe = "python.exe" if IS_WINDOWS else "python"
    for cand in (ROOT / ".venv" / sub / exe, ROOT / "agentic-cli" / ".venv" / sub / exe):
        if cand.exists():
            return str(cand)
    return sys.executable  # fall back to the interpreter running this script


def _spawn(cmd: list[str], cwd: Path, log_path: Path, pidfile: Path) -> int:
    """Start a detached background process, logging combined output to a file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab")
    kwargs: dict = dict(cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL)
    if IS_WINDOWS:
        # DETACHED_PROCESS + new group so it survives this launcher exiting.
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    finally:
        log.close()
    pidfile.write_text(str(proc.pid))
    return proc.pid


def start_backend(force: bool, port: int) -> None:
    if not BACKEND_DIR.exists():
        warn(f"Backend directory not found ({BACKEND_DIR}); skipping.")
        return
    py = _venv_python()
    if not ensure_port_free(port, "Backend", force):
        return
    info(f"Starting backend on http://localhost:{port} (background) ...")
    cmd = [py, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", str(port),
           "--reload", "--reload-dir", str(BACKEND_DIR / "src"),
           "--reload-dir", str(ROOT / "agentic-cli" / "src")]
    pid = _spawn(cmd, BACKEND_DIR, ROOT / "dashboard" / "backend.log",
                 ROOT / "dashboard" / ".backend.pid")
    ok(f"Backend started (PID {pid}); logs: dashboard/backend.log")


def start_frontend(force: bool, port: int) -> None:
    if not FRONTEND_DIR.exists():
        warn(f"Frontend directory not found ({FRONTEND_DIR}); skipping.")
        return
    npm = shutil.which("npm")
    if not npm:
        warn("npm not found on PATH; skipping frontend.")
        return
    if not ensure_port_free(port, "Frontend", force):
        return
    info(f"Starting frontend on http://localhost:{port} (background) ...")
    cmd = [npm, "run", "dev", "--", "--port", str(port)]
    # npm is npm.cmd on Windows; batch files must run via cmd.
    if IS_WINDOWS and npm.lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c"] + cmd
    pid = _spawn(cmd, FRONTEND_DIR, ROOT / "dashboard" / "frontend.log",
                 ROOT / "dashboard" / ".frontend.pid")
    ok(f"Frontend started (PID {pid}); logs: dashboard/frontend.log")


def stop_services(backend_port: int, frontend_port: int) -> None:
    for label, port, pidfile in (
        ("Backend", backend_port, ROOT / "dashboard" / ".backend.pid"),
        ("Frontend", frontend_port, ROOT / "dashboard" / ".frontend.pid"),
    ):
        pids = port_pids(port)
        if pids:
            warn(f"Stopping {label} on port {port} (PID {', '.join(map(str, pids))}) ...")
            kill_pids(pids)
            ok(f"{label} stopped.")
        else:
            info(f"{label}: nothing listening on port {port}.")
        if pidfile.exists():
            try:
                pidfile.unlink()
            except OSError:
                pass


def show_status(backend_port: int, frontend_port: int) -> None:
    for label, port in (("Backend", backend_port), ("Frontend", frontend_port)):
        pids = port_pids(port)
        if pids:
            ok(f"{label}: running on port {port} (PID {', '.join(map(str, pids))})")
        else:
            info(f"{label}: not running (port {port} free)")


# ── CLI ─────────────────────────────────────────────────────────────────────

def _add_start_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--backend", action="store_true", help="Start only the backend")
    sp.add_argument("--frontend", action="store_true", help="Start only the frontend")
    sp.add_argument("--force-restart", dest="force", action="store_true",
                    help="Kill processes on busy ports without prompting")
    sp.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    sp.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dashboard.py",
        description="Start/stop the Agentic dashboard (cross-platform: macOS, Linux, Windows).",
    )
    sub = parser.add_subparsers(dest="cmd")
    _add_start_args(sub.add_parser("start", help="Start services in the background"))
    _add_start_args(sub.add_parser("restart", help="Stop then start services"))
    for name in ("stop", "status"):
        s = sub.add_parser(name, help=f"{name.capitalize()} services")
        s.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
        s.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)

    args = parser.parse_args(argv)
    cmd = args.cmd or "start"

    if cmd == "status":
        show_status(args.backend_port, args.frontend_port)
        return 0
    if cmd == "stop":
        stop_services(args.backend_port, args.frontend_port)
        return 0

    if cmd == "restart":
        stop_services(args.backend_port, args.frontend_port)
        time.sleep(1)

    do_backend = args.backend or (not args.backend and not args.frontend)
    do_frontend = args.frontend or (not args.backend and not args.frontend)

    if do_backend:
        start_backend(args.force, args.backend_port)
    if do_frontend:
        start_frontend(args.force, args.frontend_port)

    print()
    info(f"Dashboard: http://localhost:{args.frontend_port}   (API: http://localhost:{args.backend_port})")
    info("Stop later:  python scripts/dashboard.py stop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
