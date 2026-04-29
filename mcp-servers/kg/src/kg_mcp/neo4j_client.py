"""Neo4j client for KG MCP Server.

Direct Neo4j driver client that scopes all queries to _source='dva_kg' nodes,
ensuring no interference with neo4j-agent-memory data.
"""

import logging
from typing import Any

from neo4j import GraphDatabase

from .config import KGConfig

logger = logging.getLogger(__name__)


class Neo4jKGClient:
    """Client for querying dva_kg-scoped data in Neo4j."""

    def __init__(self, config: KGConfig):
        self._config = config
        self._driver = None

    def connect(self):
        """Establish Neo4j connection."""
        self._driver = GraphDatabase.driver(
            self._config.neo4j_uri,
            auth=(self._config.neo4j_user, self._config.neo4j_password),
        )
        self._driver.verify_connectivity()
        logger.info(f"Connected to Neo4j at {self._config.neo4j_uri}")

    def close(self):
        """Close the connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()

    def _run(self, query: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results as dicts."""
        with self._driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    # ── Search / Query ──────────────────────────────────────────────────

    def search_text(
        self, text: str, *, persona: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search nodes by text content, scoped to dva_kg source."""
        where_parts = [
            "n._source = 'dva_kg'",
            "(n.name CONTAINS $text OR n.content CONTAINS $text)",
        ]
        if persona:
            where_parts.append("n.persona = $persona")

        query = f"""
        MATCH (n)
        WHERE {' AND '.join(where_parts)}
        RETURN n.name AS name, n.id AS id, labels(n) AS labels,
               n.content AS content, n.persona AS persona
        LIMIT $limit
        """
        return self._run(query, {"text": text, "persona": persona, "limit": limit})

    def query_cypher(self, cypher: str) -> list[dict[str, Any]]:
        """Execute a raw Cypher query (for power users)."""
        return self._run(cypher)

    def get_entity_details(
        self, entity_name: str
    ) -> dict[str, Any]:
        """Get a specific entity and its relationships."""
        node_query = """
        MATCH (n)
        WHERE n._source = 'dva_kg' AND n.name = $name
        RETURN n.name AS name, n.id AS id, labels(n) AS labels,
               n.content AS content, n.persona AS persona
        LIMIT 1
        """
        nodes = self._run(node_query, {"name": entity_name})
        if not nodes:
            return {"error": f"Entity '{entity_name}' not found"}

        entity = nodes[0]

        rel_query = """
        MATCH (n)-[r]-(m)
        WHERE n._source = 'dva_kg' AND n.name = $name
        RETURN type(r) AS relationship, m.name AS related_entity,
               labels(m) AS related_labels, r.type AS rel_detail
        LIMIT 50
        """
        relationships = self._run(rel_query, {"name": entity_name})
        entity["relationships"] = relationships
        return entity

    # ── Stats ───────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get KG statistics scoped to dva_kg source."""
        queries = {
            "nodes": "MATCH (n) WHERE n._source = 'dva_kg' RETURN count(n) AS count",
            "relationships": "MATCH (a)-[r]->(b) WHERE a._source = 'dva_kg' RETURN count(r) AS count",
            "node_types": "MATCH (n) WHERE n._source = 'dva_kg' RETURN DISTINCT labels(n) AS labels",
            "relationship_types": "MATCH (a)-[r]->(b) WHERE a._source = 'dva_kg' RETURN DISTINCT type(r) AS type",
        }

        stats = {}
        for key, q in queries.items():
            result = self._run(q)
            if key in ("nodes", "relationships"):
                stats[key] = result[0]["count"] if result else 0
            elif key == "node_types":
                stats[key] = [r["labels"] for r in result]
            elif key == "relationship_types":
                stats[key] = [r["type"] for r in result]

        # Top entities
        top_q = """
        MATCH (n) WHERE n._source = 'dva_kg'
        OPTIONAL MATCH (n)-[r]-()
        WITH n, count(r) AS connections
        ORDER BY connections DESC
        LIMIT 10
        RETURN n.name AS name, labels(n) AS labels, connections
        """
        stats["top_entities"] = self._run(top_q)
        return stats
