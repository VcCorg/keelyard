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
                "neo4j package not installed. Install with: uv pip install 'agentic-cli[kg]'"
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
        """Create or merge a node in the graph (idempotent)."""
        # Sanitize the label to ensure it's valid for Neo4j
        sanitized_label = sanitize_label(label)
        
        # For Tool nodes, MERGE on name instead of id due to existing unique constraint
        if sanitized_label == "Tool" and "name" in properties:
            query = f"""
            MERGE (n:{sanitized_label} {{name: $name}})
            SET n += $properties
            RETURN n
            """
            params = {"name": properties.get("name"), "properties": properties}
        else:
            # Use MERGE on id to avoid duplicates
            query = f"""
            MERGE (n:{sanitized_label} {{id: $id}})
            SET n += $properties
            RETURN n
            """
            params = {"id": properties.get("id"), "properties": properties}
        
        with self._driver.session() as session:
            result = session.run(query, **params)
            record = result.single()
            return dict(record["n"]) if record else {}
    
    def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create or merge a relationship between two nodes (idempotent)."""
        props = properties or {}
        
        # Sanitize the relationship type (same rules as labels)
        sanitized_type = sanitize_label(relationship_type)
        
        # Use MERGE to avoid duplicate relationships
        query = """
        MATCH (a {id: $from_id}), (b {id: $to_id})
        MERGE (a)-[r:%s]->(b)
        SET r += $properties
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
    
    def create_release_node(
        self,
        page_id: str,
        title: str,
        source_url: str,
        domain: str,
        product: str,
        space_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Release node directly from domain_docs tracking.
        
        Args:
            page_id: Confluence page ID
            title: Release page title
            source_url: Confluence page URL
            domain: Domain name
            product: Product name
            space_key: Confluence space key
        
        Returns:
            Created node dictionary
        """
        import uuid
        node_id = str(uuid.uuid4())
        
        properties = {
            "id": node_id,
            "name": title,
            "page_id": page_id,
            "source": source_url,
            "document_title": title,
            "domain": domain,
            "product": product,
            "_source": "dva_kg",
        }
        
        if space_key:
            properties["space"] = space_key
        
        return self.create_node("Release", properties)
    
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
    
    def get_stats(self, domain: str | None = None) -> Dict[str, Any]:
        """Get graph statistics.
        
        Args:
            domain: Optional domain slug to filter statistics
        """
        # Build WHERE clause for domain filtering
        if domain:
            # When filtering by domain, don't filter by _source to include all domain-tagged nodes
            where_clause = f"WHERE n.domain = '{domain}'"
            where_clause_rel = f"WHERE a.domain = '{domain}' OR b.domain = '{domain}'"
        else:
            where_clause = "WHERE n._source = 'dva_kg'"
            where_clause_rel = "WHERE a._source = 'dva_kg'"
        
        queries = {
            "nodes": f"MATCH (n) {where_clause} RETURN count(n) as count",
            "relationships": f"MATCH (a)-[r]->(b) {where_clause_rel} RETURN count(r) as count",
            "node_types": f"MATCH (n) {where_clause} RETURN DISTINCT labels(n) as labels",
            "relationship_types": f"MATCH (a)-[r]->(b) {where_clause_rel} RETURN DISTINCT type(r) as type",
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
            if domain:
                top_entities_query = f"""
                MATCH (n) {where_clause}
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) as connections
                ORDER BY connections DESC
                LIMIT 10
                RETURN n.name as name, n.id as id, connections
                """
            else:
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

    def check_release_requirement_links(self) -> Dict[str, Any]:
        """Check if Release nodes are linked to Document (requirement) nodes."""
        queries = {
            "release_nodes": """
            MATCH (r) WHERE r.name CONTAINS 'Release' OR r.name CONTAINS 'release'
            RETURN count(r) as count
            """,
            "document_nodes": """
            MATCH (d:Document) WHERE d._source = 'dva_kg'
            RETURN count(d) as count
            """,
            "release_document_links": """
            MATCH (r)-[rel]->(d:Document) 
            WHERE r.name CONTAINS 'Release' OR r.name CONTAINS 'release'
            RETURN count(rel) as count
            """,
            "release_nodes_sample": """
            MATCH (r) WHERE r.name CONTAINS 'Release' OR r.name CONTAINS 'release'
            RETURN r.name as name, r.id as id, labels(r) as labels, r.metadata as metadata
            LIMIT 10
            """,
            "document_nodes_sample": """
            MATCH (d:Document) WHERE d._source = 'dva_kg'
            RETURN d.name as name, d.id as id, d.domain as domain, d.metadata as metadata
            LIMIT 10
            """,
            "release_relationships": """
            MATCH (r)-[rel]->(d:Document)
            WHERE r.name CONTAINS 'Release' OR r.name CONTAINS 'release'
            RETURN r.name as release_name, d.name as doc_name, type(rel) as rel_type
            LIMIT 20
            """
        }
        
        results = {}
        
        with self._driver.session() as session:
            # Count release nodes
            result = session.run(queries["release_nodes"])
            results["release_nodes_count"] = result.single()["count"]
            
            # Count document nodes
            result = session.run(queries["document_nodes"])
            results["document_nodes_count"] = result.single()["count"]
            
            # Count release-document links
            result = session.run(queries["release_document_links"])
            results["release_document_links_count"] = result.single()["count"]
            
            # Sample release nodes
            result = session.run(queries["release_nodes_sample"])
            results["release_nodes_sample"] = [
                {"name": record["name"], "id": record["id"], "labels": record["labels"], "metadata": record.get("metadata")}
                for record in result
            ]
            
            # Sample document nodes
            result = session.run(queries["document_nodes_sample"])
            results["document_nodes_sample"] = [
                {"name": record["name"], "id": record["id"], "domain": record["domain"], "metadata": record.get("metadata")}
                for record in result
            ]
            
            # Sample release relationships
            result = session.run(queries["release_relationships"])
            results["release_relationships_sample"] = [
                {"release_name": record["release_name"], "doc_name": record["doc_name"], "rel_type": record["rel_type"]}
                for record in result
            ]
        
        return results

    def get_requirements_by_release(self, release_name: str) -> Dict[str, Any]:
        """Get all requirements (FREQ IDs) associated with a specific release."""
        import re
        
        queries = {
            "release_node": """
            MATCH (r) WHERE r.name CONTAINS $release_name
            RETURN r.name as name, r.id as id, labels(r) as labels
            LIMIT 1
            """,
            "release_documents": """
            MATCH (r {name: $release_name})-[rel:HAS_DOCUMENT]->(d:Document)
            RETURN d.name as name, d.id as id, d.source as source, d.content as content
            """,
            "release_documents_fallback_is_based_on": """
            MATCH (r {name: $release_name})-[rel:IS_BASED_ON]->(d)
            RETURN d.name as name, d.id as id, d.source as source, d.content as content
            """,
            "release_documents_fallback_specifies": """
            MATCH (d)-[rel:SPECIFIES_RELEASE]->(r {name: $release_name})
            RETURN d.name as name, d.id as id, d.source as source, d.content as content
            """,
            "release_documents_fallback_belongs": """
            MATCH (d)-[rel:BELONGS_TO]->(r {name: $release_name})
            RETURN d.name as name, d.id as id, d.source as source, d.content as content
            """,
            "freq_ids_from_docs": """
            MATCH (r {name: $release_name})-[rel:HAS_DOCUMENT]->(d:Document)
            RETURN d.name as doc_name, d.content as content
            """,
            "freq_ids_from_docs_fallback_is_based_on": """
            MATCH (r {name: $release_name})-[rel:IS_BASED_ON]->(d)
            RETURN d.name as doc_name, d.content as content
            """,
            "freq_ids_from_docs_fallback_specifies": """
            MATCH (d)-[rel:SPECIFIES_RELEASE]->(r {name: $release_name})
            RETURN d.name as doc_name, d.content as content
            """,
            "freq_ids_from_docs_fallback_belongs": """
            MATCH (d)-[rel:BELONGS_TO]->(r {name: $release_name})
            RETURN d.name as doc_name, d.content as content
            """
        }
        
        results = {}
        
        with self._driver.session() as session:
            # Find release node
            result = session.run(queries["release_node"], release_name=release_name)
            release_record = result.single()
            if release_record:
                results["release"] = {
                    "name": release_record["name"],
                    "id": release_record["id"],
                    "labels": release_record["labels"]
                }
            else:
                return {"error": f"Release node not found: {release_name}"}
            
            # Get documents for this release using HAS_DOCUMENT
            result = session.run(queries["release_documents"], release_name=release_name)
            documents = []
            for record in result:
                documents.append({
                    "name": record["name"],
                    "id": record["id"],
                    "source": record["source"],
                    "content": record["content"][:500] + "..." if len(record["content"]) > 500 else record["content"]
                })
            
            # Fallback to IS_BASED_ON if no HAS_DOCUMENT relationships
            if not documents:
                result = session.run(queries["release_documents_fallback_is_based_on"], release_name=release_name)
                for record in result:
                    documents.append({
                        "name": record["name"],
                        "id": record["id"],
                        "source": record["source"],
                        "content": record["content"][:500] + "..." if len(record["content"]) > 500 else record["content"]
                    })
            
            # Fallback to SPECIFIES_RELEASE if still no documents
            if not documents:
                result = session.run(queries["release_documents_fallback_specifies"], release_name=release_name)
                for record in result:
                    documents.append({
                        "name": record["name"],
                        "id": record["id"],
                        "source": record["source"],
                        "content": record["content"][:500] + "..." if len(record["content"]) > 500 else record["content"]
                    })
            
            # Fallback to BELONGS_TO if still no documents
            if not documents:
                result = session.run(queries["release_documents_fallback_belongs"], release_name=release_name)
                for record in result:
                    documents.append({
                        "name": record["name"],
                        "id": record["id"],
                        "source": record["source"],
                        "content": record["content"][:500] + "..." if len(record["content"]) > 500 else record["content"]
                    })
            
            results["documents"] = documents
            
            # Extract FREQ IDs from document content using HAS_DOCUMENT
            result = session.run(queries["freq_ids_from_docs"], release_name=release_name)
            freq_ids = []
            for record in result:
                content = record["content"]
                # Extract FREQ IDs (CWOW-XXXXXX pattern)
                freq_pattern = r'(CWOW-\d+)'
                matches = re.findall(freq_pattern, content)
                for freq_id in matches:
                    if freq_id not in freq_ids:
                        freq_ids.append(freq_id)
            
            # Fallback to IS_BASED_ON if no FREQ IDs found
            if not freq_ids:
                result = session.run(queries["freq_ids_from_docs_fallback_is_based_on"], release_name=release_name)
                for record in result:
                    content = record["content"]
                    # Extract FREQ IDs (CWOW-XXXXXX pattern)
                    freq_pattern = r'(CWOW-\d+)'
                    matches = re.findall(freq_pattern, content)
                    for freq_id in matches:
                        if freq_id not in freq_ids:
                            freq_ids.append(freq_id)
            
            # Fallback to SPECIFIES_RELEASE if still no FREQ IDs
            if not freq_ids:
                result = session.run(queries["freq_ids_from_docs_fallback_specifies"], release_name=release_name)
                for record in result:
                    content = record["content"]
                    # Extract FREQ IDs (CWOW-XXXXXX pattern)
                    freq_pattern = r'(CWOW-\d+)'
                    matches = re.findall(freq_pattern, content)
                    for freq_id in matches:
                        if freq_id not in freq_ids:
                            freq_ids.append(freq_id)
            
            # Fallback to BELONGS_TO if still no FREQ IDs
            if not freq_ids:
                result = session.run(queries["freq_ids_from_docs_fallback_belongs"], release_name=release_name)
                for record in result:
                    content = record["content"]
                    # Extract FREQ IDs (CWOW-XXXXXX pattern)
                    freq_pattern = r'(CWOW-\d+)'
                    matches = re.findall(freq_pattern, content)
                    for freq_id in matches:
                        if freq_id not in freq_ids:
                            freq_ids.append(freq_id)
            
            results["freq_ids"] = sorted(freq_ids)
            results["freq_count"] = len(freq_ids)
        
        return results
