"""Neo4j client for knowledge graph operations."""

import re
from typing import Any, Dict, List, Optional

from agentic_cli.kg.config import KGConfig
from agentic_cli.config import CLI_NAME


def sanitize_label(label: str) -> str:
    """
    Sanitize a label for use in Neo4j.
    
    Neo4j labels cannot contain spaces or special characters.
    This function converts spaces to underscores and removes invalid characters.
    """
    # Replace spaces with underscores
    sanitized = label.replace(" ", "_")
    # Remove any characters that aren't alphanumeric or underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    return sanitized or "KGEntity"


class Neo4jClient:
    """Client for Neo4j graph database operations."""
    
    def __init__(self, config: Optional[KGConfig] = None):
        """Initialize Neo4j client."""
        self.config = config or KGConfig.load()
        self._driver = None
        
        if not self.config.is_neo4j_configured():
            raise ValueError(
                "Neo4j is not properly configured. fRun '{CLI_NAME} kg init' first."
            )
    
    def connect(self):
        """Establish connection to Neo4j."""
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError(
                "neo4j package not installed. Install with: uv pip install 'dva-agentic-cli[kg]'"
            )
        
        self._driver = GraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_username, self.config.neo4j_password),
        )
        
        # Test connection
        with self._driver.session() as session:
            session.run("RETURN 1")
    
    def close(self):
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a node in the graph."""
        # Sanitize the label to ensure it's valid for Neo4j
        sanitized_label = sanitize_label(label)
        
        query = f"""
        CREATE (n:{sanitized_label} $properties)
        RETURN n
        """
        
        with self._driver.session() as session:
            result = session.run(query, properties=properties)
            record = result.single()
            return dict(record["n"]) if record else {}
    
    def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a relationship between two nodes."""
        props = properties or {}
        
        # Sanitize the relationship type (same rules as labels)
        sanitized_type = sanitize_label(relationship_type)
        
        query = """
        MATCH (a), (b)
        WHERE a.id = $from_id AND b.id = $to_id
        CREATE (a)-[r:%s $properties]->(b)
        RETURN r
        """ % sanitized_type
        
        with self._driver.session() as session:
            result = session.run(
                query,
                from_id=from_node_id,
                to_id=to_node_id,
                properties=props,
            )
            record = result.single()
            return dict(record["r"]) if record else {}
    
    def execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query."""
        params = parameters or {}
        
        with self._driver.session() as session:
            result = session.run(query, **params)
            return [dict(record) for record in result]
    
    def find_nodes(
        self,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Find nodes matching criteria."""
        where_clauses = []
        params = {"limit": limit}
        
        if properties:
            for key, value in properties.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"
        label_clause = f":{label}" if label else ""
        
        query = f"""
        MATCH (n{label_clause})
        WHERE {where_clause}
        RETURN n
        LIMIT $limit
        """
        
        with self._driver.session() as session:
            result = session.run(query, **params)
            return [dict(record["n"]) for record in result]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        queries = {
            "nodes": "MATCH (n) WHERE n._source = 'dva_kg' RETURN count(n) as count",
            "relationships": "MATCH (a)-[r]->(b) WHERE a._source = 'dva_kg' RETURN count(r) as count",
            "node_types": "MATCH (n) WHERE n._source = 'dva_kg' RETURN DISTINCT labels(n) as labels",
            "relationship_types": "MATCH (a)-[r]->(b) WHERE a._source = 'dva_kg' RETURN DISTINCT type(r) as type",
        }
        
        stats = {}
        
        with self._driver.session() as session:
            # Count nodes
            result = session.run(queries["nodes"])
            stats["nodes"] = result.single()["count"]
            
            # Count relationships
            result = session.run(queries["relationships"])
            stats["relationships"] = result.single()["count"]
            
            # Get node types
            result = session.run(queries["node_types"])
            node_types = set()
            for record in result:
                node_types.update(record["labels"])
            stats["node_types"] = len(node_types)
            
            # Get relationship types
            result = session.run(queries["relationship_types"])
            stats["relationship_types"] = len([record["type"] for record in result])
            
            # Get top entities by connection count
            top_entities_query = """
            MATCH (n) WHERE n._source = 'dva_kg'
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as connections
            ORDER BY connections DESC
            LIMIT 10
            RETURN n.name as name, n.id as id, connections
            """
            result = session.run(top_entities_query)
            stats["top_entities"] = [
                {"name": record["name"], "id": record["id"], "connections": record["connections"]}
                for record in result
            ]
        
        return stats
    
    def search_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search nodes by embedding similarity."""
        # This requires a vector index in Neo4j
        query = """
        CALL db.index.vector.queryNodes('entity_embeddings', $limit, $embedding)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        """
        
        with self._driver.session() as session:
            result = session.run(query, embedding=embedding, limit=limit)
            return [
                {
                    "node": dict(record["node"]),
                    "score": record["score"],
                }
                for record in result
            ]
    
    def create_vector_index(self, dimension: int = 768):
        """Create a vector index for embeddings."""
        query = """
        CREATE VECTOR INDEX kg_entity_embeddings IF NOT EXISTS
        FOR (n:KGEntity)
        ON n.embedding
        OPTIONS {indexConfig: {
            `vector.dimensions`: $dimension,
            `vector.similarity_function`: 'cosine'
        }}
        """
        
        with self._driver.session() as session:
            session.run(query, dimension=dimension)
