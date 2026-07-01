"""Devin configuration: API base, auth, TLS, and per-domain defaults.

Settings live under the ``"devin"`` key in the shared CLI config
(``~/.agent-cli-agentic/config.json``) so they sit alongside the existing
``init vertex-ai`` / ``init openai`` provider blocks. The API key itself is NEVER
persisted to disk — it is read from ``$DEVIN_API_KEY`` at call time.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

DEVIN_API_BASE = "https://api.devin.ai/v1"
DEVIN_API_KEY_ENV = "DEVIN_API_KEY"
# TLS controls for corporate proxies that inject a self-signed CA into the chain.
DEVIN_VERIFY_SSL_ENV = "DEVIN_VERIFY_SSL"   # "false"/"0" to disable verification
DEVIN_CA_BUNDLE_ENV = "DEVIN_CA_BUNDLE"     # path to a corporate CA bundle (preferred)

# Shared CLI config (same file used by commands/code.py and init.py).
CONFIG_DIR = Path.home() / ".agent-cli-agentic"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_KEY = "devin"

DEFAULT_MAX_ACU = 10


def resolve_verify() -> bool | str:
    """Resolve httpx ``verify`` from env: a CA bundle path, or a bool toggle."""
    ca = os.environ.get(DEVIN_CA_BUNDLE_ENV)
    if ca:
        return ca
    flag = os.environ.get(DEVIN_VERIFY_SSL_ENV, "true").strip().lower()
    return flag not in ("0", "false", "no", "off")


def resolve_api_key(explicit: str | None = None) -> str | None:
    """API key precedence: explicit arg -> $DEVIN_API_KEY -> None."""
    return explicit or os.environ.get(DEVIN_API_KEY_ENV) or None


def has_api_key(explicit: str | None = None) -> bool:
    return bool(resolve_api_key(explicit))


# ── Persisted settings (no secrets) ──────────────────────────────────────────

def _load_raw() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_raw(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


class DevinConfig:
    """Read/write the ``devin`` block of the shared CLI config.

    Shape::

        {
          "devin": {
            "base_url": "https://api.devin.ai/v1",
            "default_max_acu": 10,
            "domains": {
              "cwow-facility": {
                "snapshot_id": "snap-...",
                "playbook_id": "playbook-...",
                "knowledge_folder": "cwow-facility-okf"
              }
            }
          }
        }
    """

    def __init__(self, data: Optional[dict[str, Any]] = None):
        self.data: dict[str, Any] = data if data is not None else _load_raw().get(CONFIG_KEY, {})

    # -- top-level --
    @property
    def base_url(self) -> str:
        return self.data.get("base_url") or DEVIN_API_BASE

    @base_url.setter
    def base_url(self, value: str) -> None:
        self.data["base_url"] = value

    @property
    def default_max_acu(self) -> int:
        return int(self.data.get("default_max_acu", DEFAULT_MAX_ACU))

    @default_max_acu.setter
    def default_max_acu(self, value: int) -> None:
        self.data["default_max_acu"] = int(value)

    # -- per-domain --
    def domains(self) -> dict[str, Any]:
        return self.data.setdefault("domains", {})

    def domain(self, slug: str) -> dict[str, Any]:
        return self.domains().get(slug, {})

    def set_domain(self, slug: str, *, snapshot_id: str | None = None,
                   playbook_id: str | None = None, knowledge_folder: str | None = None,
                   blueprint_id: str | None = None, meta_repo_path: str | None = None,
                   meta_repo_sha: str | None = None, blueprint_hash: str | None = None,
                   built_at: str | None = None) -> None:
        """Update per-domain Devin settings.

        Beyond the core ids, this also records *provenance* for the snapshot
        (which meta-repo commit + blueprint file it was built from) so
        ``devin snapshots verify`` can detect drift between a stored snapshot
        and the current meta-repo state.
        """
        d = self.domains().setdefault(slug, {})
        if snapshot_id is not None:
            d["snapshot_id"] = snapshot_id
        if playbook_id is not None:
            d["playbook_id"] = playbook_id
        if knowledge_folder is not None:
            d["knowledge_folder"] = knowledge_folder
        if blueprint_id is not None:
            d["blueprint_id"] = blueprint_id
        if meta_repo_path is not None:
            d["meta_repo_path"] = meta_repo_path
        if meta_repo_sha is not None:
            d["meta_repo_sha"] = meta_repo_sha
        if blueprint_hash is not None:
            d["blueprint_hash"] = blueprint_hash
        if built_at is not None:
            d["built_at"] = built_at

    def is_configured(self) -> bool:
        """We consider Devin configured once an API key is available."""
        return has_api_key()

    @classmethod
    def load(cls) -> "DevinConfig":
        return cls()

    def save(self) -> None:
        raw = _load_raw()
        raw[CONFIG_KEY] = self.data
        _save_raw(raw)
