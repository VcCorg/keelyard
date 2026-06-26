# KG Provider Comparison for Code & Requirements Mapping

## Current State

| Provider | Status | ARM64 Compatible | Embeddings | Graph Queries | Notes |
|----------|--------|------------------|------------|---------------|-------|
| Neo4j | ✓ Running | ✓ | ✓ (Vector Index) | ✓ (Cypher) | Mature, stable |
| PostgreSQL (local) | ✗ Broken | ✗ | ✗ (pgvector issues) | ✓ (Apache AGE) | ARM64 build failures |
| LightRAG | ✗ Not Initialized | ✓ | ✓ | ✗ (RAG-focused) | Requires manual initialization |
| Weaviate | ✓ Running | ✓ | ✓ (Native) | ⚠ (GraphQL) | Newly configured |

## Use Case Requirements

**Primary Goal:** Ingest code and business requirements mappings

**Key Requirements:**
1. **Code Entity Ingestion** - Functions, classes, modules, files
2. **Requirements Entity Ingestion** - Business rules, specifications, user stories
3. **Relationship Mapping** - Code implements requirements, references, satisfies
4. **Semantic Search** - Find code related to requirement descriptions
5. **Graph Traversal** - Traceability (requirement → code → tests)
6. **ARM64 Compatibility** - Must work on Apple Silicon
7. **Stability** - Production-ready, reliable

## Provider Analysis

### 1. Neo4j ⭐ RECOMMENDED

**Strengths:**
- ✓ Mature, production-grade graph database
- ✓ Excellent Cypher query language for complex graph traversals
- ✓ Vector Index for semantic search (embeddings)
- ✓ Works perfectly on ARM64
- ✓ Rich ecosystem (Neo4j Bloom, Bloom explorer)
- ✓ Native graph algorithms (shortest path, centrality)
- ✓ Strong relationship modeling (ideal for code→requirements)

**Weaknesses:**
- Requires embeddings configuration (Vertex AI/OpenAI)
- Higher memory usage
- Steeper learning curve for Cypher

**Best For:**
- Complex graph queries (traceability, impact analysis)
- Relationship-heavy data structures
- When you need both graph traversals AND semantic search

**Configuration:**
```bash
dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password <password>
```

### 2. Weaviate ⭐ RECOMMENDED

**Strengths:**
- ✓ Native vector database (designed for embeddings)
- ✓ GraphQL API for flexible queries
- ✓ Works perfectly on ARM64
- ✓ Object-oriented (classes: Code, Requirement, Relationship)
- ✓ Excellent semantic search performance
- ✓ Schema validation
- ✓ Multi-modal support (text, images)
- ✓ Lower memory footprint than Neo4j

**Weaknesses:**
- Graph queries via GraphQL (less intuitive than Cypher)
- Limited native graph algorithms
- Less mature ecosystem than Neo4j
- Relationship modeling is less flexible than Neo4j

**Best For:**
- Semantic search-focused use cases
- When search is primary, graph traversal secondary
- Object-oriented data modeling
- When you want strong schema validation

**Configuration:**
```bash
dva kg init --provider weaviate --weaviate-host localhost --weaviate-port 8080
```

### 3. PostgreSQL (Cloud) ⭐ ALTERNATIVE

**Current Issue:** Local PostgreSQL fails on ARM64 due to pgvector/Apache AGE build issues

**Solution:** Use cloud PostgreSQL with pgvector + Apache AGE

**Options:**
- **Supabase** - Has pgvector, free tier, ARM64 compatible
- **Neon** - Serverless PostgreSQL, pgvector support
- **AWS RDS** - Production-grade, pgvector extension
- **Google Cloud SQL** - pgvector support

**Strengths:**
- ✓ Familiar SQL queries
- ✓ Apache AGE for graph queries (Cypher-compatible)
- ✓ pgvector for embeddings
- ✓ Cloud providers handle ARM64 builds
- ✓ Excellent backup/replication
- ✓ Cost-effective at scale

**Weaknesses:**
- Requires cloud account setup
- Network latency
- Cloud costs (though free tiers available)
- Apache AGE learning curve

**Best For:**
- When you need relational + graph + vector in one database
- Cloud-native architecture
- When you want PostgreSQL familiarity

**Configuration (Supabase example):**
```bash
# Create Supabase project with pgvector extension
# Enable Apache AGE extension in SQL editor
dva kg init --provider postgres \
  --postgres-host <supabase-host>.supabase.co \
  --postgres-port 5432 \
  --postgres-user postgres \
  --postgres-password <supabase-password> \
  --postgres-database postgres
```

### 4. LightRAG ✗ NOT RECOMMENDED

**Strengths:**
- ✓ Designed for RAG (Retrieval Augmented Generation)
- ✓ Built-in entity extraction
- ✓ Good for document ingestion
- ✓ Multiple query modes (naive, local, global, hybrid)

**Weaknesses:**
- ✗ **Not initialized** - Container runs but requires manual initialization
- ✗ All operations fail with "LightRAG not initialized" error
- ✗ Multiple known stability issues (see fix documents in kg-infrastructure/lightrag/)
- ✗ RAG-focused, not graph-focused
- ✗ Less control over graph structure
- ✗ Limited relationship modeling
- ✗ Not ideal for structured code→requirements mapping

**Test Results:**
- Health check: ✓ Returns healthy
- Insert operation: ✗ Fails with "LightRAG not initialized"
- Query operation: ✗ Fails with "LightRAG not initialized"
- Stats operation: ✗ Fails with "LightRAG not initialized"

**Known Issues:**
- Document status value mismatches
- Authentication setup complexity
- Query/search reliability problems
- Requires manual initialization

**Best For:**
- Document Q&A systems
- When you need automatic entity extraction
- RAG applications (not graph use cases)

**Recommendation:** Skip for this use case. Requires manual initialization and has known stability issues.

## Recommendations

### Primary Recommendation: Neo4j + Weaviate (Hybrid)

**Use Neo4j for:**
- Code entity storage (functions, classes, modules)
- Requirement entity storage
- Relationship modeling (implements, satisfies, references)
- Graph traversals (traceability, impact analysis)
- Complex graph queries

**Use Weaviate for:**
- Semantic search (find code related to requirements)
- Vector embeddings storage
- Natural language queries
- Similarity search

**Architecture:**
```
Code Ingestion → Neo4j (Graph) + Weaviate (Vectors)
              ↓
         Dual Storage
              ↓
    Query Engine (Neo4j for graph, Weaviate for search)
```

**Pros:**
- Best of both worlds (graph + vector)
- Each database optimized for its strength
- Redundancy (backup if one fails)
- Flexibility to use either based on query type

**Cons:**
- Complexity (two databases to manage)
- Data synchronization required
- Higher cost (two databases)

### Alternative: Single Provider

**Choose Neo4j if:**
- Graph traversals are primary use case
- You need complex relationship queries
- Traceability is critical
- Team prefers Cypher over GraphQL

**Choose Weaviate if:**
- Semantic search is primary use case
- You prefer GraphQL over Cypher
- Object-oriented modeling fits your mental model
- Memory constraints (Weaviate uses less)

**Choose PostgreSQL (Cloud) if:**
- You want one database for everything
- You prefer SQL over graph query languages
- You need cloud-native architecture
- Team has PostgreSQL experience

## Implementation Path

### Option 1: Neo4j (Quick Start)

```bash
# Already running
dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password <password>

# Test
dva kg check --provider neo4j
dva kg stats
```

### Option 2: Weaviate (Quick Start)

```bash
# Already configured
dva kg init --provider weaviate --weaviate-host localhost --weaviate-port 8080

# Test
dva kg check --provider weaviate
dva kg stats
```

### Option 3: PostgreSQL Cloud (Setup Required)

```bash
# 1. Create Supabase project
# 2. Enable pgvector extension in SQL editor
# 3. Enable Apache AGE extension
# 4. Configure DVA
dva kg init --provider postgres \
  --postgres-host <supabase-host>.supabase.co \
  --postgres-port 5432 \
  --postgres-user postgres \
  --postgres-password <supabase-password> \
  --postgres-database postgres
```

## Decision Matrix

| Criterion | Neo4j | Weaviate | PostgreSQL Cloud | LightRAG |
|-----------|-------|----------|------------------|----------|
| ARM64 Compatible | ✓ | ✓ | ✓ (cloud) | ✓ |
| Graph Queries | ✓✓✓ | ✓ | ✓ | ✗ |
| Semantic Search | ✓✓ | ✓✓✓ | ✓✓ | ✓✓ |
| Relationship Modeling | ✓✓✓ | ✓ | ✓ | ✗ |
| Stability | ✓✓✓ | ✓✓ | ✓✓✓ | ✗ |
| Ease of Setup | ✓ | ✓ | ⚠ (cloud) | ✗ |
| Learning Curve | ⚠ | ✓ | ✓ | ✓ |
| Cost (Self-hosted) | ⚠ (memory) | ✓ | N/A | ✓ |
| Production Ready | ✓✓✓ | ✓✓ | ✓✓✓ | ✗ |

## Next Steps

1. **Short Term (This Week):**
   - ✓ Test Neo4j with sample code + requirements data (COMPLETED)
   - ✓ Test Weaviate with sample code + requirements data (COMPLETED)
   - ✓ Test LightRAG stability (FAILED - not initialized)
   - ✓ Compare query performance and ease of use (COMPLETED)
   - ✓ Decide on primary provider (Neo4j recommended)

2. **Medium Term (Next Sprint):**
   - Implement ingestion pipeline for Neo4j
   - Build code→requirements mapping schema in Neo4j
   - Implement traceability queries using Cypher
   - Add semantic search using Neo4j Vector Index

3. **Long Term:**
   - Consider hybrid Neo4j + Weaviate if single provider limitations emerge
   - Evaluate PostgreSQL cloud if team prefers SQL
   - Monitor LightRAG stability improvements (currently not recommended)

## Questions to Decide

1. **What's more important:**
   - Graph traversals (traceability, impact analysis)? → Neo4j
   - Semantic search (find code from natural language)? → Weaviate

2. **Team expertise:**
   - Cypher (Neo4j) vs GraphQL (Weaviate) vs SQL (PostgreSQL)

3. **Infrastructure preference:**
   - Self-hosted (Neo4j, Weaviate) vs Cloud (PostgreSQL)

4. **Budget:**
   - Self-hosted (free) vs Cloud (costs at scale)

## Recommendation Summary

**For Code + Requirements Mapping:**

1. **Start with Neo4j** - Best for relationship modeling and graph traversals (traceability is key for requirements)
2. **Consider Weaviate** - If semantic search is your primary need
3. **Skip PostgreSQL local** - ARM64 issues, use cloud if you want PostgreSQL
4. **Skip LightRAG** - Not initialized, requires manual setup, known stability issues

**My recommendation:** Start with **Neo4j** for this use case because:
- Code→requirements mapping is fundamentally a graph problem
- Traceability requires graph traversals
- Neo4j is mature and stable
- Vector Index gives you semantic search too
- Best fit for the specific use case
