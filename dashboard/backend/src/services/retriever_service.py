"""Named retriever instances — first-class semantic/full-text indexes.

Turns retrievers from "supported backends" into named, persisted objects an
agent can bind to (e.g. a FAISS index with a gemini-embedding model over a
data source). Instances are stored in a small JSON registry under ~/.dva so
they survive restarts without requiring the KG/vector infra to be running.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

_STORE = Path.home() / ".dva" / "retrievers.json"

# Retriever backends that may back an instance (mirrors the catalog).
VALID_BACKENDS = {"faiss", "fts", "kg", "hybrid"}


class RetrieverInstance(BaseModel):
    id: str
    name: str
    description: str = ""
    backend: str = "faiss"
    embedding_model: Optional[str] = None
    source: Optional[str] = None
    created_at: str


class RetrieverList(BaseModel):
    items: List[RetrieverInstance]
    total: int


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


def list_instances() -> RetrieverList:
    items = [RetrieverInstance(**r) for r in _load().get("retrievers", [])]
    return RetrieverList(items=items, total=len(items))


def create_instance(
    name: str,
    backend: str = "faiss",
    embedding_model: Optional[str] = None,
    source: Optional[str] = None,
    description: str = "",
) -> RetrieverInstance:
    name = (name or "").strip()
    if not name:
        raise ValueError("Retriever name is required")
    backend = (backend or "faiss").lower()
    if backend not in VALID_BACKENDS:
        raise ValueError(f"Unknown backend '{backend}'. Valid: {', '.join(sorted(VALID_BACKENDS))}")

    instance = RetrieverInstance(
        id=uuid.uuid4().hex[:12],
        name=name,
        description=description or "",
        backend=backend,
        embedding_model=embedding_model or None,
        source=source or None,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    data = _load()
    data.setdefault("retrievers", []).append(instance.model_dump())
    _save(data)
    return instance


def delete_instance(retriever_id: str) -> bool:
    data = _load()
    before = len(data.get("retrievers", []))
    data["retrievers"] = [r for r in data.get("retrievers", []) if r.get("id") != retriever_id]
    _save(data)
    return len(data["retrievers"]) < before
