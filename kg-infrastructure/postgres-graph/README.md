# PostgreSQL + pgvector + Apache AGE

A unified knowledge graph infrastructure combining vector search (pgvector) and graph traversal (Apache AGE) in a single PostgreSQL database.

## Overview

This setup provides:
- **Vector Search**: Fast semantic search using pgvector with HNSW indexes
- **Graph Traversal**: Cypher-based graph queries using Apache AGE
- **Hybrid Queries**: Combine vector similarity with graph relationships
- **Single Database**: One backup, one monitoring stack, one connection pool
- **Cost Effective**: ~$650/month savings vs Neo4j + Weaviate

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                       │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
                ┌───────────┴──────────┐
                │    PostgreSQL         │
                │  + pgvector (vectors) │
                │  + Apache AGE (graph) │
                │  Single SQL Database  │
                └───────────────────────┘
```

## Quick Start

### 1. Start the Database

```bash
cd /Users/your-user/agentic-project/myAgentPG/kg-infrastructure/postgres-graph
docker-compose up -d
```

This will:
- Build the Docker image with PostgreSQL 16, pgvector, and Apache AGE
- Start the database on port 5432
- Initialize the database with extensions
- Create a test graph called `knowledge_graph`

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Knowledge Graph Tables

```bash
./setup-kg.sh
```

This creates:
- `code_entities` table with vector index for code artifacts
- `document_entities` table with vector index for documents
- `entity_relationships` table for tracking relationships
- Apache AGE graph named `knowledge_graph`

### 4. Validate Setup

```bash
./validate-mcp.sh
```

This validates:
- PostgreSQL connection
- Extensions (pgvector, Apache AGE)
- KG tables and indexes
- Apache AGE graph
- MCP server availability (if running)

### 3. Run Test Scripts

```bash
# Test vector search
python scripts/test_vector_search.py

# Test graph queries
python scripts/test_graph_queries.py

# Test hybrid (vector + graph) queries
python scripts/test_hybrid_queries.py
```

## Database Connection

**Default Credentials:**
- **Host**: localhost
- **Port**: 5432
- **User**: postgres
- **Password**: postgres
- **Database**: knowledge_graph

**Environment Variables:**
Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

## Usage Examples

### Vector Search

```python
import psycopg2
import numpy as np

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="knowledge_graph"
)

# Create table with vector column
with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE code_entities (
            id SERIAL PRIMARY KEY,
            name TEXT,
            content TEXT,
            embedding vector(768)
        )
    """)
    
    # Create HNSW index
    cur.execute("""
        CREATE INDEX code_entities_embedding_idx 
        ON code_entities 
        USING hnsw (embedding vector_cosine_ops)
    """)
    
    # Insert with embedding
    embedding = np.random.rand(768).tolist()
    cur.execute(
        "INSERT INTO code_entities (name, content, embedding) VALUES (%s, %s, %s)",
        ("my_function", "function description", embedding)
    )
    
    # Vector search
    query_vector = np.random.rand(768).tolist()
    cur.execute("""
        SELECT name, content, 1 - (embedding <=> %s) as similarity
        FROM code_entities
        ORDER BY embedding <=> %s
        LIMIT 5
    """, (query_vector, query_vector))
    
    results = cur.fetchall()
```

### Graph Queries (Apache AGE)

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="knowledge_graph"
)

with conn.cursor() as cur:
    # Set search path
    cur.execute("SET search_path = ag_catalog, '$user', public")
    
    # Create graph
    cur.execute("SELECT create_graph('knowledge_graph')")
    
    # Create nodes and edges
    cur.execute("""
        SELECT * FROM cypher('knowledge_graph', $$
            CREATE (f:Function {name: 'calculate_dosage'})
            CREATE (c:Class {name: 'Patient'})
            CREATE (f)-[:OPERATES_ON]->(c)
        $$) as (result agtype)
    """)
    
    # Graph traversal
    cur.execute("""
        SELECT * FROM cypher('knowledge_graph', $$
            MATCH (f:Function)-[:OPERATES_ON]->(c:Class)
            RETURN f.name, c.name
        $$) as (function_name agtype, class_name agtype)
    """)
    
    results = cur.fetchall()
```

### Hybrid Queries (Bridge Pattern)

```python
# Step 1: Vector search to find similar entities
cur.execute("""
    WITH similar_entities AS (
        SELECT id, name, 1 - (embedding <=> %s) as similarity
        FROM code_entities
        ORDER BY embedding <=> %s
        LIMIT 10
    )
    SELECT * FROM similar_entities
""", (query_vector, query_vector))

# Step 2: Use results in graph traversal
cur.execute("""
    SELECT * FROM cypher('knowledge_graph', $$
        MATCH (f:Function)-[:RELATES_TO]->(other)
        WHERE f.name IN $similar_names
        RETURN f.name, other.name
    $$, {'similar_names': similar_names}) as (name agtype, other_name agtype)
""")

# Or combine in single query
cur.execute("""
    WITH similar_functions AS (
        SELECT id, name, 1 - (embedding <=> %s) as similarity
        FROM code_entities
        ORDER BY embedding <=> %s
        LIMIT 10
    )
    SELECT sf.name, sf.similarity
    FROM similar_functions sf
    WHERE sf.name IN (
        SELECT f.name::text 
        FROM cypher('knowledge_graph', $$
            MATCH (f:Function)-[:OPERATES_ON]->(c:Class {name: 'Patient'})
            RETURN f.name
        $$) as (name agtype)
    )
""", (query_vector, query_vector))
```

## Performance Considerations

### Vector Search
- **HNSW Index**: Use for approximate nearest neighbor search (fast, ~95% recall)
- **IVFFlat Index**: Use for exact search (slower, 100% recall)
- **Cosine Similarity**: `vector_cosine_ops` operator class
- **Euclidean Distance**: `vector_l2_ops` operator class

### Graph Queries
- **Index**: Create indexes on frequently queried properties
- **Query Optimization**: Use specific node labels and relationship types
- **Batch Operations**: Use multiple MATCH clauses in single query

### Hybrid Queries
- **Bridge Pattern**: Pre-compute similarity edges for frequently used queries
- **Materialized Views**: Cache results of expensive hybrid queries
- **Query Planning**: Consider vector search first, then graph traversal

## Cost Comparison

| Option | Monthly Cost | Savings |
|--------|--------------|---------|
| Neo4j + Weaviate | $900 | baseline |
| PostgreSQL + Extensions | $250 | -$650 |

## Migration from Neo4j + Weaviate

### Step 1: Export Neo4j Data
```bash
# Export nodes and relationships to CSV
neo4j-admin dump --database=neo4j --to=/backup/neo4j-backup
```

### Step 2: Import to Apache AGE
```python
# Use cypher() function to load data
cur.execute("""
    SELECT * FROM cypher('knowledge_graph', $$
        LOAD CSV FROM 'file:///nodes.csv' AS row
        CREATE (n:Node {id: row.id, name: row.name})
    $$) as (result agtype)
""")
```

### Step 3: Migrate Vectors
```python
# Export from Weaviate, import to pgvector
# Weaviate uses similar vector dimensions
cur.execute("""
    INSERT INTO code_entities (name, content, embedding)
    VALUES (%s, %s, %s::vector)
""", (name, content, vector))
```

### Step 4: Update Application Code
- Replace Neo4j driver with psycopg2
- Replace Cypher queries with `cypher()` function calls
- Replace Weaviate queries with pgvector queries
- Implement bridge pattern for hybrid queries

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs postgres

# Rebuild image
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Extension not loaded
```sql
-- Check extensions
SELECT * FROM pg_extension;

-- Load manually
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS age;
```

### Graph queries fail
```sql
-- Check search path
SET search_path = ag_catalog, "$user", public;

-- Check graph exists
SELECT * FROM ag_graph;

-- Create graph if needed
SELECT create_graph('knowledge_graph');
```

## Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Apache AGE Documentation](https://age.apache.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## License

This infrastructure setup is part of the myAgentPG project.
