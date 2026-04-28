"""Terminal service — manages PTY sessions for inline terminal."""

import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Where dva CLI lives
VENV_DIR = Path.home() / "dva-agentic-project" / ".venv"
WORKSPACE_DIR = Path.home() / "dva-agentic-project"

MAX_SESSIONS = 4


@dataclass
class TerminalSession:
    """A single PTY terminal session."""
    id: str
    pid: int
    fd: int
    created_at: str
    cols: int = 120
    rows: int = 30
    title: str = "Terminal"


# Active sessions keyed by session ID
_sessions: dict[str, TerminalSession] = {}


def _build_env() -> dict[str, str]:
    """Build environment with venv activated and uv tools on PATH."""
    env = os.environ.copy()

    extra_paths = []

    # Project venv FIRST — has correct arm64 Python + dva
    if VENV_DIR.exists():
        venv_bin = str(VENV_DIR / "bin")
        extra_paths.append(venv_bin)
        env["VIRTUAL_ENV"] = str(VENV_DIR)

    # uv tool bin second (fallback)
    uv_bin = Path.home() / ".local" / "bin"
    if uv_bin.exists():
        extra_paths.append(str(uv_bin))

    if extra_paths:
        env["PATH"] = ":".join(extra_paths) + ":" + env.get("PATH", "")

    # Remove PYTHONHOME if set (breaks venv)
    env.pop("PYTHONHOME", None)
    # Fully deactivate conda so the login shell starts clean
    # and our venv/uv paths take priority
    env.pop("CONDA_PREFIX", None)
    env.pop("CONDA_DEFAULT_ENV", None)
    env.pop("CONDA_SHLVL", None)
    env.pop("CONDA_PROMPT_MODIFIER", None)
    env.pop("CONDA_EXE", None)
    env.pop("CONDA_PYTHON_EXE", None)
    env.pop("CONDA_ROOT", None)
    # Remove conda paths from PATH to avoid re-activation conflicts
    current_path = env.get("PATH", "")
    clean_parts = [p for p in current_path.split(":") if "conda" not in p.lower()]
    env["PATH"] = ":".join(clean_parts)

    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["LANG"] = env.get("LANG", "en_US.UTF-8")
    return env


def create_session(cols: int = 120, rows: int = 30, title: str = "Terminal") -> TerminalSession:
    """Spawn a new PTY shell session."""
    if len(_sessions) >= MAX_SESSIONS:
        raise RuntimeError(f"Maximum {MAX_SESSIONS} terminal sessions reached")

    session_id = uuid.uuid4().hex[:12]
    env = _build_env()
    # Prefer zsh on macOS; fall back to SHELL or /bin/sh
    shell = "/bin/zsh" if Path("/bin/zsh").exists() else os.environ.get("SHELL", "/bin/sh")
    cwd = str(WORKSPACE_DIR) if WORKSPACE_DIR.exists() else str(Path.home())

    # Build a minimal rc file that skips conda init
    # Use zsh-compatible prompt escapes
    rc_content = (
        '# DVA Dashboard Terminal\n'
        'autoload -Uz colors && colors\n'
        'export PS1="%F{cyan}dva%f %F{yellow}%~%f $ "\n'
        '# Source user aliases if present, but skip conda\n'
        'if [ -f ~/.aliases ]; then source ~/.aliases; fi\n'
    )
    rc_path = Path.home() / ".dva" / "terminal_rc"
    rc_path.parent.mkdir(parents=True, exist_ok=True)
    rc_path.write_text(rc_content)

    # Use subprocess with PTY via pty.openpty
    master_fd, slave_fd = pty.openpty()

    # Set initial window size on slave
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    # Use ZDOTDIR to point zsh at our clean rc (skips conda init)
    if "zsh" in shell:
        zdotdir = rc_path.parent
        env["ZDOTDIR"] = str(zdotdir)
        zsh_rc = zdotdir / ".zshrc"
        zsh_rc.write_text(rc_content)
        shell_args = [shell]
    else:
        shell_args = [shell, "--rcfile", str(rc_path), "--noprofile"]

    proc = subprocess.Popen(
        shell_args,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        cwd=cwd,
        preexec_fn=os.setsid,
        close_fds=True,
    )
    os.close(slave_fd)

    # Set master fd to non-blocking
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    session = TerminalSession(
        id=session_id,
        pid=proc.pid,
        fd=master_fd,
        created_at=datetime.now(timezone.utc).isoformat(),
        cols=cols,
        rows=rows,
        title=title,
    )
    _sessions[session_id] = session
    return session


def list_sessions() -> list[dict]:
    """List all active terminal sessions."""
    result = []
    for s in _sessions.values():
        alive = _is_alive(s.pid)
        result.append({
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "cols": s.cols,
            "rows": s.rows,
            "alive": alive,
        })
    return result


def get_session(session_id: str) -> Optional[TerminalSession]:
    """Get a session by ID."""
    return _sessions.get(session_id)


def kill_session(session_id: str) -> bool:
    """Kill a terminal session."""
    session = _sessions.pop(session_id, None)
    if not session:
        return False
    try:
        os.close(session.fd)
    except OSError:
        pass
    try:
        os.kill(session.pid, signal.SIGHUP)
        os.waitpid(session.pid, os.WNOHANG)
    except (OSError, ChildProcessError):
        pass
    return True


def resize_session(session_id: str, cols: int, rows: int) -> bool:
    """Resize a terminal session."""
    session = _sessions.get(session_id)
    if not session:
        return False
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(session.fd, termios.TIOCSWINSZ, winsize)
        session.cols = cols
        session.rows = rows
        return True
    except OSError:
        return False


def write_to_pty(session_id: str, data: bytes) -> bool:
    """Write data (keystrokes) to the PTY."""
    session = _sessions.get(session_id)
    if not session:
        return False
    try:
        os.write(session.fd, data)
        return True
    except OSError:
        return False


def read_from_pty(session_id: str, max_bytes: int = 65536) -> Optional[bytes]:
    """Read available output from the PTY (non-blocking)."""
    session = _sessions.get(session_id)
    if not session:
        return None
    try:
        if select.select([session.fd], [], [], 0)[0]:
            return os.read(session.fd, max_bytes)
    except OSError:
        return None
    return b""


def _is_alive(pid: int) -> bool:
    """Check if process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cleanup_dead_sessions():
    """Remove sessions whose processes have died."""
    dead = [sid for sid, s in _sessions.items() if not _is_alive(s.pid)]
    for sid in dead:
        kill_session(sid)
