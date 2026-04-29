"""Glean REST API client.

Targets Glean REST API v1.
Reference: https://developers.glean.com/
"""

import logging
from typing import Any, Optional

import httpx

from .config import GleanConfig

logger = logging.getLogger(__name__)


class GleanClient:
    """Client for Glean REST API."""

    def __init__(self, config: GleanConfig):
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.api_base_url,
            headers=config.auth_headers,
            timeout=30.0,
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        """Make authenticated POST request."""
        resp = await self._client.post(path, json=json_data or {})
        resp.raise_for_status()
        return resp.json()

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make authenticated GET request."""
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _try_endpoints(
        self,
        endpoints: list[tuple[str, str, Optional[dict]]],
    ) -> dict[str, Any]:
        """Try multiple endpoint variations, return first success."""
        for method, path, body in endpoints:
            try:
                if method == "POST":
                    resp = await self._client.post(path, json=body or {})
                else:
                    resp = await self._client.get(path)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 404:
                    continue
            except Exception as e:
                logger.warning(f"Error trying {path}: {e}")
                continue

        return {
            "error": "No working endpoint found",
            "tried": [path for _, path, _ in endpoints],
        }

    # ── Search ───────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        datasources: Optional[list[str]] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search across Glean datasources."""
        payload: dict[str, Any] = {"query": query, "pageSize": limit}
        if datasources:
            payload["datasources"] = datasources
        return await self._post("/search", payload)

    # ── Documents ────────────────────────────────────────────────────────

    async def get_document(self, document_id: str) -> dict[str, Any]:
        """Retrieve a specific document by ID."""
        return await self._get(f"/documents/{document_id}")

    # ── Datasources ──────────────────────────────────────────────────────

    async def list_datasources(self) -> dict[str, Any]:
        """List available datasources."""
        return await self._try_endpoints([
            ("GET", "/datasources", None),
            ("GET", "/admin/datasources", None),
        ])

    # ── Agents / Chat ────────────────────────────────────────────────────

    async def list_agents(self) -> dict[str, Any]:
        """List available Glean agents/assistants."""
        return await self._try_endpoints([
            ("POST", "/chat/agents", {}),
            ("POST", "/listAgents", {}),
            ("GET", "/agents", None),
            ("POST", "/chat/listAgents", {}),
        ])

    async def chat(
        self,
        message: str,
        agent_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        include_citations: bool = True,
    ) -> dict[str, Any]:
        """Send a message to a Glean agent."""
        payload: dict[str, Any] = {
            "message": message,
            "stream": False,
            "includeCitations": include_citations,
        }
        if agent_id:
            payload["agentId"] = agent_id
        if chat_id:
            payload["chatId"] = chat_id

        return await self._try_endpoints([
            ("POST", "/chat", payload),
            ("POST", "/chat/send", payload),
            ("POST", "/messages/send", payload),
        ])

    async def get_conversation(self, chat_id: str) -> dict[str, Any]:
        """Retrieve conversation history by chat ID."""
        return await self._try_endpoints([
            ("POST", "/chat/retrieve", {"chatId": chat_id}),
            ("POST", "/retrievechatmessages", {"chatId": chat_id}),
            ("GET", f"/chat/{chat_id}", None),
        ])
