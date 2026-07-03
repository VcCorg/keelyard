"""Build components catalog — the ingredients used to assemble an agent.

Backs the Build section's component pages (Tools, Retrievers, Databases,
Models) with real data derived from the CLI's template enums, the agent-tools
registry, and the skills registry. Every function degrades gracefully to an
empty (or supported-defaults) list so the pages always render.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ComponentItem(BaseModel):
    """A single build ingredient, normalized across component types."""
    id: str
    name: str
    description: str = ""
    category: Optional[str] = None
    tags: List[str] = []
    type: Optional[str] = None       # e.g. "built-in", "registry", "gemini", "semantic"
    available: bool = True
    detail: Optional[str] = None


class ComponentList(BaseModel):
    items: List[ComponentItem]
    total: int
    source: str


# ── Tools ────────────────────────────────────────────────────────────────

# Category for each built-in tool (mirrors the groupings in templates/enums.py).
_TOOL_CATEGORY: Dict[str, str] = {
    "calculator": "Utility", "text_analyzer": "Utility", "file_reader": "Utility", "file_writer": "Utility",
    "web_search": "Web", "web_scraper": "Web", "api_caller": "Web",
    "vector_search": "Retrieval", "document_loader": "Retrieval", "embeddings": "Retrieval",
    "kg_query": "Knowledge Graph", "kg_ingest": "Knowledge Graph", "entity_extractor": "Knowledge Graph",
    "code_executor": "Code", "code_analyzer": "Code", "git_tool": "Code",
    "csv_processor": "Data", "json_processor": "Data", "database_tool": "Data",
    "memory": "Agent", "agent_router": "Agent",
    "bitbucket_mcp": "MCP", "jira_mcp": "MCP", "kg_mcp_tool": "MCP", "confluence_mcp": "MCP",
}


def _repo_root() -> Optional[Path]:
    """Locate the workspace root by searching upward for agent-tools/registry.json."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "agent-tools" / "registry.json").exists():
            return parent
    return None


def list_tools() -> ComponentList:
    """Built-in template tools + tools from the agent-tools registry."""
    items: List[ComponentItem] = []

    # Built-in tools from the CLI template enum.
    try:
        from agentic_cli.templates.enums import Tool

        for value in Tool.choices():
            member = Tool(value)
            items.append(
                ComponentItem(
                    id=f"builtin:{value}",
                    name=member.display_name(),
                    description=f"Built-in {_TOOL_CATEGORY.get(value, 'agent')} tool",
                    category=_TOOL_CATEGORY.get(value, "Other"),
                    tags=[value],
                    type="built-in",
                )
            )
    except Exception:  # noqa: BLE001 - enum optional; registry tools still load
        pass

    # Reusable tools from the agent-tools registry.
    root = _repo_root()
    if root:
        try:
            data = json.loads((root / "agent-tools" / "registry.json").read_text())
            for tid, t in (data.get("tools") or {}).items():
                items.append(
                    ComponentItem(
                        id=f"registry:{tid}",
                        name=t.get("name", tid),
                        description=t.get("description", ""),
                        category=(t.get("category") or "integrations").title(),
                        tags=t.get("tags", []),
                        type="registry",
                        detail=t.get("version"),
                    )
                )
        except (OSError, json.JSONDecodeError):
            pass

    return ComponentList(items=items, total=len(items), source="enum+agent-tools")


# ── Databases ────────────────────────────────────────────────────────────

def list_databases() -> ComponentList:
    """Database connectors the platform supports (database-* skills)."""
    items: List[ComponentItem] = []
    try:
        from agentic_cli.analyzer.matcher import load_registry
        from agentic_cli.commands.code import _ensure_registry

        registry = load_registry(_ensure_registry())
        for skill in registry.get("skills", []):
            name = skill.get("name", "")
            if not name.startswith("database-"):
                continue
            engine = name.split("-", 1)[1]
            items.append(
                ComponentItem(
                    id=name,
                    name=engine.title(),
                    description=skill.get("description", ""),
                    category="Database",
                    tags=skill.get("tags", []),
                    type=engine,
                )
            )
    except Exception:  # noqa: BLE001 - registry optional
        pass
    return ComponentList(items=items, total=len(items), source="skills-registry")


# ── Retrievers ───────────────────────────────────────────────────────────

# Retriever backends the platform can build indexes on. Named indexes are
# created during onboarding / RAG; these are the supported building blocks.
_RETRIEVER_BACKENDS = [
    ("vector-faiss", "Vector index (FAISS)", "semantic",
     "Dense semantic similarity search over embeddings."),
    ("fts", "Full-text search", "lexical",
     "Keyword / BM25-style full-text retrieval."),
    ("kg-graph", "Knowledge-graph retriever", "graph",
     "Traverse a Neo4j/LightRAG semantic graph for grounded context."),
    ("hybrid", "Hybrid (vector + FTS)", "hybrid",
     "Blend semantic and lexical results for higher recall."),
]


def list_retrievers() -> ComponentList:
    """Supported retriever backends for building semantic/full-text indexes."""
    items = [
        ComponentItem(
            id=rid, name=name, description=desc,
            category="Retriever backend", type=rtype, tags=[rtype],
        )
        for rid, name, rtype, desc in _RETRIEVER_BACKENDS
    ]
    return ComponentList(items=items, total=len(items), source="supported-backends")


# ── Models ───────────────────────────────────────────────────────────────

_SUPPORTED_MODELS = [
    ("gemini-2.5-pro", "Most capable Gemini for complex reasoning and long context."),
    ("gemini-2.5-flash", "Fast, cost-efficient Gemini for most agent workloads."),
    ("gemini-2.5-flash-lite", "Lightweight Gemini for high-volume, low-latency tasks."),
    ("gemini-2.0-flash-001", "Stable default used by generated agent projects."),
]

_DEFAULT_MODEL = os.environ.get("VERTEX_AI_MODEL", "gemini-2.0-flash-001")


def list_models() -> ComponentList:
    """Supported LLM models (Vertex AI / Gemini), flagging the configured default."""
    items: List[ComponentItem] = []
    for mid, desc in _SUPPORTED_MODELS:
        is_default = mid == _DEFAULT_MODEL
        items.append(
            ComponentItem(
                id=mid,
                name=mid,
                description=desc,
                category="Vertex AI / Gemini",
                tags=["gemini"] + (["default"] if is_default else []),
                type="gemini",
                detail="Configured default" if is_default else None,
            )
        )
    return ComponentList(items=items, total=len(items), source="vertex-gemini")
