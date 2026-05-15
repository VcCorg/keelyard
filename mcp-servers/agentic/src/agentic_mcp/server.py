"""Agentic Platform Central MCP Server.

Exposes domain management, code onboarding/tracking, skill resolution,
and activity tracking tools via Model Context Protocol.

Shares the same tracker.db as the agentic CLI (~/.agent-cli-agentic/tracker.db).
Supports both stdio and SSE transports (set MCP_TRANSPORT=sse for Docker).
"""

import json
import logging
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .config import AgenticConfig
from .db import TrackerDB

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# ── Initialize MCP server ───────────────────────────────────────────────────

_transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
_mcp_kwargs = {
    "name": "Agentic Platform",
    "instructions": (
        "Central Agentic Platform service. Use these tools to manage products, "
        "domains, repos, onboarding, skills, and activity tracking. All data is "
        "stored in the shared tracker database."
    ),
}
if _transport == "sse":
    _mcp_kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
    _mcp_kwargs["port"] = int(os.environ.get("MCP_PORT", "8132"))

mcp = FastMCP(**_mcp_kwargs)

# Lazy-initialized singletons
_config: AgenticConfig | None = None
_db: TrackerDB | None = None


def _get_config() -> AgenticConfig:
    global _config
    if _config is None:
        _config = AgenticConfig()
    return _config


def _get_db() -> TrackerDB:
    global _db
    if _db is None:
        _db = TrackerDB(_get_config().tracker_db)
    return _db


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 1: Product Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def product_create(name: str, description: str = "", tags: Optional[list[str]] = None) -> str:
    """Register a new product (e.g., CWOW, IMTO).

    Products are the top-level grouping. Domains belong to products.

    Args:
        name: Product name (uppercase, e.g. "CWOW")
        description: Optional product description
        tags: Optional list of tags
    """
    try:
        result = _get_db().product_create(name, description, tags or [])
        return json.dumps({"status": "created", **result})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def product_list() -> str:
    """List all registered products."""
    return json.dumps(_get_db().product_list())


@mcp.tool()
def product_get(name: str) -> str:
    """Get details of a specific product.

    Args:
        name: Product name
    """
    result = _get_db().product_get(name)
    if result:
        return json.dumps(result)
    return json.dumps({"error": f"Product '{name}' not found"})


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 2: Domain Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def domain_create(
    domain: str,
    product: str,
    description: str = "",
    jira: str = "",
    bb: str = "",
    confluence: str = "",
) -> str:
    """Register a domain under a product.

    The slug is auto-generated as "<product>-<domain>" in lowercase.

    Args:
        domain: Domain label (e.g. "Facility")
        product: Product name (must exist, e.g. "CWOW")
        description: Optional domain description
        jira: Jira project key (e.g. "CWOW")
        bb: Bitbucket project key (e.g. "CGF")
        confluence: Confluence space key (e.g. "MTT")
    """
    try:
        # Verify product exists
        if not _get_db().product_get(product):
            return json.dumps({"error": f"Product '{product}' not found. Create it first."})

        slug = f"{product}-{domain}".lower().replace(" ", "-")
        result = _get_db().domain_create(
            slug=slug, product=product, domain_label=domain,
            description=description, jira=jira, bb=bb, confluence=confluence,
        )
        return json.dumps({"status": "created", "slug": slug, **result})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def domain_list(product: Optional[str] = None) -> str:
    """List all registered domains, optionally filtered by product.

    Args:
        product: Optional product name to filter by
    """
    return json.dumps(_get_db().domain_list(product))


@mcp.tool()
def domain_get(slug: str) -> str:
    """Get domain details with linked repos and docs.

    Args:
        slug: Domain slug (e.g. "cwow-facility")
    """
    domain = _get_db().domain_get(slug)
    if not domain:
        return json.dumps({"error": f"Domain '{slug}' not found"})

    repos = _get_db().domain_list_repos(slug)
    docs = _get_db().domain_list_docs(slug)
    domain["repos"] = repos
    domain["docs"] = docs
    return json.dumps(domain)


@mcp.tool()
def domain_link_repo(domain_slug: str, repo_slug: str, clone_url: str = "") -> str:
    """Link a repository to a domain.

    Args:
        domain_slug: Domain slug (e.g. "cwow-facility")
        repo_slug: Repository slug/name
        clone_url: Optional clone URL
    """
    try:
        result = _get_db().domain_link_repo(domain_slug, repo_slug, clone_url)
        return json.dumps({"status": "linked", **result})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def domain_unlink_repo(domain_slug: str, repo_slug: str) -> str:
    """Unlink a repository from a domain.

    Args:
        domain_slug: Domain slug
        repo_slug: Repository slug
    """
    removed = _get_db().domain_unlink_repo(domain_slug, repo_slug)
    return json.dumps({"status": "unlinked" if removed else "not_found"})


@mcp.tool()
def domain_list_repos(domain_slug: str) -> str:
    """List repositories linked to a domain.

    Args:
        domain_slug: Domain slug
    """
    return json.dumps(_get_db().domain_list_repos(domain_slug))


@mcp.tool()
def domain_add_doc(
    domain_slug: str, page_id: str, space_key: str = "", title: str = ""
) -> str:
    """Track a Confluence doc for a domain.

    Args:
        domain_slug: Domain slug
        page_id: Confluence page ID
        space_key: Confluence space key
        title: Page title
    """
    try:
        result = _get_db().domain_add_doc(domain_slug, page_id, space_key, title)
        return json.dumps({"status": "added", **result})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def domain_list_docs(domain_slug: str) -> str:
    """List Confluence docs tracked for a domain.

    Args:
        domain_slug: Domain slug
    """
    return json.dumps(_get_db().domain_list_docs(domain_slug))


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 3: Repo / Onboarding Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def repo_register(
    name: str,
    path: str,
    repo_url: str = "",
    languages: Optional[list[str]] = None,
    frameworks: Optional[list[str]] = None,
    build_tools: Optional[list[str]] = None,
    test_frameworks: Optional[list[str]] = None,
    databases: Optional[list[str]] = None,
    dependencies: int = 0,
    skills_installed: Optional[list[str]] = None,
    has_docker: bool = False,
) -> str:
    """Register (or update) an onboarded repository in the central tracker.

    Call this after onboarding a repo to make it visible across the platform.

    Args:
        name: Repository name
        path: Absolute path on disk
        repo_url: Git remote URL
        languages: Detected languages (e.g. ["Java", "Python"])
        frameworks: Detected frameworks (e.g. ["Spring Boot"])
        build_tools: Detected build tools (e.g. ["Maven"])
        test_frameworks: Detected test frameworks
        databases: Detected databases
        dependencies: Total dependency count
        skills_installed: List of installed skill names
        has_docker: Whether Docker files were detected
    """
    try:
        result = _get_db().repo_register(
            name=name, path=path, repo_url=repo_url,
            languages=languages, frameworks=frameworks,
            build_tools=build_tools, test_frameworks=test_frameworks,
            databases=databases, dependencies=dependencies,
            skills_installed=skills_installed, has_docker=has_docker,
        )
        return json.dumps({"status": "registered", **result})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def repo_list() -> str:
    """List all onboarded repositories."""
    return json.dumps(_get_db().repo_list())


@mcp.tool()
def repo_get(path: str) -> str:
    """Get details of a specific onboarded repository.

    Args:
        path: Absolute path of the repository
    """
    result = _get_db().repo_get(path)
    if result:
        return json.dumps(result)
    return json.dumps({"error": f"Repo at '{path}' not found"})


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 4: Activity / Tracking Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def activity_log(
    command: str,
    subcommand: str = "",
    status: str = "success",
    duration_ms: int = 0,
    args: Optional[dict] = None,
    details: Optional[dict] = None,
    repo_path: str = "",
) -> str:
    """Record an activity in the central activity log.

    Args:
        command: Command group (e.g. "onboard", "domain", "skill")
        subcommand: Subcommand (e.g. "detect", "create", "install")
        status: "success" or "error"
        duration_ms: Duration in milliseconds
        args: Significant arguments as a dict
        details: Result details or error message as a dict
        repo_path: Associated repository path
    """
    result = _get_db().activity_log(
        command=command, subcommand=subcommand, status=status,
        duration_ms=duration_ms, args=args, details=details, repo_path=repo_path,
    )
    return json.dumps({"status": "logged", **result})


@mcp.tool()
def activity_recent(limit: int = 25) -> str:
    """Get recent activity log entries.

    Args:
        limit: Maximum number of entries (default 25)
    """
    return json.dumps(_get_db().activity_recent(limit))


@mcp.tool()
def activity_summary() -> str:
    """Get a summary of platform usage: counts of repos, projects, products, domains, activities."""
    return json.dumps(_get_db().activity_summary())


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 5: Skills / Registry Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def registry_list() -> str:
    """List all skills in the local skills registry (registry.json)."""
    config = _get_config()
    registry_path = config.skills_registry
    if not registry_path.exists():
        return json.dumps({"error": f"Registry not found at {registry_path}"})

    with open(registry_path) as f:
        registry = json.load(f)

    skills = registry.get("skills", [])
    return json.dumps([{"name": s["name"], "description": s.get("description", "")} for s in skills])


@mcp.tool()
def skill_available(skill_name: str) -> str:
    """Check if a specific skill exists in the local registry and return its details.

    Args:
        skill_name: Name of the skill to look up
    """
    config = _get_config()
    skill_dir = config.skills_dir / skill_name

    if not skill_dir.exists():
        return json.dumps({"exists": False, "name": skill_name})

    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text() if skill_md.exists() else ""

    return json.dumps({"exists": True, "name": skill_name, "path": str(skill_dir), "has_skill_md": skill_md.exists(), "preview": content[:500]})


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 6: Knowledge Graph Query Tools
# These tools expose the linked Neo4j graph to IDE agents and developer workflows.
# They connect to Neo4j via env vars: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# ═══════════════════════════════════════════════════════════════════════════

def _neo4j_query(cypher: str, params: dict) -> list:
    """Execute a read-only Cypher query against Neo4j. Returns list of record dicts."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        raise RuntimeError("neo4j package not installed in MCP server environment.")

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")

    if not password:
        raise RuntimeError(
            "NEO4J_PASSWORD env var not set. Add it to the MCP server environment."
        )

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            result = session.run(cypher, **params)
            return [dict(record) for record in result]
    finally:
        driver.close()


@mcp.tool()
def kg_get_requirements_for_code(domain: str, repo_name: str) -> str:
    """Get requirement documents linked to a code repository in the knowledge graph.

    Use this when a developer opens a repo in the IDE to instantly understand
    which business requirements this code implements.

    Args:
        domain: Domain slug (e.g. "cwow-facility")
        repo_name: Repository name or partial name (e.g. "medication-standard")
    """
    try:
        cypher = """
        MATCH (c)-[r]->(d:Document)
        WHERE c._source = 'dva_kg'
          AND c.persona = 'developer'
          AND (c.domain = $domain OR c.metadata CONTAINS $domain)
          AND toLower(c.name) CONTAINS toLower($repo_name)
          AND r.linked_by = 'dva-kg-link'
        RETURN c.name AS code_name,
               labels(c) AS code_type,
               type(r) AS relationship,
               r.confidence AS confidence,
               r.evidence AS evidence,
               d.name AS requirement_name,
               d.id AS requirement_id
        ORDER BY r.confidence DESC
        LIMIT 50
        """
        records = _neo4j_query(cypher, {"domain": domain, "repo_name": repo_name})

        if not records:
            return json.dumps({
                "domain": domain,
                "repo_name": repo_name,
                "requirements": [],
                "message": (
                    f"No linked requirements found for repo '{repo_name}' in domain '{domain}'. "
                    "Run `dva kg link --domain {domain}` to generate links."
                ),
            })

        requirements = [
            {
                "requirement_name": r["requirement_name"],
                "requirement_id": r["requirement_id"],
                "relationship": r["relationship"],
                "confidence": r["confidence"],
                "evidence": r["evidence"],
                "code_entity": r["code_name"],
                "code_type": (r["code_type"] or ["Unknown"])[0],
            }
            for r in records
        ]
        return json.dumps({
            "domain": domain,
            "repo_name": repo_name,
            "requirements": requirements,
            "total": len(requirements),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def kg_get_code_for_requirement(domain: str, requirement_id: str) -> str:
    """Get code entities that implement a specific requirement.

    Use this when a developer picks up a Jira ticket to see which code already
    implements parts of the requirement and what still needs to be built.

    Args:
        domain: Domain slug (e.g. "cwow-facility")
        requirement_id: OneView/Jira ID or partial title (e.g. "CWOW-278922" or "HDF Treatment")
    """
    try:
        cypher = """
        MATCH (c)-[r]->(d:Document)
        WHERE c._source = 'dva_kg'
          AND c.persona = 'developer'
          AND (c.domain = $domain OR c.metadata CONTAINS $domain)
          AND r.linked_by = 'dva-kg-link'
          AND (
            toLower(d.name) CONTAINS toLower($req_id)
            OR toLower(d.id) CONTAINS toLower($req_id)
            OR toLower(coalesce(d.content, '')) CONTAINS toLower($req_id)
          )
        RETURN c.id AS code_id,
               c.name AS code_name,
               labels(c) AS code_type,
               type(r) AS relationship,
               r.confidence AS confidence,
               r.evidence AS evidence,
               d.name AS requirement_name,
               d.id AS requirement_id
        ORDER BY r.confidence DESC
        LIMIT 50
        """
        records = _neo4j_query(cypher, {"domain": domain, "req_id": requirement_id})

        if not records:
            return json.dumps({
                "domain": domain,
                "requirement_id": requirement_id,
                "code_entities": [],
                "message": (
                    f"No code found implementing '{requirement_id}' in domain '{domain}'. "
                    "This requirement may not be implemented yet, or run `dva kg link` to generate links."
                ),
            })

        code_entities = [
            {
                "code_name": r["code_name"],
                "code_id": r["code_id"],
                "code_type": (r["code_type"] or ["Unknown"])[0],
                "relationship": r["relationship"],
                "confidence": r["confidence"],
                "evidence": r["evidence"],
                "requirement_name": r["requirement_name"],
            }
            for r in records
        ]
        return json.dumps({
            "domain": domain,
            "requirement_id": requirement_id,
            "code_entities": code_entities,
            "total": len(code_entities),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def kg_get_coverage_gaps(domain: str) -> str:
    """Find requirement documents with NO code entities linked to them.

    Use this for sprint planning to identify which requirements still need
    implementation. Requirements with zero code links are coverage gaps.

    Args:
        domain: Domain slug (e.g. "cwow-facility")
    """
    try:
        cypher = """
        MATCH (d:Document)
        WHERE d._source = 'dva_kg'
          AND (d.domain = $domain OR d.metadata CONTAINS $domain)
        OPTIONAL MATCH (c)-[r {linked_by: 'dva-kg-link'}]->(d)
        WITH d, count(r) AS link_count
        WHERE link_count = 0
        RETURN d.id AS doc_id,
               d.name AS doc_name,
               d.content AS doc_content
        ORDER BY d.name
        """
        records = _neo4j_query(cypher, {"domain": domain})

        gaps = [
            {
                "doc_id": r["doc_id"],
                "doc_name": r["doc_name"],
                "summary": (r["doc_content"] or "")[:200],
            }
            for r in records
        ]
        return json.dumps({
            "domain": domain,
            "coverage_gaps": gaps,
            "total_unlinked": len(gaps),
            "message": (
                f"{len(gaps)} requirement(s) have no code linked in domain '{domain}'."
                if gaps else
                f"All requirements in domain '{domain}' have at least one code link."
            ),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def kg_get_domain_graph_summary(domain: str) -> str:
    """Get a high-level knowledge graph summary for a domain.

    Shows node counts, edge counts, coverage percentage, and top linked requirements.
    Use this to understand the current state of the KG for a domain.

    Args:
        domain: Domain slug (e.g. "cwow-facility")
    """
    try:
        code_q = """
        MATCH (n)
        WHERE n._source = 'dva_kg' AND n.persona = 'developer'
          AND (n.domain = $domain OR n.metadata CONTAINS $domain)
        RETURN count(n) AS count
        """
        doc_q = """
        MATCH (n:Document)
        WHERE n._source = 'dva_kg'
          AND (n.domain = $domain OR n.metadata CONTAINS $domain)
        RETURN count(n) AS count
        """
        edge_q = """
        MATCH (c)-[r]->(d:Document)
        WHERE c._source = 'dva_kg' AND r.linked_by = 'dva-kg-link'
          AND (c.domain = $domain OR c.metadata CONTAINS $domain)
        RETURN count(r) AS count
        """
        covered_q = """
        MATCH (d:Document)
        WHERE d._source = 'dva_kg'
          AND (d.domain = $domain OR d.metadata CONTAINS $domain)
        OPTIONAL MATCH (c)-[r {linked_by: 'dva-kg-link'}]->(d)
        WITH d, count(r) AS links
        RETURN
          count(d) AS total_docs,
          sum(CASE WHEN links > 0 THEN 1 ELSE 0 END) AS covered_docs
        """
        top_req_q = """
        MATCH (c)-[r {linked_by: 'dva-kg-link'}]->(d:Document)
        WHERE c._source = 'dva_kg'
          AND (c.domain = $domain OR c.metadata CONTAINS $domain)
        RETURN d.name AS requirement, count(r) AS link_count
        ORDER BY link_count DESC
        LIMIT 5
        """

        params = {"domain": domain}
        code_count = (_neo4j_query(code_q, params) or [{}])[0].get("count", 0)
        doc_count = (_neo4j_query(doc_q, params) or [{}])[0].get("count", 0)
        edge_count = (_neo4j_query(edge_q, params) or [{}])[0].get("count", 0)
        cov = (_neo4j_query(covered_q, params) or [{}])[0]
        total_docs = cov.get("total_docs", 0) or 0
        covered_docs = cov.get("covered_docs", 0) or 0
        coverage_pct = round((covered_docs / total_docs * 100) if total_docs > 0 else 0, 1)
        top_reqs = _neo4j_query(top_req_q, params)

        return json.dumps({
            "domain": domain,
            "code_nodes": code_count,
            "document_nodes": doc_count,
            "link_edges": edge_count,
            "coverage_pct": coverage_pct,
            "covered_requirements": covered_docs,
            "total_requirements": total_docs,
            "top_linked_requirements": [
                {"requirement": r["requirement"], "linked_code_count": r["link_count"]}
                for r in top_reqs
            ],
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════════════════


@mcp.resource("agentic://config")
def get_config() -> str:
    """Current Agentic MCP server configuration."""
    config = _get_config()
    return json.dumps({
        "tracker_db": str(config.tracker_db),
        "skills_registry": str(config.skills_registry),
        "skills_dir": str(config.skills_dir),
        "db_exists": config.tracker_db.exists(),
    })


@mcp.resource("agentic://summary")
def get_summary() -> str:
    """Platform usage summary: counts of repos, products, domains, etc."""
    try:
        return json.dumps(_get_db().activity_summary())
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    """Run the Agentic Platform MCP server."""
    logger.info("Starting Agentic Platform MCP server (transport=%s)", _transport)
    mcp.run(transport=_transport)


if __name__ == "__main__":
    main()
