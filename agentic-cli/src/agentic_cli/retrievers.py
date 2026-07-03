"""Named retriever instances — CLI-owned registry.

First-class semantic/full-text indexes an agent can bind to (e.g. a FAISS
index with an embedding model over a data source). The registry lives in the
CLI so it is the single source of truth; the dashboard delegates here. Every
mutation is recorded in the central audit trail.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Optional

from agentic_cli.tracker import DB_DIR, record_action

VALID_BACKENDS = {"faiss", "fts", "kg", "hybrid"}
_STORE = DB_DIR / "retrievers.json"


def _load() -> dict:
    if not _STORE.exists():
        return {"retrievers": []}
    try:
        return json.loads(_STORE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"retrievers": []}


def _save(data: dict) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(data, indent=2))


def list_instances() -> List[dict]:
    return _load().get("retrievers", [])


def create_instance(
    name: str,
    backend: str = "faiss",
    embedding_model: Optional[str] = None,
    source: Optional[str] = None,
    description: str = "",
    *,
    origin: str = "cli",
    correlation_id: Optional[str] = None,
) -> dict:
    """Create and persist a named retriever instance, auditing the action."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Retriever name is required")
    backend = (backend or "faiss").lower()
    if backend not in VALID_BACKENDS:
        raise ValueError(f"Unknown backend '{backend}'. Valid: {', '.join(sorted(VALID_BACKENDS))}")

    instance = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "description": description or "",
        "backend": backend,
        "embedding_model": embedding_model or None,
        "source": source or None,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    data = _load()
    data.setdefault("retrievers", []).append(instance)
    _save(data)

    try:
        record_action(
            "retriever", "create",
            entity_type="retriever", entity_id=instance["id"],
            correlation_id=correlation_id, source=origin,
            details={"name": name, "backend": backend},
        )
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return instance


def delete_instance(retriever_id: str, *, origin: str = "cli") -> bool:
    data = _load()
    before = len(data.get("retrievers", []))
    data["retrievers"] = [r for r in data.get("retrievers", []) if r.get("id") != retriever_id]
    _save(data)
    deleted = len(data["retrievers"]) < before
    if deleted:
        try:
            record_action(
                "retriever", "delete",
                entity_type="retriever", entity_id=retriever_id, source=origin,
            )
        except Exception:  # noqa: BLE001
            pass
    return deleted
