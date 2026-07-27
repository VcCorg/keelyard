"""Process-wide WatcherRuntime holder.

Wraps ``agentic_cli.watchers.runtime.WatcherRuntime`` so the API layer can
share one instance across requests and the FastAPI lifespan can start/stop it.

Kept in a separate module (not inside watchers_service) to keep the service
module import-cheap: watchers_service is called from many places that don't
need the runtime.
"""
from __future__ import annotations

from typing import Optional

from agentic_cli.watchers.runtime import WatcherRuntime

_runtime: Optional[WatcherRuntime] = None


def get_runtime() -> WatcherRuntime:
    """Return the singleton, constructing it on first access."""
    global _runtime
    if _runtime is None:
        _runtime = WatcherRuntime()
    return _runtime


async def start_runtime() -> None:
    """Wired to the FastAPI lifespan startup hook."""
    await get_runtime().start()


async def stop_runtime() -> None:
    """Wired to the FastAPI lifespan shutdown hook."""
    global _runtime
    if _runtime is not None:
        await _runtime.stop()
        _runtime = None
