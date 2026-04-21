"""DVA Knowledge Graph MCP Server.

Exposes knowledge graph search, query, and management tools via Model Context Protocol.
Supports both Neo4j and LightRAG backends. Designed for use with any MCP-compatible
AI coding assistant (Windsurf, Claude Desktop, OpenCode, Cursor, etc.).

Supports both stdio and SSE transports (set MCP_TRANSPORT=sse for Docker).
"""

import json
import logging
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .config import KGConfig
from .lightrag_client import LightRAGClient
from .neo4j_client import Neo4jKGClient
from .sources import SourceRegistry

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# ── Initialize MCP server ───────────────────────────────────────────────────

_transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
_mcp_kwargs = {
    "name": "DVA Knowledge Graph",
    "instructions": (
        "Access domain knowledge, business requirements, and project context "
        "from the DVA Knowledge Graph. Use these tools to understand business "
        "rules, search requirements, and explore domain entities when writing "
        "or reviewing code."
    ),
}
if _transport == "sse":
    _mcp_kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
    _mcp_kwargs["port"] = int(os.environ.get("MCP_PORT", "8131"))

mcp = FastMCP(**_mcp_kwargs)

# Lazy-initialized singletons
_config: KGConfig | None = None
_registry: SourceRegistry | None = None


def _get_config() -> KGConfig:
    global _config
    if _config is None:
        _config = KGConfig()
    return _config


def _get_registry() -> SourceRegistry:
    global _registry
    if _registry is None:
        _registry = SourceRegistry(_get_config())
    return _registry


def _get_lightrag() -> LightRAGClient:
    return LightRAGClient(_get_config())


def _get_neo4j() -> Neo4jKGClient:
    return Neo4jKGClient(_get_config())


# ═══════════════════════════════════════════════════════════════════════════
# Tier 1 — Primary tools (AI coding assistants use these most)
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def search_business_context(
    query: str,
    project: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Search domain knowledge and business requirements related to the query.

    Use this when you need to understand business rules, domain concepts, or
    requirements while writing or reviewing code. Returns relevant knowledge
    graph entries ranked by relevance.

    Args:
        query: What to search for (e.g. "patient eligibility rules",
               "care plan requirements", "CWOW data model")
        project: Optional project name to scope results. If omitted, searches
                 across all available knowledge.
        limit: Maximum number of results (default: 10)
    """
    config = _get_config()
    results: list[dict] = []

    # Try LightRAG first (better for semantic/RAG search)
    if config.is_lightrag_configured:
        try:
            with _get_lightrag() as client:
                if client.is_healthy():
                    resp = client.query(query, mode="hybrid", top_k=limit)
                    result_text = resp.get("result", "")
                    if result_text:
                        results.append({
                            "source": "lightrag",
                            "type": "semantic_search",
                            "content": result_text,
                        })
        except Exception as e:
            logger.warning(f"LightRAG search failed: {e}")

    # Also search Neo4j for structured entities
    if config.is_neo4j_configured:
        try:
            with _get_neo4j() as client:
                neo4j_results = client.search_text(query, limit=limit)
                for r in neo4j_results:
                    results.append({
                        "source": "neo4j",
                        "type": "entity",
                        "name": r.get("name", ""),
                        "labels": r.get("labels", []),
                        "content": (r.get("content", "") or "")[:500],
                        "persona": r.get("persona", ""),
                    })
        except Exception as e:
            logger.warning(f"Neo4j search failed: {e}")

    if not results:
        return json.dumps({
            "message": "No results found. The knowledge graph may be empty or the query didn't match.",
            "suggestion": "Try broader terms or check available projects with list_knowledge_projects.",
        })

    return json.dumps({"query": query, "results": results, "count": len(results)}, indent=2)


@mcp.tool()
def get_project_context(project: str) -> str:
    """Get a high-level overview of a project's business domain and requirements.

    Use this when starting work on a project or when you need to understand its
    scope, key entities, and domain model before writing code.

    Args:
        project: Project name (e.g. "cwow-patient", "care-plan-service")
    """
    config = _get_config()
    context: dict = {"project": project, "sources": [], "stats": {}, "summary": ""}

    # Get registered sources for this project
    registry = _get_registry()
    sources = registry.list_all(project=project)
    context["sources"] = [
        {
            "name": s.name,
            "type": s.source_type,
            "location": s.location,
            "status": s.status,
            "last_ingested": s.last_ingested,
        }
        for s in sources
    ]

    # Get stats from Neo4j
    if config.is_neo4j_configured:
        try:
            with _get_neo4j() as client:
                stats = client.get_stats()
                context["stats"]["neo4j"] = {
                    "nodes": stats.get("nodes", 0),
                    "relationships": stats.get("relationships", 0),
                    "node_types": stats.get("node_types", []),
                    "top_entities": stats.get("top_entities", [])[:5],
                }
        except Exception as e:
            logger.warning(f"Neo4j stats failed: {e}")

    # Get stats from LightRAG
    if config.is_lightrag_configured:
        try:
            with _get_lightrag() as client:
                if client.is_healthy():
                    stats = client.get_stats()
                    doc_status = client.get_document_status()
                    context["stats"]["lightrag"] = {
                        **stats,
                        "documents": doc_status.get("total_documents", 0),
                    }
        except Exception as e:
            logger.warning(f"LightRAG stats failed: {e}")

    # Build summary
    source_count = len(sources)
    ingested = sum(1 for s in sources if s.status == "ingested")
    context["summary"] = (
        f"Project '{project}' has {source_count} registered knowledge source(s) "
        f"({ingested} ingested). "
        f"Use search_business_context to query specific requirements."
    )

    return json.dumps(context, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# Tier 2 — Power tools (deeper exploration)
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def query_knowledge_graph(
    query: str,
    provider: str = "lightrag",
    format: str = "natural",
    persona: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Query the knowledge graph for entities, relationships, and structured data.

    Use this for targeted queries when you need specific information from the
    knowledge graph. Supports natural language (via LightRAG) or Cypher queries
    (via Neo4j).

    Args:
        query: Query text. For Neo4j with format='cypher', use Cypher syntax.
        provider: Backend to query - 'lightrag' (default, best for natural language)
                  or 'neo4j' (best for structured graph queries)
        format: Query format - 'natural' (default) or 'cypher' (Neo4j only)
        persona: Filter by perspective - 'developer' (code entities) or
                 'business' (requirements/docs). Optional.
        limit: Maximum results (default: 10)
    """
    config = _get_config()

    if provider == "lightrag":
        if not config.is_lightrag_configured:
            return json.dumps({"error": "LightRAG is not configured"})
        try:
            with _get_lightrag() as client:
                resp = client.query(query, mode="hybrid", top_k=limit)
                return json.dumps({
                    "provider": "lightrag",
                    "query": query,
                    "result": resp.get("result", "No results"),
                }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"LightRAG query failed: {e}"})

    elif provider == "neo4j":
        if not config.is_neo4j_configured:
            return json.dumps({"error": "Neo4j is not configured"})
        try:
            with _get_neo4j() as client:
                if format == "cypher":
                    results = client.query_cypher(query)
                else:
                    results = client.search_text(query, persona=persona, limit=limit)
                return json.dumps({
                    "provider": "neo4j",
                    "query": query,
                    "results": results,
                    "count": len(results),
                }, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": f"Neo4j query failed: {e}"})

    return json.dumps({"error": f"Unknown provider: {provider}"})


@mcp.tool()
def get_entity_details(entity_name: str) -> str:
    """Get detailed information about a specific business entity.

    Returns the entity's properties, type, and all its relationships to other
    entities. Use this to drill into a specific concept mentioned in search results.

    Args:
        entity_name: Name of the entity (e.g. "Patient", "Care Plan",
                     "Eligibility Check")
    """
    config = _get_config()

    if not config.is_neo4j_configured:
        return json.dumps({"error": "Neo4j is not configured for entity details"})

    try:
        with _get_neo4j() as client:
            details = client.get_entity_details(entity_name)
            return json.dumps(details, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to get entity details: {e}"})


# ═══════════════════════════════════════════════════════════════════════════
# Tier 3 — Source management tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def list_knowledge_projects() -> str:
    """List all available knowledge base projects and their registered sources.

    Shows what knowledge is available for querying. Each project may have
    multiple sources (document directories, Confluence spaces) that have
    been registered and ingested.
    """
    registry = _get_registry()
    sources = registry.list_all()

    if not sources:
        return json.dumps({
            "message": "No knowledge sources registered yet.",
            "hint": "Register sources using the CLI: dva data create --name <name> --source-type doc --source-location /path --project <project>",
        })

    # Group by project
    projects: dict[str, list] = {}
    for s in sources:
        proj = s.project or "(unassigned)"
        projects.setdefault(proj, []).append({
            "name": s.name,
            "type": s.source_type,
            "location": s.location,
            "status": s.status,
            "description": s.description,
        })

    return json.dumps({"projects": projects, "total_sources": len(sources)}, indent=2)


@mcp.tool()
def register_knowledge_source() -> str:
    """How to register a knowledge source for the knowledge graph.

    Sources are registered using the DVA CLI. Run these commands in a terminal:

    For documents:
      dva data create --name <name> --source-type doc --source-location /path/to/docs --project <project>

    For Confluence:
      dva data create --name <name> --source-type confluence --source-location https://confluence.example.com --confluence-space <SPACE> --project <project>

    After registration, use ingest_knowledge_source(name='<name>') to index the source.
    Use list_knowledge_projects() to see registered sources.
    """
    return json.dumps({
        "instructions": "Register sources using the DVA CLI",
        "commands": {
            "document": "dva data create --name <name> --source-type doc --source-location /path/to/docs --project <project>",
            "confluence": "dva data create --name <name> --source-type confluence --source-location https://confluence.example.com --confluence-space <SPACE> --project <project>",
        },
        "list": "dva data list",
        "delete": "dva data delete <name>",
    }, indent=2)


@mcp.tool()
def ingest_knowledge_source(
    name: str,
    extract_entities: bool = True,
) -> str:
    """Ingest a registered knowledge source into the knowledge graph.

    Reads documents or Confluence pages from the registered source and indexes
    them into the knowledge graph for search and querying.

    Args:
        name: Name of the registered source to ingest
        extract_entities: Whether to use AI to extract entities and relationships
                          from the source content (default: True)
    """
    config = _get_config()
    registry = _get_registry()
    source = registry.get(name)

    if not source:
        return json.dumps({"error": f"Source '{name}' not found. Register it first."})

    registry.update_status(name, "ingesting")

    try:
        results = {"source": name, "type": source.source_type, "documents_processed": 0}

        if source.source_type == "document":
            results.update(_ingest_documents(source, config))
        elif source.source_type == "confluence":
            results.update(_ingest_confluence(source, config))

        registry.update_status(name, "ingested")
        results["status"] = "completed"
        return json.dumps(results, indent=2)

    except Exception as e:
        registry.update_status(name, "failed")
        return json.dumps({"error": f"Ingestion failed: {e}", "source": name})


def _ingest_documents(source, config: KGConfig) -> dict:
    """Ingest from a local document directory into LightRAG."""
    from pathlib import Path

    source_path = Path(source.location)
    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source.location}")

    extensions = {".txt", ".md", ".pdf", ".json", ".csv"}
    files = [f for f in source_path.rglob("*") if f.suffix.lower() in extensions and f.is_file()]

    if not files:
        return {"documents_processed": 0, "message": "No supported files found"}

    processed = 0
    total_chars = 0

    if config.is_lightrag_configured:
        with _get_lightrag() as client:
            if not client.is_healthy():
                raise ConnectionError("LightRAG is not reachable")

            for file_path in files:
                try:
                    text = file_path.read_text(errors="ignore")
                    if text.strip():
                        metadata = {
                            "source_name": source.name,
                            "project": source.project,
                            "file_name": file_path.name,
                            "persona": "business",
                        }
                        resp = client.insert(text, metadata=metadata)
                        processed += 1
                        total_chars += resp.get("characters", len(text))
                except Exception as e:
                    logger.warning(f"Failed to ingest {file_path.name}: {e}")

    return {"documents_processed": processed, "total_files": len(files), "total_characters": total_chars}


def _ingest_confluence(source, config: KGConfig) -> dict:
    """Ingest from a Confluence space into LightRAG.

    Uses the confluence-mcp service or direct Confluence REST API to fetch pages,
    then inserts them into LightRAG.
    """
    # For now, use httpx to call Confluence REST API directly
    import httpx

    confluence_url = source.location.rstrip("/")
    space_key = source.confluence_space

    if not space_key:
        raise ValueError("Confluence space key is required for confluence sources")

    # Get Confluence auth from environment
    confluence_token = os.environ.get("CONFLUENCE_PERSONAL_ACCESS_TOKEN", "")
    if not confluence_token:
        raise ValueError(
            "CONFLUENCE_PERSONAL_ACCESS_TOKEN environment variable is required "
            "for Confluence ingestion"
        )

    headers = {
        "Authorization": f"Bearer {confluence_token}",
        "Accept": "application/json",
    }

    # Fetch pages from space
    api_url = f"{confluence_url}/rest/api/content"
    params = {
        "spaceKey": space_key,
        "type": "page",
        "limit": 100,
        "expand": "body.storage,space,version",
    }

    processed = 0
    total_chars = 0

    try:
        with httpx.Client(timeout=30.0, verify=True) as http:
            resp = http.get(api_url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("results", [])

            if config.is_lightrag_configured:
                with _get_lightrag() as client:
                    if not client.is_healthy():
                        raise ConnectionError("LightRAG is not reachable")

                    for page in pages:
                        try:
                            title = page.get("title", "")
                            body_html = (
                                page.get("body", {})
                                .get("storage", {})
                                .get("value", "")
                            )
                            # Strip HTML for cleaner text
                            import re
                            body_text = re.sub(r"<[^>]+>", " ", body_html)
                            body_text = re.sub(r"\s+", " ", body_text).strip()

                            if body_text:
                                text = f"# {title}\n\n{body_text}"
                                metadata = {
                                    "source_name": source.name,
                                    "project": source.project,
                                    "page_title": title,
                                    "page_id": str(page.get("id", "")),
                                    "space_key": space_key,
                                    "persona": "business",
                                }
                                client.insert(text, metadata=metadata)
                                processed += 1
                                total_chars += len(text)
                        except Exception as e:
                            logger.warning(f"Failed to ingest page '{title}': {e}")

    except httpx.HTTPStatusError as e:
        raise ConnectionError(f"Confluence API error: {e.response.status_code} {e.response.text[:200]}")

    return {
        "documents_processed": processed,
        "total_pages_found": len(pages) if "pages" in dir() else 0,
        "total_characters": total_chars,
        "space_key": space_key,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════════════════


@mcp.resource("kg://config")
def get_config_resource() -> str:
    """Current KG MCP Server configuration (without secrets)."""
    config = _get_config()
    return json.dumps({
        "default_provider": config.default_provider,
        "neo4j_configured": config.is_neo4j_configured,
        "neo4j_uri": config.neo4j_uri,
        "lightrag_configured": config.is_lightrag_configured,
        "lightrag_url": config.lightrag_url,
    }, indent=2)


@mcp.resource("kg://sources")
def get_sources_resource() -> str:
    """List of all registered knowledge sources."""
    registry = _get_registry()
    sources = registry.list_all()
    return json.dumps([s.to_dict() for s in sources], indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════


def main():
    """Run the MCP server."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"Starting DVA Knowledge Graph MCP server (transport={transport})...")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
