"""ConfluenceSource — fetches tracked domain docs for the enrichment pass.

This is the DVA analog of the GCP agent's web pass. Instead of crawling arbitrary
URLs via fetch_url, it reads the Confluence pages already registered for the
domain (`dva domain add-docs`) through the Confluence MCP server. Each page
becomes enrichment material the LLM uses to augment existing OKF concepts or mint
`references/<slug>` concepts.

No seed URLs are accepted from the CLI: the page set comes entirely from domain
data (`get_domain_docs`).
"""
from __future__ import annotations

import re
from typing import Any

from agentic_cli.kg.okf.enrichment.source import ConceptRef, Source
from agentic_cli.kg.okf.schema import slugify

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")
_MAX_BODY_CHARS = 8000


def _html_to_text(html: str) -> str:
    """Very small HTML->text reduction for Confluence storage-format bodies."""
    if not html:
        return ""
    text = re.sub(r"<(br|/p|/h[1-6]|/li|/tr)\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    )
    text = _WS_RE.sub(" ", text)
    text = _BLANK_RE.sub("\n\n", text)
    return text.strip()


class ConfluenceSource(Source):
    name = "confluence"

    def __init__(self, page_ids: list[str], titles: dict[str, str] | None = None):
        self.page_ids = [str(p) for p in page_ids if p]
        self.titles = titles or {}

    @classmethod
    def from_domain_docs(cls, docs: list[dict[str, Any]]) -> "ConfluenceSource":
        ids = [d["source_page_id"] for d in docs if d.get("source_page_id")]
        titles = {
            str(d["source_page_id"]): (d.get("title") or "")
            for d in docs if d.get("source_page_id")
        }
        return cls(ids, titles)

    def list_concepts(self) -> list[ConceptRef]:
        refs: list[ConceptRef] = []
        for pid in self.page_ids:
            title = self.titles.get(pid, "") or f"page-{pid}"
            refs.append(
                ConceptRef(
                    id=("references", slugify(title)),
                    type="Requirement",
                    resource=f"confluence://{pid}",
                    hint={"page_id": pid, "title": title},
                )
            )
        return refs

    def read_concept(self, ref: ConceptRef) -> dict[str, Any]:
        pid = ref.hint.get("page_id")
        if not pid:
            return {}
        return self.fetch_page(pid)

    def fetch_page(self, page_id: str) -> dict[str, Any]:
        """Fetch a Confluence page body via MCP, reduced to plain text."""
        from agentic_cli.mcp_tool_client import MCPToolError, confluence_get_page

        try:
            page = confluence_get_page(str(page_id), include_body=True)
        except MCPToolError as e:
            return {"page_id": page_id, "error": str(e)}

        if not isinstance(page, dict):
            return {"page_id": page_id, "error": "unexpected MCP response"}

        body = (
            page.get("body")
            or page.get("content")
            or (page.get("storage") or {}).get("value", "")
        )
        if isinstance(body, dict):
            body = body.get("value", "") or body.get("storage", {}).get("value", "")

        return {
            "page_id": str(page_id),
            "title": page.get("title") or self.titles.get(str(page_id), ""),
            "space": page.get("space") or page.get("spaceKey", ""),
            "url": page.get("url") or page.get("_links", {}).get("webui", ""),
            "text": _html_to_text(str(body))[:_MAX_BODY_CHARS],
        }
