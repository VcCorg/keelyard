"""Named retriever instances — thin dashboard delegation to the CLI.

The retriever registry is CLI-owned (``agentic_cli.retrievers``) so it is the
single source of truth and every mutation is audited. The dashboard keeps its
pydantic response models and delegates create/list/delete to the CLI, tagging
mutations as ``origin="dashboard"``.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

# Backends that may back an instance (mirrors the CLI registry).
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


def list_instances() -> RetrieverList:
    from agentic_cli import retrievers as retr

    items = [RetrieverInstance(**r) for r in retr.list_instances()]
    return RetrieverList(items=items, total=len(items))


def create_instance(
    name: str,
    backend: str = "faiss",
    embedding_model: Optional[str] = None,
    source: Optional[str] = None,
    description: str = "",
) -> RetrieverInstance:
    from agentic_cli import retrievers as retr

    inst = retr.create_instance(
        name,
        backend=backend,
        embedding_model=embedding_model,
        source=source,
        description=description,
        origin="dashboard",
    )
    return RetrieverInstance(**inst)


def delete_instance(retriever_id: str) -> bool:
    from agentic_cli import retrievers as retr

    return retr.delete_instance(retriever_id, origin="dashboard")
