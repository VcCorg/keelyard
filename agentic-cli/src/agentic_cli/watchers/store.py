"""Watcher spec + state persistence — ~/.keel/watchers/.

Split by design: **specs** are user-authored YAML (one per watcher) so a
team can commit them alongside a domain meta-repo; **state** (cursors,
delivered-event dedup, last-fired) is machine-managed in a single JSON blob
so frequent writes don't churn the YAML.

Layout::

  ~/.keel/watchers/
  |-- <name>.yaml       # WatcherSpec, one per watcher
  `-- state.json        # {watcher_name: WatcherState, ...}

All I/O is defensive: a corrupt state file resets to empty (not raise), and
a corrupt spec file is logged + skipped so one bad watcher can't block the
runtime from starting.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from .types import WatcherSpec, WatcherState

logger = logging.getLogger(__name__)


def watchers_dir() -> Path:
    """Location of the watcher store. Override with ``KEEL_WATCHERS_DIR``."""
    override = os.environ.get("KEEL_WATCHERS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".keel" / "watchers"


def _state_path() -> Path:
    return watchers_dir() / "state.json"


def _spec_path(name: str) -> Path:
    # Names are validated at API boundary (no path traversal); this is a
    # belt-and-suspenders sanitation for anything that skipped that path.
    safe = "".join(c for c in name if c.isalnum() or c in "-_")
    if not safe:
        raise ValueError(f"invalid watcher name: {name!r}")
    return watchers_dir() / f"{safe}.yaml"


# ── Specs (YAML) ─────────────────────────────────────────────────────────────


def load_specs() -> list[WatcherSpec]:
    """Load every watcher spec from disk. Bad files logged + skipped."""
    d = watchers_dir()
    if not d.is_dir():
        return []
    specs: list[WatcherSpec] = []
    for f in sorted(d.glob("*.yaml")):
        spec = _load_spec_file(f)
        if spec is not None:
            specs.append(spec)
    return specs


def load_spec(name: str) -> Optional[WatcherSpec]:
    """Load a single watcher spec by name; None if not found or malformed."""
    path = _spec_path(name)
    return _load_spec_file(path) if path.exists() else None


def _load_spec_file(path: Path) -> Optional[WatcherSpec]:
    try:
        import yaml  # type: ignore
    except ImportError:
        logger.warning("PyYAML not installed; watcher specs cannot be loaded")
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:  # type: ignore[attr-defined]
        logger.warning(f"skipping malformed watcher spec {path.name}: {e}")
        return None
    if not isinstance(raw, dict):
        logger.warning(f"skipping watcher spec {path.name}: root must be a mapping")
        return None
    # Force name to match the filename stem so the two never diverge.
    raw["name"] = path.stem
    try:
        return WatcherSpec.from_dict(raw)
    except (TypeError, ValueError) as e:
        logger.warning(f"skipping invalid watcher spec {path.name}: {e}")
        return None


def save_spec(spec: WatcherSpec) -> Path:
    """Write a watcher spec to disk (creates the dir if needed)."""
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise RuntimeError("PyYAML is required to save watcher specs") from e
    watchers_dir().mkdir(parents=True, exist_ok=True)
    path = _spec_path(spec.name)
    path.write_text(
        yaml.safe_dump(spec.to_dict(), sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return path


def delete_spec(name: str) -> bool:
    """Remove a watcher spec + its state entry. Returns True if anything was deleted."""
    removed = False
    path = _spec_path(name)
    if path.exists():
        try:
            path.unlink()
            removed = True
        except OSError as e:
            logger.warning(f"could not delete {path}: {e}")
    # Also drop this watcher's state so a fresh spec with the same name
    # starts clean (no ghost cursor / delivered set).
    all_states = load_all_state()
    if name in all_states:
        all_states.pop(name, None)
        save_all_state(all_states)
        removed = True
    return removed


# ── State (JSON, atomic write) ───────────────────────────────────────────────


def load_all_state() -> dict[str, WatcherState]:
    """Read the whole state file. Missing/corrupt returns {}."""
    path = _state_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # A corrupt file must not brick the runtime — just start fresh.
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, WatcherState] = {}
    for name, entry in raw.items():
        if isinstance(entry, dict):
            out[str(name)] = WatcherState.from_dict(entry)
    return out


def load_state(name: str) -> WatcherState:
    """Return this watcher's state; default (empty) if unseen."""
    return load_all_state().get(name, WatcherState())


def save_state(name: str, state: WatcherState) -> None:
    """Persist one watcher's state (rewrites the whole state file atomically)."""
    all_states = load_all_state()
    all_states[name] = state
    save_all_state(all_states)


def save_all_state(all_states: dict[str, WatcherState]) -> None:
    """Atomic write of the whole state file (tmp + rename)."""
    watchers_dir().mkdir(parents=True, exist_ok=True)
    payload = {name: state.to_dict() for name, state in all_states.items()}
    path = _state_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
