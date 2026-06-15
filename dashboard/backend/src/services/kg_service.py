"""KG Context service — reads product/domain knowledge graph data from Neo4j and tracker DB."""

from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel


# ── Pydantic models ────────────────────────────────────────────────────────────

class DomainKGStats(BaseModel):
    domain: str
    product: str
    code_entities: int = 0
    requirement_docs: int = 0
    linked_edges: int = 0
    unlinked_docs: int = 0
    coverage_pct: float = 0.0
    relationship_breakdown: dict[str, int] = {}
    has_data: bool = False


class ProductKGSummary(BaseModel):
    product: str
    total_domains: int = 0
    total_code_entities: int = 0
    total_requirement_docs: int = 0
    total_linked_edges: int = 0
    overall_coverage_pct: float = 0.0
    domains: list[DomainKGStats] = []


class KGLinkRow(BaseModel):
    code_id: str
    code_name: str
    code_type: str
    doc_id: str
    doc_name: str
    relationship: str
    confidence: float
    evidence: str
    domain: str


class KGGapRow(BaseModel):
    doc_id: str
    doc_name: str
    domain: str
    jira_id: Optional[str] = None
    content_preview: str = ""


class KGGraphNode(BaseModel):
    id: str
    label: str
    node_type: str  # "code" | "document"
    domain: Optional[str] = None


class KGGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    confidence: float


class KGNeighborhood(BaseModel):
    nodes: list[KGGraphNode]
    edges: list[KGGraphEdge]
    center_id: str


# ── Neo4j helpers ──────────────────────────────────────────────────────────────

def _get_neo4j_client():
    """Get a connected Neo4j client, or None if unavailable."""
    try:
        from agentic_cli.kg.neo4j_client import Neo4jClient
        from agentic_cli.kg.config import KGConfig
        config = KGConfig.load()
        print(f"DEBUG: KGConfig provider={config.provider}, is_neo4j_configured={config.is_neo4j_configured()}")
        if not config.is_neo4j_configured():
            print("DEBUG: Neo4j not configured")
            return None
        client = Neo4jClient(config=config)
        client.connect()
        print("DEBUG: Neo4j client connected successfully")
        return client
    except Exception as e:
        print(f"DEBUG: Error getting Neo4j client: {e}")
        import traceback
        traceback.print_exc()
        return None


def _get_tracker_db():
    """Get tracker DB instance, or None if unavailable."""
    try:
        from agentic_mcp.db import TrackerDB
        from agentic_mcp.config import AgenticConfig
        config = AgenticConfig()
        db = TrackerDB(db_path=config.tracker_db)
        print(f"DEBUG: TrackerDB initialized successfully with path: {config.tracker_db}")
        return db
    except ImportError as e:
        print(f"Failed to import agentic_mcp: {e}")
        return None
    except Exception as e:
        print(f"Error getting tracker DB: {e}")
        import traceback
        traceback.print_exc()
        return None


# ── Service functions ──────────────────────────────────────────────────────────

def get_all_products_kg_summary() -> list[ProductKGSummary]:
    """Return KG coverage stats for all products and their domains."""
    db = _get_tracker_db()
    client = _get_neo4j_client()
    
    print(f"DEBUG: db={db}, client={client}")

    products_map: dict[str, ProductKGSummary] = {}

    # Pull domain list from tracker
    domains: list[dict[str, Any]] = []
    if db:
        try:
            domains = db.domain_list() or []
            print(f"DEBUG: Got {len(domains)} domains from tracker DB")
        except Exception as e:
            print(f"DEBUG: Error getting domains from tracker: {e}")
            domains = []

    if not domains:
        # Fallback: discover domains from Neo4j directly
        if client:
            try:
                rows = client.execute_cypher(
                    "MATCH (n) WHERE n._source = 'dva_kg' AND n.domain IS NOT NULL "
                    "RETURN DISTINCT n.domain AS domain LIMIT 100"
                )
                print(f"DEBUG: Got {len(rows)} domains from Neo4j")
                for r in rows:
                    domains.append({"slug": r["domain"], "product": "unknown", "name": r["domain"]})
            except Exception as e:
                print(f"DEBUG: Error getting domains from Neo4j: {e}")
                pass

    for d in domains:
        slug = d.get("slug") or d.get("name") or ""
        product = d.get("product") or "Unknown"

        stats = _get_domain_stats(slug, client)
        stats.product = product

        if product not in products_map:
            products_map[product] = ProductKGSummary(product=product)
        products_map[product].domains.append(stats)
        products_map[product].total_domains += 1
        products_map[product].total_code_entities += stats.code_entities
        products_map[product].total_requirement_docs += stats.requirement_docs
        products_map[product].total_linked_edges += stats.linked_edges

    # Compute overall coverage per product
    for p in products_map.values():
        if p.total_requirement_docs > 0:
            linked_docs = sum(1 for d in p.domains if d.linked_edges > 0)
            p.overall_coverage_pct = round(linked_docs / max(p.total_requirement_docs, 1) * 100, 1)

    if client:
        client.close()

    return list(products_map.values())


def _get_domain_stats(domain: str, client) -> DomainKGStats:
    """Query Neo4j for stats for a single domain."""
    stats = DomainKGStats(domain=domain, product="")
    if not client or not domain:
        return stats

    try:
        # Use global stats like CLI - count all nodes regardless of persona/labels
        rows = client.execute_cypher("""
            MATCH (n)
            WHERE n._source = 'dva_kg'
            RETURN count(n) as total_count
        """)
        if rows:
            total_count = rows[0].get("total_count") or 0
            # For now, assign all nodes to code_entities since we can't distinguish
            stats.code_entities = total_count
            stats.requirement_docs = 0  # Will be refined if we can identify docs

        edge_rows = client.execute_cypher("""
            MATCH (a)-[r]->(b)
            WHERE a._source = 'dva_kg'
            RETURN count(r) as total_edges
        """)
        if edge_rows:
            stats.linked_edges = edge_rows[0].get("total_edges") or 0

        # Try to get document count specifically
        doc_rows = client.execute_cypher("""
            MATCH (n:Document)
            WHERE n._source = 'dva_kg'
            RETURN count(n) as doc_count
        """)
        if doc_rows:
            doc_count = doc_rows[0].get("doc_count") or 0
            stats.requirement_docs = doc_count
            # Adjust code entities to exclude docs
            stats.code_entities = max(0, total_count - doc_count)

        # Mark as having data if we found anything
        stats.has_data = (stats.code_entities > 0 or stats.requirement_docs > 0)
    except Exception:
        pass

    return stats


def get_domain_links(domain: str, limit: int = 200) -> list[KGLinkRow]:
    """Return code→doc link edges for a domain."""
    client = _get_neo4j_client()
    if not client:
        return []
    try:
        rows = client.execute_cypher("""
            MATCH (c)-[r]->(d:Document)
            WHERE c._source = 'dva_kg' AND c.domain = $domain
              AND type(r) IN ['IMPLEMENTS','REFERENCES','TESTED_BY','CONFIGURES']
            RETURN
                c.id AS code_id,
                c.name AS code_name,
                labels(c) AS code_labels,
                d.id AS doc_id,
                d.name AS doc_name,
                type(r) AS rel_type,
                r.confidence AS confidence,
                r.evidence AS evidence
            ORDER BY r.confidence DESC
            LIMIT $limit
        """, {"domain": domain, "limit": limit})
        result = []
        for r in rows:
            code_labels = r.get("code_labels") or []
            code_type = next((lb for lb in code_labels if lb != "Code"), "Entity")
            result.append(KGLinkRow(
                code_id=r.get("code_id") or "",
                code_name=r.get("code_name") or "",
                code_type=code_type,
                doc_id=r.get("doc_id") or "",
                doc_name=r.get("doc_name") or "",
                relationship=r.get("rel_type") or "",
                confidence=float(r.get("confidence") or 0.0),
                evidence=r.get("evidence") or "",
                domain=domain,
            ))
        return result
    except Exception:
        return []
    finally:
        client.close()


def get_domain_gaps(domain: str) -> list[KGGapRow]:
    """Return requirement docs that have no linked code entities."""
    client = _get_neo4j_client()
    if not client:
        return []
    try:
        rows = client.execute_cypher("""
            MATCH (d:Document)
            WHERE d._source = 'dva_kg' AND d.domain = $domain
              AND NOT (d)<-[:IMPLEMENTS|REFERENCES|TESTED_BY|CONFIGURES]-()
            RETURN d.id AS id, d.name AS name, d.content AS content,
                   d.jira_id AS jira_id
            ORDER BY d.name
        """, {"domain": domain})
        result = []
        for r in rows:
            content = r.get("content") or ""
            result.append(KGGapRow(
                doc_id=r.get("id") or "",
                doc_name=r.get("name") or "",
                domain=domain,
                jira_id=r.get("jira_id"),
                content_preview=content[:160],
            ))
        return result
    except Exception:
        return []
    finally:
        client.close()


def get_node_neighborhood(node_id: str, domain: str) -> KGNeighborhood:
    """Return 1-hop graph neighborhood for a given node id."""
    client = _get_neo4j_client()
    nodes: dict[str, KGGraphNode] = {}
    edges: list[KGGraphEdge] = []

    if not client:
        return KGNeighborhood(nodes=[], edges=[], center_id=node_id)

    try:
        rows = client.execute_cypher("""
            MATCH (center {id: $node_id})
            OPTIONAL MATCH (center)-[r]->(neighbor)
            OPTIONAL MATCH (incoming)-[r2]->(center)
            RETURN
                center.id AS c_id, center.name AS c_name, labels(center) AS c_labels,
                neighbor.id AS n_id, neighbor.name AS n_name, labels(neighbor) AS n_labels,
                type(r) AS rel_out, r.confidence AS conf_out,
                incoming.id AS in_id, incoming.name AS in_name, labels(incoming) AS in_labels,
                type(r2) AS rel_in, r2.confidence AS conf_in
        """, {"node_id": node_id})

        for r in rows:
            # Center node
            c_id = r.get("c_id") or node_id
            if c_id not in nodes:
                c_labels = r.get("c_labels") or []
                nodes[c_id] = KGGraphNode(
                    id=c_id,
                    label=r.get("c_name") or c_id,
                    node_type="document" if "Document" in c_labels else "code",
                    domain=domain,
                )

            # Outgoing neighbor
            if r.get("n_id"):
                n_id = r["n_id"]
                if n_id not in nodes:
                    n_labels = r.get("n_labels") or []
                    nodes[n_id] = KGGraphNode(
                        id=n_id,
                        label=r.get("n_name") or n_id,
                        node_type="document" if "Document" in n_labels else "code",
                        domain=domain,
                    )
                edges.append(KGGraphEdge(
                    source=c_id, target=n_id,
                    relationship=r.get("rel_out") or "RELATES_TO",
                    confidence=float(r.get("conf_out") or 0.0),
                ))

            # Incoming neighbor
            if r.get("in_id"):
                in_id = r["in_id"]
                if in_id not in nodes:
                    in_labels = r.get("in_labels") or []
                    nodes[in_id] = KGGraphNode(
                        id=in_id,
                        label=r.get("in_name") or in_id,
                        node_type="document" if "Document" in in_labels else "code",
                        domain=domain,
                    )
                edges.append(KGGraphEdge(
                    source=in_id, target=c_id,
                    relationship=r.get("rel_in") or "RELATES_TO",
                    confidence=float(r.get("conf_in") or 0.0),
                ))

    except Exception:
        pass
    finally:
        client.close()

    return KGNeighborhood(nodes=list(nodes.values()), edges=edges, center_id=node_id)
