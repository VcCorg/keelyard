"""Per-domain cross-process locking for OKF bundle mutations.

Multiple developers (and the dashboard, which shells out to the same CLI) can
trigger `kg okf enrich`, `kg okf export`, or `domain sync` for the same domain
concurrently. Those all write the same shared artifacts (the OKF bundle dir and
the canonical store clones), so concurrent runs can interleave writes and
corrupt the bundle index.

``domain_lock`` is an advisory, machine-scoped lock keyed by domain (and an
optional scope). It uses ``fcntl.flock`` on a lock file under the system temp
dir, so it is shared across every process on the host that locks the same key.
By default it is non-blocking and raises :class:`DomainLockBusy` if the lock is
held; pass ``timeout`` to wait.
"""
from __future__ import annotations

import errno
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from agentic_cli.kg.okf.schema import slugify

try:  # POSIX
    import fcntl
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore
    _HAVE_FCNTL = False


class DomainLockBusy(RuntimeError):
    """Raised when a domain lock is already held by another process."""

    def __init__(self, domain: str, scope: str, holder: str = ""):
        self.domain = domain
        self.scope = scope
        self.holder = holder
        msg = f"OKF '{scope}' for domain '{domain}' is busy (another run is in progress)"
        if holder:
            msg += f" — held by {holder}"
        super().__init__(msg)


def lock_dir() -> Path:
    d = Path(tempfile.gettempdir()) / "agentic-okf-locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lock_path(domain: str, scope: str = "okf") -> Path:
    return lock_dir() / f"{slugify(scope)}-{slugify(domain)}.lock"


@contextmanager
def domain_lock(domain: str, *, scope: str = "okf", timeout: float = 0.0, poll: float = 0.5):
    """Acquire an advisory machine-scoped lock for ``domain``.

    Args:
        domain: Domain slug (the shared resource).
        scope: Lock scope, e.g. ``okf`` or ``sync``; use the same scope for
            operations that touch the same artifacts.
        timeout: Seconds to wait for the lock. ``0`` (default) is non-blocking
            and raises :class:`DomainLockBusy` immediately if held.
        poll: Retry interval while waiting.

    Raises:
        DomainLockBusy: If the lock cannot be acquired within ``timeout``.
    """
    path = lock_path(domain, scope)
    # No-op lock on platforms without fcntl (best effort: still create the file).
    if not _HAVE_FCNTL:  # pragma: no cover
        path.write_text(f"{os.getpid()}\n", encoding="utf-8")
        try:
            yield path
        finally:
            try:
                path.unlink()
            except OSError:
                pass
        return

    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + max(0.0, timeout)
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    holder = ""
                    try:
                        holder = os.pread(fd, 256, 0).decode(errors="replace").strip()
                    except OSError:
                        pass
                    raise DomainLockBusy(domain, scope, holder)
                time.sleep(poll)
        # Record holder info for diagnostics.
        try:
            os.ftruncate(fd, 0)
            os.pwrite(fd, f"pid={os.getpid()} scope={scope} domain={domain}\n".encode(), 0)
        except OSError:
            pass
        yield path
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def is_locked(domain: str, scope: str = "okf") -> bool:
    """Best-effort check whether a domain lock is currently held (non-blocking)."""
    if not _HAVE_FCNTL:  # pragma: no cover
        return False
    path = lock_path(domain, scope)
    if not path.exists():
        return False
    fd = os.open(str(path), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        os.close(fd)
