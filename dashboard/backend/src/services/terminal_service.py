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

# How long an orphaned session (no attached websocket client) is kept alive
# before being reaped. Tab-switch/page-reload reconnects happen within
# seconds, so this only catches genuinely abandoned sessions (crashed
# client, closed tab, dropped network) — see mark_disconnected/mark_connected.
ORPHAN_GRACE_PERIOD_SECONDS = 600


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
    disconnected_at: Optional[datetime] = None


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

    if not IS_WINDOWS:
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"
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

    # Skip the user's profile/AutoRun scripts: mirrors the Unix backend's use
    # of a minimal custom rc file rather than the user's real (possibly slow
    # or antivirus-scanned) shell config. Without this, PowerShell can sit
    # silent for tens of seconds loading profile modules before ever
    # printing a prompt.
    shell_lower = shell.lower()
    if "powershell" in shell_lower or "pwsh" in shell_lower:
        argv = [shell, "-NoLogo", "-NoProfile"]
    elif "cmd" in shell_lower:
        argv = [shell, "/D"]
    else:
        argv = [shell]

    proc = PtyProcess.spawn(
        argv,
        dimensions=(rows, cols),
        env=env,
        cwd=cwd,
    )
    # PtyProcess.read() is a blocking socket.recv() with no timeout. Bound it
    # so a stalled/dead shell (or a stale reader after the client
    # disconnects and later reconnects to the same session) can't block
    # forever; _read_windows treats socket.timeout as an idle poll tick.
    proc.fileobj.settimeout(0.2)

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
    """Read from a pywinpty PTY without freezing the asyncio event loop.

    Tries ``read(max_bytes, blocking=False)`` first (some pywinpty releases
    support this and it's the cheapest path when available). The pinned
    version here — pywinpty 3.0.5 — does NOT: its ``PtyProcess.read(self,
    size=1024)`` takes no ``blocking`` kwarg and does a plain blocking
    ``socket.recv()`` (confirmed by reading the installed
    ``winpty/ptyprocess.py`` source), so that call raises ``TypeError`` and
    we fall back to the plain ``read()``. That fallback is still safe:
    ``_create_session_windows`` calls ``proc.fileobj.settimeout(0.2)`` at
    spawn time, so the "blocking" read can never actually block longer than
    ~200ms — it raises ``socket.timeout`` instead, which we treat as an
    idle poll tick. Combined with ``asyncio.to_thread`` at the call site
    (api/terminal.py), this guarantees the event loop is never wedged
    waiting on shell output, regardless of which pywinpty version is
    installed.
    """
    import socket
    try:
        text = session.handle.read(max_bytes, blocking=False)
    except TypeError:
        try:
            text = session.handle.read(max_bytes)
        except socket.timeout:
            return b""  # idle poll tick — not death
        except EOFError:
            return None
        except Exception:
            return None
    except socket.timeout:
        return b""
    except EOFError:
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

    # Start the disconnect timer immediately so a session that's created but
    # never actually connected to (client crashed between create and
    # websocket-open) still gets reaped by cleanup_dead_sessions().
    session.disconnected_at = datetime.now(timezone.utc)
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
    """Remove sessions whose processes have died or that were abandoned.

    A session is "abandoned" if no websocket client has been attached for
    longer than ``ORPHAN_GRACE_PERIOD_SECONDS`` (see ``mark_disconnected``).
    Tab-switch/page-reload reconnects clear this within seconds via
    ``mark_connected``, so this only reaps genuinely dropped clients.
    """
    now = datetime.now(timezone.utc)
    to_kill = []
    for sid, s in _sessions.items():
        if not _is_alive(s):
            to_kill.append(sid)
        elif s.disconnected_at is not None:
            idle = (now - s.disconnected_at).total_seconds()
            if idle > ORPHAN_GRACE_PERIOD_SECONDS:
                to_kill.append(sid)
    for sid in to_kill:
        kill_session(sid)


def mark_connected(session_id: str) -> None:
    """Clear the disconnect timer — a client has attached to this session."""
    session = _sessions.get(session_id)
    if session:
        session.disconnected_at = None


def mark_disconnected(session_id: str) -> None:
    """Start the disconnect timer — no client is currently attached."""
    session = _sessions.get(session_id)
    if session:
        session.disconnected_at = datetime.now(timezone.utc)
