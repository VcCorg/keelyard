"""LightRAG HTTP client for KG MCP Server.

Talks directly to the LightRAG REST API for document insertion, querying,
and search. Supports workspace-scoped operations.
"""

import logging
from typing import Any

import httpx

from .config import KGConfig

logger = logging.getLogger(__name__)


class LightRAGClient:
    """HTTP client for LightRAG REST API."""

    def __init__(self, config: KGConfig):
        self._config = config
        self._client = httpx.Client(
            base_url=config.lightrag_url.rstrip("/"),
            timeout=config.lightrag_timeout,
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Health ──────────────────────────────────────────────────────────

    def is_healthy(self) -> bool:
        """Check if LightRAG is reachable."""
        try:
            resp = self._client.get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    # ── Insert ──────────────────────────────────────────────────────────

    def insert(self, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Insert text into LightRAG."""
        payload: dict[str, Any] = {"text": text}
        if metadata:
            payload["metadata"] = metadata
        resp = self._client.post("/insert", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ── Query ───────────────────────────────────────────────────────────

    def query(
        self, query: str, *, mode: str = "hybrid", top_k: int = 10
    ) -> dict[str, Any]:
        """Query LightRAG using natural language."""
        resp = self._client.post(
            "/query",
            json={"query": query, "mode": mode, "top_k": top_k},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Search ──────────────────────────────────────────────────────────

    def search(self, query: str, *, top_k: int = 10) -> dict[str, Any]:
        """Semantic search in LightRAG."""
        resp = self._client.post(
            "/search",
            json={"query": query, "top_k": top_k},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Stats ───────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get LightRAG statistics."""
        resp = self._client.get("/stats")
        resp.raise_for_status()
        return resp.json()

    def get_document_status(self) -> dict[str, Any]:
        """Get document ingestion status."""
        resp = self._client.get("/document-status")
        resp.raise_for_status()
        return resp.json()
