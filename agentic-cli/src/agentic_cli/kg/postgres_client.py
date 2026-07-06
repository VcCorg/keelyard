"""PostgreSQL client for knowledge graph operations with pgvector and Apache AGE."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2.extras import execute_values
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 not installed. PostgreSQL support will be limited.")


class PostgresClient:
    """Client for PostgreSQL with pgvector and Apache AGE for KG operations."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "postgres",
        password: str = "postgres",
        database: str = "knowledge_graph",
        graph_name: str = "knowledge_graph"
    ):
        """
        Initialize PostgreSQL client.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: PostgreSQL username
            password: PostgreSQL password
            database: Database name
            graph_name: Apache AGE graph name
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            )
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.graph_name = graph_name
        self._conn = None
        logger.info(f"PostgreSQL client initialized: {host}:{port}/{database}")
    
    def connect(self):
        """Establish connection to PostgreSQL."""
        self._conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.database
        )
        self._conn.autocommit = True
        
        # Test connection
        with self._conn.cursor() as cur:
            cur.execute("SELECT 1")
        
        logger.info("Connected to PostgreSQL")
    
    def close(self):
        """Close PostgreSQL connection."""
        if self._conn:
            self._conn.close()
            logger.info("PostgreSQL connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _ensure_graph(self):
        """Ensure the Apache AGE graph exists."""
        with self._conn.cursor() as cur:
            # Set search path
            cur.execute("SET search_path = ag_catalog, '$user', public")
            
            # Check if graph exists
            cur.execute("SELECT graphname FROM ag_graph WHERE graphname = %s", (self.graph_name,))
            if not cur.fetchone():
                # Create graph
                cur.execute("SELECT create_graph(%s)", (self.graph_name,))
                logger.info(f"Created Apache AGE graph: {self.graph_name}")
    
    def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a node in the graph using Apache AGE.
        
        Args:
            label: Node label (e.g., "Function", "Class")
            properties: Node properties
            
        Returns:
            Created node properties
        """
        self._ensure_graph()
        
        # Build Cypher query
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"""
        SELECT * FROM cypher(%s, $$
            CREATE (n:{label} {{{props_str}}})
            RETURN n
        $$, %s) as (n agtype)
        """
        
        with self._conn.cursor() as cur:
            cur.execute(query, (self.graph_name, properties))
            result = cur.fetchone()
            if result:
                # Parse agtype to dict
                import json
                return json.loads(result[0])
            return {}
    
    def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a relationship between two nodes using Apache AGE.
        
        Args:
            from_node_id: ID of the source node
            to_node_id: ID of the target node
            relationship_type: Type of relationship (e.g., "CALLS", "USES")
            properties: Optional relationship properties
            
        Returns:
            Created relationship properties
        """
        self._ensure_graph()
        
        props = properties or {}
        props_str = ", ".join([f"{k}: ${k}" for k in props.keys()]) if props else ""
        
        query = f"""
        SELECT * FROM cypher(%s, $$
            MATCH (a), (b)
            WHERE a.id = $from_id AND b.id = $to_id
            CREATE (a)-[r:{relationship_type} {{{props_str}}}]->(b)
            RETURN r
        $$, %s) as (r agtype)
        """
        
        params = {**props, "from_id": from_node_id, "to_id": to_node_id}
        
        with self._conn.cursor() as cur:
            cur.execute(query, (self.graph_name, params))
            result = cur.fetchone()
            if result:
                import json
                return json.loads(result[0])
            return {}
    
    def execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query using Apache AGE.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query results
        """
        # Check if Apache AGE is available
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'age')")
                age_installed = cur.fetchone()[0]
        except:
            age_installed = False
        
        if not age_installed:
            # Apache AGE not installed, use table-based queries instead
            return self.execute_sql_query(query, parameters)
        
        self._ensure_graph()
        params = parameters or {}
        
        full_query = f"""
        SELECT * FROM cypher(%s, $query, %s) as (result agtype)
        """
        
        with self._conn.cursor() as cur:
            cur.execute(full_query, (self.graph_name, {"query": query, **params}))
            results = []
            for row in cur.fetchall():
                import json
                results.append(json.loads(row[0]))
            return results
    
    def execute_sql_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query on KG tables (fallback when Apache AGE is not available).
        
        Args:
            query: Query string (can be simple SQL or limited Cypher-like syntax)
            parameters: Query parameters
            
        Returns:
            Query results
        """
        params = parameters or {}
        
        # Convert simple Cypher to SQL for basic operations
        # This is a limited implementation for when AGE is not available
        if "MATCH" in query.upper() and "RETURN" in query.upper():
            # Simple pattern: MATCH (n) RETURN n -> SELECT * FROM code_entities
            sql_query = "SELECT name, content, entity_type, file_path, language FROM code_entities LIMIT 100"
        else:
            # Use as-is for SQL queries
            sql_query = query
        
        with self._conn.cursor() as cur:
            cur.execute(sql_query, params)
            results = []
            for row in cur.fetchall():
                results.append({
                    "name": row[0],
                    "content": row[1],
                    "entity_type": row[2],
                    "file_path": row[3],
                    "language": row[4],
                })
            return results
    
    def find_nodes(
        self,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Find nodes matching criteria.
        
        Args:
            label: Node label filter
            properties: Property filters
            limit: Maximum number of results
            
        Returns:
            Matching nodes
        """
        self._ensure_graph()
        
        where_clauses = []
        params = {"limit": limit}
        
        if properties:
            for key, value in properties.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"
        label_clause = f":{label}" if label else ""
        
        query = f"""
        SELECT * FROM cypher(%s, $$
            MATCH (n{label_clause})
            WHERE {where_clause}
            RETURN n
            LIMIT $limit
        $$, %s) as (n agtype)
        """
        
        with self._conn.cursor() as cur:
            cur.execute(query, (self.graph_name, params))
            results = []
            for row in cur.fetchall():
                import json
                results.append(json.loads(row[0]))
            return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics (for Apache AGE).
        
        Returns:
            Graph statistics including node counts, relationship counts, etc.
        """
        self._ensure_graph()
        
        stats = {}
        
        with self._conn.cursor() as cur:
            # Count nodes
            cur.execute(f"""
                SELECT * FROM cypher(%s, $$
                    MATCH (n) WHERE n._source = 'keel_kg'
                    RETURN count(n) as count
                $$) as (count agtype)
            """, (self.graph_name,))
            result = cur.fetchone()
            if result:
                import json
                stats["nodes"] = json.loads(result[0])["count"]
            
            # Count relationships
            cur.execute(f"""
                SELECT * FROM cypher(%s, $$
                    MATCH (a)-[r]->(b) WHERE a._source = 'keel_kg'
                    RETURN count(r) as count
                $$) as (count agtype)
            """, (self.graph_name,))
            result = cur.fetchone()
            if result:
                import json
                stats["relationships"] = json.loads(result[0])["count"]
            
            # Get node types
            cur.execute(f"""
                SELECT * FROM cypher(%s, $$
                    MATCH (n) WHERE n._source = 'keel_kg'
                    RETURN DISTINCT labels(n) as labels
                $$) as (labels agtype)
            """, (self.graph_name,))
            node_types = set()
            for row in cur.fetchall():
                import json
                labels = json.loads(row[0])["labels"]
                node_types.update(labels)
            stats["node_types"] = len(node_types)
            
            # Get relationship types
            cur.execute(f"""
                SELECT * FROM cypher(%s, $$
                    MATCH (a)-[r]->(b) WHERE a._source = 'keel_kg'
                    RETURN DISTINCT type(r) as type
                $$) as (type agtype)
            """, (self.graph_name,))
            stats["relationship_types"] = len([row for row in cur.fetchall()])
        
        return stats
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get PostgreSQL KG statistics (for table-based storage).
        
        Returns:
            Statistics including entity counts and relationship counts.
        """
        stats = {}
        
        with self._conn.cursor() as cur:
            # Count code entities
            cur.execute("SELECT COUNT(*) FROM code_entities WHERE _source = 'keel_kg'")
            result = cur.fetchone()
            stats["code_entities"] = result[0] if result else 0
            
            # Count document entities
            cur.execute("SELECT COUNT(*) FROM document_entities WHERE _source = 'keel_kg'")
            result = cur.fetchone()
            stats["document_entities"] = result[0] if result else 0
            
            # Count relationships
            cur.execute("SELECT COUNT(*) FROM entity_relationships WHERE _source = 'keel_kg'")
            result = cur.fetchone()
            stats["relationships"] = result[0] if result else 0
            
            # Get entity types
            cur.execute("SELECT DISTINCT entity_type FROM code_entities WHERE _source = 'keel_kg'")
            entity_types = [row[0] for row in cur.fetchall()]
            stats["entity_types"] = entity_types
            
            # Get document types
            cur.execute("SELECT DISTINCT doc_type FROM document_entities WHERE _source = 'keel_kg'")
            doc_types = [row[0] for row in cur.fetchall()]
            stats["document_types"] = doc_types
        
        return stats
    
    def clear_graph(self) -> None:
        """
        Clear all data from PostgreSQL KG tables.
        
        This deletes all entities and relationships from the knowledge graph tables.
        """
        with self._conn.cursor() as cur:
            # Clear relationships first (due to foreign key constraints)
            cur.execute("DELETE FROM entity_relationships WHERE _source = 'keel_kg'")
            deleted_relationships = cur.rowcount
            
            # Clear code entities
            cur.execute("DELETE FROM code_entities WHERE _source = 'keel_kg'")
            deleted_code_entities = cur.rowcount
            
            # Clear document entities
            cur.execute("DELETE FROM document_entities WHERE _source = 'keel_kg'")
            deleted_document_entities = cur.rowcount
        
        logger.info(
            f"Cleared PostgreSQL KG: {deleted_code_entities} code entities, "
            f"{deleted_document_entities} document entities, "
            f"{deleted_relationships} relationships"
        )
    
    def search_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
        table: str = "code_entities",
        entity_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search nodes by embedding similarity using pgvector.
        
        Args:
            embedding: Query embedding vector
            limit: Maximum number of results
            table: Table to search (default: code_entities)
            entity_type: Optional entity type filter
            
        Returns:
            Similar nodes with scores
        """
        # Convert embedding to string for SQL
        embedding_str = str(embedding)
        
        query = f"""
            SELECT name, content, entity_type,
                   1 - (embedding <=> %s::vector) as similarity
            FROM {table}
        """
        params = [embedding_str]
        
        if entity_type:
            query += " WHERE entity_type = %s"
            params.append(entity_type)
        
        query += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([embedding_str, limit])
        
        with self._conn.cursor() as cur:
            cur.execute(query, params)
            results = []
            for row in cur.fetchall():
                results.append({
                    "name": row[0],
                    "content": row[1],
                    "entity_type": row[2],
                    "similarity": float(row[3]),
                })
            return results
    
    def create_vector_index(
        self,
        table: str = "code_entities",
        column: str = "embedding",
        dimension: int = 768,
    ):
        """
        Create a vector index for embeddings using pgvector.
        
        Args:
            table: Table name
            column: Column name with vector data
            dimension: Vector dimension
        """
        with self._conn.cursor() as cur:
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table,))
            
            if not cur.fetchone()[0]:
                logger.warning(f"Table {table} does not exist, skipping index creation")
                return
            
            # Drop existing index if exists
            cur.execute(f"""
                DROP INDEX IF EXISTS {table}_{column}_idx
            """)
            
            # Create HNSW index
            cur.execute(f"""
                CREATE INDEX {table}_{column}_idx 
                ON {table} 
                USING hnsw ({column} vector_cosine_ops)
            """)
            
            logger.info(f"Created vector index on {table}.{column}")
    
    def hybrid_search(
        self,
        embedding: List[float],
        graph_filter: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and graph traversal.
        
        This implements the "bridge pattern" - use vector search to find similar entities,
        then filter by graph relationships.
        
        Args:
            embedding: Query embedding vector
            graph_filter: Optional Cypher WHERE clause for graph filtering
            limit: Maximum number of results
            
        Returns:
            Hybrid search results
        """
        self._ensure_graph()
        
        # Step 1: Vector search
        similar_entities = self.search_by_embedding(embedding, limit=limit * 2)
        
        if not similar_entities:
            return []
        
        # Step 2: Graph traversal to filter results
        similar_names = [e["name"] for e in similar_entities]
        
        if graph_filter:
            query = f"""
                SELECT * FROM cypher(%s, $$
                    MATCH (n)
                    WHERE n.name IN $similar_names
                    AND {graph_filter}
                    RETURN n.name as name, n.content as content
                $$, %s) as (name agtype, content agtype)
            """
            
            with self._conn.cursor() as cur:
                cur.execute(query, (self.graph_name, {"similar_names": similar_names}))
                graph_results = {}
                for row in cur.fetchall():
                    import json
                    name = json.loads(row[0])
                    content = json.loads(row[1])
                    graph_results[name] = content
                
                # Merge results
                final_results = []
                for entity in similar_entities:
                    if entity["name"] in graph_results:
                        entity["graph_matched"] = True
                        final_results.append(entity)
                
                return final_results[:limit]
        else:
            return similar_entities[:limit]
    
    def create_entity_table(
        self,
        table_name: str = "code_entities",
        dimension: int = 768,
    ):
        """
        Create a table for storing entities with embeddings.
        
        Args:
            table_name: Table name
            dimension: Vector dimension
        """
        with self._conn.cursor() as cur:
            cur.execute(f"""
                DROP TABLE IF EXISTS {table_name} CASCADE
            """)
            
            cur.execute(f"""
                CREATE TABLE {table_name} (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    content TEXT,
                    entity_type TEXT,
                    embedding vector({dimension}),
                    _source TEXT DEFAULT 'keel_kg',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            logger.info(f"Created table: {table_name}")
    
    def insert_entity(
        self,
        table_name: str,
        name: str,
        content: str,
        entity_type: str,
        embedding: List[float],
    ):
        """
        Insert an entity with embedding.
        
        Args:
            table_name: Table name
            name: Entity name
            content: Entity content
            entity_type: Entity type
            embedding: Embedding vector
        """
        with self._conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {table_name} (name, content, entity_type, embedding)
                VALUES (%s, %s, %s, %s::vector)
            """, (name, content, entity_type, str(embedding)))
            
            logger.debug(f"Inserted entity: {name}")


def check_postgres_availability(
    host: str = "localhost",
    port: int = 5432,
    user: str = "postgres",
    password: str = "postgres",
    database: str = "knowledge_graph"
) -> tuple[bool, str]:
    """
    Check if PostgreSQL is available.
    
    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        user: PostgreSQL username
        password: PostgreSQL password
        database: Database name
        
    Returns:
        (is_available, message) tuple
    """
    if not PSYCOPG2_AVAILABLE:
        return False, "psycopg2 not installed. Install with: pip install psycopg2-binary"
    
    try:
        client = PostgresClient(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        client.connect()
        client.close()
        
        return True, f"PostgreSQL is available at {host}:{port}/{database}"
        
    except Exception as e:
        return False, f"Cannot connect to PostgreSQL at {host}:{port}: {str(e)}"
