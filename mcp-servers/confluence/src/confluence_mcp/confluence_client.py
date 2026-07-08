"""Confluence Server REST API client.

Targets Confluence Server/Data Center REST API.
Reference: https://developer.atlassian.com/server/confluence/confluence-rest-api-examples/
"""

import logging
from typing import Any, Optional

import httpx

from .config import ConfluenceConfig

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Client for Confluence Server REST API."""

    def __init__(self, config: ConfluenceConfig):
        self.config = config
        self._client = httpx.Client(
            base_url=config.api_base_url,
            headers=config.auth_headers,
            verify=config.verify_ssl,
            timeout=30.0,
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make authenticated GET request."""
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        """Make authenticated POST request."""
        resp = self._client.post(path, json=json_data)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, json_data: Optional[dict] = None) -> dict:
        """Make authenticated PUT request."""
        resp = self._client.put(path, json=json_data)
        resp.raise_for_status()
        return resp.json()

    # ── Search ───────────────────────────────────────────────────────────

    def search_content(
        self,
        cql: str,
        limit: int = 10,
        start: int = 0,
        expand: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Search Confluence content using CQL (Confluence Query Language).

        Args:
            cql: CQL query string (e.g. 'type=page AND space=DEV AND text~"deployment"')
            limit: Maximum results per page
            start: Starting index for pagination
            expand: Fields to expand (e.g. ['body.storage', 'space', 'version'])
        """
        params: dict[str, Any] = {
            "cql": cql,
            "limit": limit,
            "start": start,
        }
        if expand:
            params["expand"] = ",".join(expand)

        data = self._get("/content/search", params)
        results = []
        for item in data.get("results", []):
            summary = self._summarize_content(item)
            summary["url"] = self._content_url(item)
            summary["excerpt"] = self.strip_html(item.get("excerpt", ""))
            results.append(summary)

        return {
            "total": data.get("totalSize", len(results)),
            "start": data.get("start", start),
            "limit": data.get("limit", limit),
            "results": results,
        }

    def _content_url(self, item: dict) -> str:
        """Absolute web URL for a content item (webui link, else viewpage by id)."""
        base = self.config.server_url.rstrip("/")
        webui = (item.get("_links", {}) or {}).get("webui", "")
        if webui:
            return f"{base}{webui}"
        cid = item.get("id", "")
        return f"{base}/pages/viewpage.action?pageId={cid}" if cid else base

    # ── Spaces ───────────────────────────────────────────────────────────

    def list_spaces(
        self, limit: int = 25, space_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List Confluence spaces.

        Args:
            limit: Maximum number of spaces
            space_type: Filter by type ('global', 'personal')
        """
        params: dict[str, Any] = {"limit": limit, "expand": "description.plain"}
        if space_type:
            params["type"] = space_type

        data = self._get("/space", params)
        spaces = []
        for s in data.get("results", []):
            spaces.append({
                "key": s.get("key", ""),
                "name": s.get("name", ""),
                "type": s.get("type", ""),
                "status": s.get("status", ""),
                "description": (
                    s.get("description", {}).get("plain", {}).get("value", "")
                ),
                "link": (
                    f"{self.config.server_url}/display/{s.get('key', '')}"
                ),
            })
        return spaces

    def get_space(self, space_key: str) -> dict[str, Any]:
        """Get space details by key."""
        data = self._get(
            f"/space/{space_key}",
            {"expand": "description.plain,homepage"},
        )
        homepage = data.get("homepage", {})
        return {
            "key": data.get("key", ""),
            "name": data.get("name", ""),
            "type": data.get("type", ""),
            "status": data.get("status", ""),
            "description": (
                data.get("description", {}).get("plain", {}).get("value", "")
            ),
            "homepage": {
                "id": homepage.get("id", ""),
                "title": homepage.get("title", ""),
            } if homepage else None,
            "link": f"{self.config.server_url}/display/{data.get('key', '')}",
        }

    # ── Pages ────────────────────────────────────────────────────────────

    def get_page(
        self,
        page_id: str,
        expand_body: bool = True,
    ) -> dict[str, Any]:
        """Get a page by ID.

        Args:
            page_id: Confluence page ID
            expand_body: Whether to include the page body content
        """
        expand = ["space", "version", "ancestors"]
        if expand_body:
            expand.append("body.storage")

        data = self._get(f"/content/{page_id}", {"expand": ",".join(expand)})
        result = self._summarize_content(data)

        if expand_body:
            body = data.get("body", {}).get("storage", {}).get("value", "")
            result["body_html"] = body

        ancestors = data.get("ancestors", [])
        result["ancestors"] = [
            {"id": a.get("id", ""), "title": a.get("title", "")}
            for a in ancestors
        ]
        return result

    def get_page_by_title(
        self,
        space_key: str,
        title: str,
        expand_body: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Find a page by space key and title."""
        params: dict[str, Any] = {
            "spaceKey": space_key,
            "title": title,
            "expand": "space,version",
        }
        if expand_body:
            params["expand"] += ",body.storage"

        data = self._get("/content", params)
        results = data.get("results", [])
        if not results:
            return None

        item = results[0]
        result = self._summarize_content(item)
        if expand_body:
            result["body_html"] = (
                item.get("body", {}).get("storage", {}).get("value", "")
            )
        return result

    def get_child_pages(
        self, page_id: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        """Get child pages of a given page."""
        data = self._get(
            f"/content/{page_id}/child/page",
            {"limit": limit, "expand": "space,version"},
        )
        return [self._summarize_content(c) for c in data.get("results", [])]

    def get_space_pages(
        self,
        space_key: str,
        limit: int = 25,
        start: int = 0,
    ) -> dict[str, Any]:
        """Get pages in a space."""
        params: dict[str, Any] = {
            "spaceKey": space_key,
            "type": "page",
            "limit": limit,
            "start": start,
            "expand": "version",
        }
        data = self._get("/content", params)
        pages = [self._summarize_content(c) for c in data.get("results", [])]
        return {
            "total": data.get("size", len(pages)),
            "start": start,
            "limit": limit,
            "pages": pages,
        }

    # ── Create / Update ────────────────────────────────────────────────

    def create_space(
        self,
        key: str,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new Confluence space.

        Args:
            key: Space key (uppercase, e.g. 'KEEL-CWOW')
            name: Display name for the space
            description: Space description
        """
        payload: dict[str, Any] = {
            "key": key,
            "name": name,
            "type": "global",
        }
        if description:
            payload["description"] = {
                "plain": {
                    "value": description,
                    "representation": "plain",
                }
            }

        data = self._post("/space", payload)
        return {
            "key": data.get("key", ""),
            "name": data.get("name", ""),
            "type": data.get("type", ""),
            "link": f"{self.config.server_url}/display/{data.get('key', '')}",
        }

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_page_id: Optional[str] = None,
        representation: str = "storage",
    ) -> dict[str, Any]:
        """Create a new Confluence page.

        Args:
            space_key: Space key to create the page in
            title: Page title
            body: Page content (HTML storage format by default)
            parent_page_id: Optional parent page ID for hierarchy
            representation: Body format - 'storage' (XHTML) or 'wiki'
        """
        payload: dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                representation: {
                    "value": body,
                    "representation": representation,
                }
            },
        }
        if parent_page_id:
            payload["ancestors"] = [{"id": parent_page_id}]

        data = self._post("/content", payload)
        return self._summarize_content(data)

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version_number: int,
        representation: str = "storage",
    ) -> dict[str, Any]:
        """Update an existing Confluence page.

        Args:
            page_id: ID of the page to update
            title: New page title
            body: New page content
            version_number: Current version number (will be incremented)
            representation: Body format - 'storage' (XHTML) or 'wiki'
        """
        payload = {
            "type": "page",
            "title": title,
            "version": {"number": version_number + 1},
            "body": {
                representation: {
                    "value": body,
                    "representation": representation,
                }
            },
        }
        data = self._put(f"/content/{page_id}", payload)
        return self._summarize_content(data)

    # ── Comments ─────────────────────────────────────────────────────────

    def get_page_comments(
        self, page_id: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        """Get comments on a page."""
        data = self._get(
            f"/content/{page_id}/child/comment",
            {"limit": limit, "expand": "body.storage,version"},
        )
        comments = []
        for c in data.get("results", []):
            comments.append({
                "id": c.get("id", ""),
                "body": c.get("body", {}).get("storage", {}).get("value", ""),
                "author": (
                    c.get("version", {}).get("by", {}).get("displayName", "unknown")
                ),
                "created": c.get("version", {}).get("when", ""),
            })
        return comments

    def add_page_comment(self, page_id: str, body: str) -> dict[str, Any]:
        """Add a comment to a page.

        Args:
            page_id: Confluence page ID
            body: Comment body in Confluence storage format (XHTML)
        """
        payload = {
            "type": "comment",
            "container": {"id": page_id, "type": "page"},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }
        data = self._post("/content", payload)
        return {
            "id": data.get("id", ""),
            "author": (
                data.get("version", {}).get("by", {}).get("displayName", "unknown")
            ),
            "created": data.get("version", {}).get("when", ""),
        }

    # ── Labels ───────────────────────────────────────────────────────────

    def get_page_labels(self, page_id: str) -> list[dict[str, Any]]:
        """Get labels on a page."""
        data = self._get(f"/content/{page_id}/label")
        return [
            {"name": l.get("name", ""), "prefix": l.get("prefix", "")}
            for l in data.get("results", [])
        ]

    # ── Attachments ────────────────────────────────────────────────────────

    def list_attachments(self, page_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """List attachments for a page.

        Args:
            page_id: Confluence page ID
            limit: Maximum number of attachments (default: 100)

        Returns list of attachments with metadata and download links.
        """
        data = self._get(
            f"/content/{page_id}/child/attachment",
            {"limit": limit, "expand": "version"},
        )
        attachments = []
        for a in data.get("results", []):
            version = a.get("version", {})
            links = a.get("_links", {})
            attachments.append({
                "id": a.get("id", ""),
                "filename": a.get("title", ""),
                "media_type": a.get("metadata", {}).get("mediaType", ""),
                "size": a.get("metadata", {}).get("size", 0),
                "version": version.get("number", 0),
                "created": version.get("when", ""),
                "created_by": version.get("by", {}).get("displayName", "unknown"),
                "_links": {
                    "download": f"{self.config.server_url}{links.get('download', '')}",
                    "self": f"{self.config.server_url}{links.get('self', '')}",
                },
            })
        return attachments

    def get_attachment(self, attachment_id: str) -> dict[str, Any]:
        """Get attachment metadata by ID.

        Args:
            attachment_id: Confluence attachment ID

        Returns attachment metadata with download link.
        """
        data = self._get(
            f"/content/{attachment_id}",
            {"expand": "version"},
        )
        version = data.get("version", {})
        links = data.get("_links", {})
        return {
            "id": data.get("id", ""),
            "filename": data.get("title", ""),
            "media_type": data.get("metadata", {}).get("mediaType", ""),
            "size": data.get("metadata", {}).get("size", 0),
            "version": version.get("number", 0),
            "created": version.get("when", ""),
            "created_by": version.get("by", {}).get("displayName", "unknown"),
            "_links": {
                "download": f"{self.config.server_url}{links.get('download', '')}",
                "self": f"{self.config.server_url}{links.get('self', '')}",
            },
        }

    def download_attachment_content(self, attachment_id: str) -> bytes:
        """Download attachment content as bytes.

        Args:
            attachment_id: Confluence attachment ID

        Returns raw bytes of the attachment file.
        """
        # Get the download link
        attachment = self.get_attachment(attachment_id)
        download_url = attachment["_links"]["download"]
        
        # Convert relative URL to absolute
        if download_url.startswith("/"):
            download_url = f"{self.config.api_base_url}{download_url}"
        
        # Download using the authenticated client
        resp = self._client.get(download_url)
        resp.raise_for_status()
        return resp.content

    def get_page_children(self, page_id: str) -> list[dict[str, Any]]:
        """Get direct child pages of a page.

        Args:
            page_id: Confluence page ID

        Returns list of child page metadata
        """
        data = self._get(
            f"/content/{page_id}/child/page",
            {"limit": 100},  # Get up to 100 child pages
        )
        
        results = data.get("results", [])
        children = []
        for child in results:
            children.append({
                "id": child.get("id", ""),
                "title": child.get("title", ""),
                "type": child.get("type", ""),
                "status": child.get("status", ""),
                "_links": child.get("_links", {}),
            })
        
        return children

    # ── Current User ─────────────────────────────────────────────────────

    def get_current_user(self) -> dict[str, Any]:
        """Get the currently authenticated user."""
        data = self._get("/user/current")
        return {
            "username": data.get("username", ""),
            "display_name": data.get("displayName", ""),
            "email": data.get("email", ""),
            "type": data.get("type", ""),
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _summarize_content(item: dict) -> dict[str, Any]:
        """Create a compact summary of a content item."""
        space = item.get("space", {})
        version = item.get("version", {})
        return {
            "id": item.get("id", ""),
            "type": item.get("type", ""),
            "title": item.get("title", ""),
            "status": item.get("status", ""),
            "space_key": space.get("key", ""),
            "space_name": space.get("name", ""),
            "version": version.get("number", 0),
            "last_updated": version.get("when", ""),
            "last_updated_by": (
                version.get("by", {}).get("displayName", "unknown")
            ),
        }

    @staticmethod
    def strip_html(html: str) -> str:
        """Basic HTML tag stripping for plain-text output."""
        import re
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text
