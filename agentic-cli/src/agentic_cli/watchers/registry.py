"""Trigger registry — adapters register themselves on import."""
from __future__ import annotations

from typing import Optional

from .types import TriggerProtocol


class TriggerNotFoundError(KeyError):
    """Raised when a watcher spec references an unknown trigger type."""


_REGISTRY: dict[str, TriggerProtocol] = {}


def register_trigger(trigger: TriggerProtocol) -> None:
    """Register (or replace) a trigger by name.

    Called by adapter modules at import time. Idempotent — re-registering
    the same name overwrites, so tests can swap in mock adapters cleanly.
    """
    _REGISTRY[trigger.info.name] = trigger


def list_triggers() -> list[TriggerProtocol]:
    """Every registered trigger, sorted by name for stable UI ordering."""
    return sorted(_REGISTRY.values(), key=lambda t: t.info.name)


def get_trigger(name: str) -> TriggerProtocol:
    """Return the trigger by name, or raise ``TriggerNotFoundError``."""
    trigger = _REGISTRY.get(name)
    if trigger is None:
        raise TriggerNotFoundError(
            f"Unknown trigger '{name}'. Known: {sorted(_REGISTRY.keys())}."
        )
    return trigger


def try_get_trigger(name: str) -> Optional[TriggerProtocol]:
    """Non-raising lookup used by the runtime — a stale spec must not crash startup."""
    return _REGISTRY.get(name)
