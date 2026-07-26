"""Terminal service — manages PTY sessions for the inline terminal.

Cross-platform: a Unix backend (``pty``/``termios``) and a Windows backend
(``pywinpty``/ConPTY) implement the same small interface. The Unix-only stdlib
modules are imported lazily inside the Unix backend so this module imports
cleanly on Windows (where ``fcntl``/``pty``/``termios`` do not exist).
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

IS_WINDOWS = os.name == "nt"

# Where keel CLI lives
VENV_DIR = Path.home() / "keel-agentic-project" / ".venv"
WORKSPACE_DIR = Path.home() / "keel-agentic-project"

MAX_SESSIONS = 4


@dataclass
class TerminalSession:
    """A single PTY terminal session.

    ``fd``/``pid`` are used by the Unix backend; ``handle`` carries the
    backend-specific process object (``subprocess.Popen`` on Unix, a
    ``winpty.PtyProcess`` on Windows).
    """
    id: str
    created_at: str
    cols: int = 120
    rows: int = 30
    title: str = "Terminal"
    pid: int = 0
    fd: Optional[int] = None
    handle: object = field(default=None, repr=False)


# Active sessions keyed by session ID
_sessions: dict[str, TerminalSession] = {}


def _venv_bin_dir() -> Path:
    """Return the venv executables dir (``Scripts`` on Windows, ``bin`` elsewhere)."""
    return VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")


def _build_env() -> dict[str, str]:
    """Build environment with venv activated and uv tools on PATH."""
    env = os.environ.copy()

    extra_paths = []

    # Project venv FIRST — has the correct Python + keel
    venv_bin = _venv_bin_dir()
    if venv_bin.exists():
        extra_paths.append(str(venv_bin))
        env["VIRTUAL_ENV"] = str(VENV_DIR)

    # uv tool bin second (fallback)
    uv_bin = Path.home() / ".local" / "bin"
    if uv_bin.exists():
        extra_paths.append(str(uv_bin))

    if extra_paths:
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get("PATH", "")

    # Remove PYTHONHOME if set (breaks venv)
    env.pop("PYTHONHOME", None)
    # Fully deactivate conda so the shell starts clean and our venv/uv paths win
    for key in (
        "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "CONDA_SHLVL",
        "CONDA_PROMPT_MODIFIER", "CONDA_EXE", "CONDA_PYTHON_EXE", "CONDA_ROOT",
    ):
        env.pop(key, None)
    # Remove conda paths from PATH to avoid re-activation conflicts
    current_path = env.get("PATH", "")
    clean_parts = [p for p in current_path.split(os.pathsep) if "conda" not in p.lower()]
    env["PATH"] = os.pathsep.join(clean_parts)

    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    if not IS_WINDOWS:
        env["LANG"] = env.get("LANG", "en_US.UTF-8")
    return env


def _workspace_cwd() -> str:
    return str(WORKSPACE_DIR) if WORKSPACE_DIR.exists() else str(Path.home())


# ── Unix backend (pty/termios) ──────────────────────────────────────────────

def _create_session_unix(cols: int, rows: int, title: str) -> TerminalSession:
    import fcntl
    import pty
    import struct
    import subprocess
    import termios

    env = _build_env()
    # Prefer zsh on macOS; fall back to SHELL or /bin/sh
    shell = "/bin/zsh" if Path("/bin/zsh").exists() else os.environ.get("SHELL", "/bin/sh")
    cwd = _workspace_cwd()

    # Build a minimal rc file that skips conda init (zsh-compatible prompt escapes)
    rc_content = (
        '# KEEL Dashboard Terminal\n'
        'autoload -Uz colors && colors\n'
        'export PS1="%F{cyan}keel%f %F{yellow}%~%f $ "\n'
        '# Source user aliases if present, but skip conda\n'
        'if [ -f ~/.aliases ]; then source ~/.aliases; fi\n'
    )
    rc_path = Path.home() / ".keel" / "terminal_rc"
    rc_path.parent.mkdir(parents=True, exist_ok=True)
    rc_path.write_text(rc_content)

    master_fd, slave_fd = pty.openpty()

    # Set initial window size on slave
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    # Use ZDOTDIR to point zsh at our clean rc (skips conda init)
    if "zsh" in shell:
        zdotdir = rc_path.parent
        env["ZDOTDIR"] = str(zdotdir)
        (zdotdir / ".zshrc").write_text(rc_content)
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

    return TerminalSession(
        id=uuid.uuid4().hex[:12],
        pid=proc.pid,
        fd=master_fd,
        handle=proc,
        created_at=datetime.now(timezone.utc).isoformat(),
        cols=cols,
        rows=rows,
        title=title,
    )


def _resize_unix(session: TerminalSession, cols: int, rows: int) -> bool:
    import fcntl
    import struct
    import termios
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(session.fd, termios.TIOCSWINSZ, winsize)
        return True
    except OSError:
        return False


def _write_unix(session: TerminalSession, data: bytes) -> bool:
    try:
        os.write(session.fd, data)
        return True
    except OSError:
        return False


def _read_unix(session: TerminalSession, max_bytes: int) -> Optional[bytes]:
    import select
    try:
        if select.select([session.fd], [], [], 0)[0]:
            return os.read(session.fd, max_bytes)
    except OSError:
        return None
    return b""


def _kill_unix(session: TerminalSession) -> None:
    import signal
    try:
        os.close(session.fd)
    except OSError:
        pass
    try:
        os.kill(session.pid, signal.SIGHUP)
        os.waitpid(session.pid, os.WNOHANG)
    except (OSError, ChildProcessError):
        pass


def _alive_unix(session: TerminalSession) -> bool:
    try:
        os.kill(session.pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ── Windows backend (pywinpty / ConPTY) ─────────────────────────────────────

def _create_session_windows(cols: int, rows: int, title: str) -> TerminalSession:
    try:
        from winpty import PtyProcess
    except ImportError as e:  # pragma: no cover - depends on install
        raise RuntimeError(
            "Terminal support on Windows requires 'pywinpty'. "
            "Install it with: pip install pywinpty"
        ) from e

    env = _build_env()
    cwd = _workspace_cwd()

    # Prefer PowerShell, fall back to the comspec shell (cmd.exe).
    import shutil
    shell = (
        shutil.which("pwsh")
        or shutil.which("powershell")
        or os.environ.get("COMSPEC", "cmd.exe")
    )

    proc = PtyProcess.spawn(
        shell,
        dimensions=(rows, cols),
        env=env,
        cwd=cwd,
    )

    return TerminalSession(
        id=uuid.uuid4().hex[:12],
        pid=getattr(proc, "pid", 0) or 0,
        fd=None,
        handle=proc,
        created_at=datetime.now(timezone.utc).isoformat(),
        cols=cols,
        rows=rows,
        title=title,
    )


def _resize_windows(session: TerminalSession, cols: int, rows: int) -> bool:
    try:
        session.handle.setwinsize(rows, cols)
        return True
    except Exception:
        return False


def _write_windows(session: TerminalSession, data: bytes) -> bool:
    try:
        session.handle.write(data.decode("utf-8", errors="replace"))
        return True
    except Exception:
        return False


def _read_windows(session: TerminalSession, max_bytes: int) -> Optional[bytes]:
    """Non-blocking read from a pywinpty PTY.

    The Unix path (_read_unix) uses ``select`` with timeout=0 so it never
    blocks the asyncio event loop. Windows must do the same — pywinpty's
    ``read()`` defaults to ``blocking=True`` and stalls the whole loop
    until the shell writes something. That deadlocks the WebSocket
    terminal on Windows: the read blocks waiting for shell output, the
    loop can't process the client's input, so the shell never receives
    the command and never produces output the read is waiting for. The
    frozen bundle observed exactly this: 0 bytes back over the WS in
    25s despite the shell process starting cleanly.

    Passing ``blocking=False`` (pywinpty >= 2.0) returns whatever bytes
    are already buffered and lets the loop yield back to write_pty_loop.
    """
    try:
        text = session.handle.read(max_bytes, blocking=False)
    except EOFError:
        return None
    except TypeError:
        # Very old pywinpty without the blocking kwarg — degrade to
        # sync read and accept the risk of a brief stall on first call.
        try:
            text = session.handle.read(max_bytes)
        except EOFError:
            return None
        except Exception:
            return None
    except Exception:
        return None
    if not text:
        return b""
    return text.encode("utf-8", errors="replace")


def _kill_windows(session: TerminalSession) -> None:
    try:
        session.handle.terminate(force=True)
    except Exception:
        pass


def _alive_windows(session: TerminalSession) -> bool:
    try:
        return bool(session.handle.isalive())
    except Exception:
        return False


# ── Public API (dispatches to the active backend) ───────────────────────────

def create_session(cols: int = 120, rows: int = 30, title: str = "Terminal") -> TerminalSession:
    """Spawn a new PTY shell session for the current platform."""
    if len(_sessions) >= MAX_SESSIONS:
        raise RuntimeError(f"Maximum {MAX_SESSIONS} terminal sessions reached")

    if IS_WINDOWS:
        session = _create_session_windows(cols, rows, title)
    else:
        session = _create_session_unix(cols, rows, title)

    _sessions[session.id] = session
    return session


def list_sessions() -> list[dict]:
    """List all active terminal sessions."""
    result = []
    for s in _sessions.values():
        result.append({
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "cols": s.cols,
            "rows": s.rows,
            "alive": _is_alive(s),
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
    if IS_WINDOWS:
        _kill_windows(session)
    else:
        _kill_unix(session)
    return True


def resize_session(session_id: str, cols: int, rows: int) -> bool:
    """Resize a terminal session."""
    session = _sessions.get(session_id)
    if not session:
        return False
    ok = _resize_windows(session, cols, rows) if IS_WINDOWS else _resize_unix(session, cols, rows)
    if ok:
        session.cols = cols
        session.rows = rows
    return ok


def write_to_pty(session_id: str, data: bytes) -> bool:
    """Write data (keystrokes) to the PTY."""
    session = _sessions.get(session_id)
    if not session:
        return False
    return _write_windows(session, data) if IS_WINDOWS else _write_unix(session, data)


def read_from_pty(session_id: str, max_bytes: int = 65536) -> Optional[bytes]:
    """Read available output from the PTY (non-blocking).

    Returns ``None`` if the session has died, ``b""`` if no data is available,
    or the available bytes otherwise.
    """
    session = _sessions.get(session_id)
    if not session:
        return None
    return _read_windows(session, max_bytes) if IS_WINDOWS else _read_unix(session, max_bytes)


def _is_alive(session: TerminalSession) -> bool:
    """Check if a session's process is still running."""
    return _alive_windows(session) if IS_WINDOWS else _alive_unix(session)


def cleanup_dead_sessions():
    """Remove sessions whose processes have died."""
    dead = [sid for sid, s in _sessions.items() if not _is_alive(s)]
    for sid in dead:
        kill_session(sid)
