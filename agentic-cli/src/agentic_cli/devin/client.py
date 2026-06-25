"""Thin httpx wrapper over the Devin v1 API (Knowledge + Sessions).

Non-2xx responses raise :class:`DevinError` with the response body included, so
callers see Devin's real message (e.g. ``{"detail":"Unauthorized"}``) instead of
a bare status code.

TLS: ``verify`` defaults to :func:`resolve_verify` (env-driven), so corporate
proxies can supply a CA bundle (``DEVIN_CA_BUNDLE``) or disable verification
(``DEVIN_VERIFY_SSL=false``) without code changes.
"""
from __future__ import annotations

from typing import Any

from agentic_cli.devin.config import (
    DEVIN_API_BASE,
    DEVIN_API_KEY_ENV,
    resolve_api_key,
    resolve_verify,
)
from agentic_cli.devin.errors import DevinError


class DevinClient:
    """HTTP client for the Devin v1 API."""

    def __init__(self, api_key: str, base_url: str = DEVIN_API_BASE, timeout: float = 30.0,
                 verify: bool | str | None = None):
        import httpx

        if not api_key:
            raise ValueError("A Devin API key is required (DEVIN_API_KEY).")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
            verify=resolve_verify() if verify is None else verify,
        )

    def __enter__(self) -> "DevinClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any):
        r = self._client.request(method, path, **kwargs)
        if r.status_code >= 400:
            body = (r.text or "").strip()
            raise DevinError(f"{method} {path} -> {r.status_code} {body[:500]}")
        return r

    # ── Knowledge API ────────────────────────────────────────────────────────
    def list_knowledge(self) -> dict[str, Any]:
        return self._request("GET", "/knowledge").json()

    def list_folders(self) -> list[dict[str, Any]]:
        return self.list_knowledge().get("folders", [])

    def resolve_folder_id(self, name: str,
                          folders: list[dict[str, Any]] | None = None) -> str | None:
        for f in (folders if folders is not None else self.list_folders()):
            if f.get("name") == name:
                return f.get("id")
        return None

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/knowledge", json=payload).json()

    def update(self, note_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", f"/knowledge/{note_id}", json=payload).json()

    def delete(self, note_id: str) -> None:
        self._request("DELETE", f"/knowledge/{note_id}")

    # ── Sessions API ───────────────────────────────────────────────────────--
    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /sessions — trigger a new Devin session. Returns {session_id,url,...}."""
        return self._request("POST", "/sessions", json=payload).json()

    def get_session(self, session_id: str) -> dict[str, Any]:
        """GET /sessions/{id} — status + structured_output + messages."""
        return self._request("GET", f"/session/{session_id}").json()

    def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        """POST /sessions/{id}/message — send a follow-up instruction."""
        return self._request("POST", f"/session/{session_id}/message",
                             json={"message": message}).json()

    def list_sessions(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET /sessions — list sessions (optionally filtered)."""
        return self._request("GET", "/sessions", params=params or {}).json()


def get_client(api_key: str | None = None, base_url: str = DEVIN_API_BASE) -> DevinClient:
    key = resolve_api_key(api_key)
    if not key:
        raise ValueError(f"No Devin API key. Set ${DEVIN_API_KEY_ENV} or pass --api-key.")
    return DevinClient(key, base_url=base_url)
