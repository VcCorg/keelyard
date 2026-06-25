"""Generic Devin Knowledge operations (domain-agnostic).

These helpers manage Knowledge entries/folders via the live API and are NOT tied
to OKF. The OKF-specific rendering/push lives in
``agentic_cli.kg.okf.devin`` and builds on top of these.
"""
from __future__ import annotations

from typing import Any

from agentic_cli.devin.client import get_client
from agentic_cli.devin.config import DEVIN_API_BASE
from agentic_cli.devin.errors import DevinError

# Fields Devin's PUT /knowledge accepts.
_UPDATABLE_FIELDS = ("name", "body", "trigger_description", "pinned_repo", "parent_folder_id")


def list_entries(api_key: str | None = None, base_url: str = DEVIN_API_BASE) -> dict[str, Any]:
    """Return ``{knowledge: [...], folders: [...]}`` from the live API."""
    with get_client(api_key, base_url=base_url) as client:
        return client.list_knowledge()


def delete_entries(ids: list[str], api_key: str | None = None,
                   base_url: str = DEVIN_API_BASE) -> tuple[list[str], list[tuple[str, str]]]:
    """Delete entries by id. Returns ``(deleted_ids, [(id, error), ...])``."""
    deleted: list[str] = []
    failed: list[tuple[str, str]] = []
    with get_client(api_key, base_url=base_url) as client:
        for note_id in ids:
            try:
                client.delete(note_id)
                deleted.append(note_id)
            except Exception as exc:  # noqa: BLE001
                failed.append((note_id, str(exc)))
    return deleted, failed


def update_entry(note_id: str, fields: dict[str, Any], api_key: str | None = None,
                 base_url: str = DEVIN_API_BASE) -> dict[str, Any]:
    """Partially update an entry: merge ``fields`` over the current values.

    Devin's PUT requires the full ``name``/``body``/``trigger_description``, so we
    fetch the current entry and overlay only the provided keys. Passing a key with
    an empty value clears optional fields (``pinned_repo``/``parent_folder_id``).
    """
    with get_client(api_key, base_url=base_url) as client:
        index = {k.get("id"): k for k in client.list_knowledge().get("knowledge", [])}
        cur = index.get(note_id)
        if not cur:
            raise DevinError(f"Knowledge entry '{note_id}' not found")
        merged = {f: (fields[f] if f in fields else cur.get(f)) for f in _UPDATABLE_FIELDS}
        payload: dict[str, Any] = {
            "name": merged.get("name") or "",
            "body": merged.get("body") or "",
            "trigger_description": merged.get("trigger_description") or "",
        }
        if merged.get("pinned_repo"):
            payload["pinned_repo"] = merged["pinned_repo"]
        if merged.get("parent_folder_id"):
            payload["parent_folder_id"] = merged["parent_folder_id"]
        return client.update(note_id, payload)


def move_entry(note_id: str, folder_id: str | None, api_key: str | None = None,
               base_url: str = DEVIN_API_BASE) -> dict[str, Any]:
    """Move an entry to ``folder_id`` (None = root) by re-sending its fields."""
    return update_entry(note_id, {"parent_folder_id": folder_id or ""},
                        api_key=api_key, base_url=base_url)
