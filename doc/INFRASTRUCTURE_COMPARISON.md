# Infrastructure Comparison: Neo4j, LightRAG, and Weaviate

## Executive Summary

| System | Primary Purpose | Core Strength | Critical Limitation for DVA |
|--------|----------------|---------------|---------------------------|
| **Neo4j** | Graph storage and traversal | Mature graph ecosystem, Cypher query language | No built-in vector search, requires external embedding service |
| **LightRAG** | Graph-enhanced RAG | Combines graph + vector search in one library | Unstable library, requires patching, limited scalability |
| **Weaviate** | Vector database with graph capabilities | Native vector search + object relationships, stable | Graph features less mature than Neo4j |

**Key Insight:** No single system provides everything DVA needs. Each requires trade-offs between stability, capabilities, and complexity.

---

## Part 1: System-by-System Deep Dive

### Neo4j

#### What It Is
- **Pure graph database** optimized for storing and querying connected data
- Uses property graph model (nodes, relationships, properties)
- Query language: Cypher (declarative, similar to SQL for graphs)

#### Architecture
```
┌─────────────────────────────────────┐
│         Neo4j Database              │
│  ┌─────────┐      ┌──────────────┐ │
│  │ Nodes   │◄─────│ Relationships│ │
│  │ (Code,  │      │ (implements, │ │
│  │  Doc)   │      │  references) │ │
│  └─────────┘      └──────────────┘ │
└─────────────────────────────────────┘
         ▲         ▲         ▲
         │         │         │
    Cypher Queries  │    Bolt Protocol
                    │   (Binary Protocol)
                    │
              HTTP API (7474)
```

#### Capabilities
- **Graph Traversal**: Efficiently navigate relationships (e.g., "find all functions that reference class X")
- **Pattern Matching**: Complex graph patterns using Cypher
- **ACID Transactions**: Reliable multi-operation transactions
- **Indexing**: Property indexes for fast lookups
- **Vector Index** (Limited): Can store embeddings but search is basic cosine similarity

#### Why Neo4j Alone Is Insufficient

**1. No Native Vector Search**
```cypher
// Neo4j's vector search is basic and slow
CALL db.index.vector.queryNodes('myIndex', 5, $embedding)
YIELD node, score
RETURN node, score
```
- Limited to cosine similarity
- No hybrid search (vector + filters)
- No reranking
- No advanced vector operations (e.g., fusion search)

**2. Requires External Embedding Pipeline**
```
Code → Embedding Service (Vertex AI) → Store in Neo4j
         ↑                              ↑
    External dependency          Manual management
```
- Need separate service for generating embeddings
- Manual synchronization between code changes and embeddings
- No automatic re-indexing when data changes

**3. Poor Semantic Search Performance**
- Vector search in Neo4j is ~10-100x slower than specialized vector DBs
- No built-in HNSW/IVF indexes for approximate nearest neighbor
- No support for large-scale vector operations (>1M vectors)

**4. Limited RAG Capabilities**
- No built-in context window management
- No citation/retrieval metadata
- No query expansion or rewriting
- No hybrid ranking (BM25 + vector)

#### Complexities
- **Query Complexity**: Cypher has steep learning curve for complex graph patterns
- **Schema Management**: Requires manual schema design and evolution
- **Scaling**: Horizontal scaling requires Enterprise Edition
- **Embedding Integration**: Custom pipeline required for vector operations

---

### LightRAG

#### What It Is
- **Python library** that combines vector search with knowledge graph
- Built on top of NetworkX (graph) + nano-vectordb (vectors) by default
- Designed for RAG (Retrieval-Augmented Generation) use cases

#### Architecture
```
┌─────────────────────────────────────────────────────┐
│              LightRAG Library                       │
│  ┌──────────────┐      ┌──────────────┐           │
│  │ Vector Store │◄────►│ Graph Store  │           │
│  │ (nano-vectordb│      │ (NetworkX)   │           │
│  │  / Milvus)   │      │ (or Neo4j)   │           │
│  └──────────────┘      └──────────────┘           │
│           ▲                    ▲                   │
│           │                    │                   │
│  ┌────────┴────────────────────┴─────────┐       │
│  │         Query Engine (hybrid mode)      │       │
│  │  - Local context search                 │       │
│  │  - Global graph traversal              │       │
│  │  - Fusion ranking                       │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

#### Capabilities
- **Hybrid Search**: Combines vector similarity with graph traversal
- **Context-Aware Retrieval**: Uses graph structure to enhance relevance
- **Multiple Query Modes**: naive, local, global, hybrid
- **Built-in LLM Integration**: Direct integration with OpenAI, Anthropic, Vertex AI

#### Why LightRAG Alone Is Insufficient

**1. Library Instability**
```
Current Issues in LightRAG v1.4.16:
- NetworkX graph serialization failures
- Race conditions in async operations
- Memory leaks in vector store operations
- Inconsistent behavior across storage backends
```
- Requires manual patching of source code
- No official support channel
- Breaking changes between minor versions
- Production deployment risk

**2. Limited Scalability**
- Default storage (nano-vectordb) is in-memory only
- NetworkX doesn't scale beyond ~100K nodes
- No distributed deployment option
- Single-process architecture

**3. No Persistent Graph Storage**
```
Default: NetworkX (in-memory)
Problem: Data loss on restart
Alternative: Neo4j
Problem: Requires additional infrastructure
```
- Need to choose between data loss (NetworkX) or complexity (Neo4j)
- No seamless migration path
- Schema inconsistencies between storage backends

**4. Tight LLM Coupling**
- Designed specifically for RAG with LLMs
- Not suitable for general-purpose graph queries
- Limited query flexibility outside of RAG use cases
- No API for direct graph operations

**5. Poor Integration with Existing Systems**
- No standard protocol (only Python library)
- No REST API (requires custom FastAPI wrapper)
- No MCP server integration
- No multi-language support

#### Complexities
- **Version Management**: Frequent breaking changes require constant updates
- **Debugging**: Poor error messages, hard to trace issues
- **Testing**: Inconsistent behavior makes testing difficult
- **Deployment**: Requires custom Docker setup for production

---

### Weaviate

#### What It Is
- **Vector database** with graph-like object relationships
- Designed for AI/ML workloads with native vector operations
- Uses GraphQL + REST APIs for queries

#### Architecture
```
┌─────────────────────────────────────────────────────┐
│              Weaviate Database                      │
│  ┌──────────────┐      ┌──────────────┐           │
│  │ Vector Index │◄────►│ Object Store │           │
│  │ (HNSW/IVF)   │      │ (Collections)│           │
│  │  + gRPC      │      │ + References │           │
│  └──────────────┘      └──────────────┘           │
│           ▲                    ▲                   │
│           │                    │                   │
│  ┌────────┴────────────────────┴─────────┐       │
│  │         Query Engine                     │       │
│  │  - Vector search (near_vector)         │       │
│  │  - Hybrid search (BM25 + vector)       │       │
│  │  - Graph traversal (references)        │       │
│  │  - Filter aggregation                 │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

#### Capabilities
- **Native Vector Search**: HNSW/IVF indexes for fast approximate nearest neighbor
- **Hybrid Search**: BM25 keyword search + vector similarity with fusion
- **Object References**: Cross-collection relationships (graph-like)
- **Multi-modal**: Text, image, audio vectors
- **REST + gRPC**: Standard protocols for integration
- **Modular Vectorizers**: Built-in integrations (OpenAI, Cohere, Vertex AI) or manual

#### Why Weaviate Alone Is Insufficient

**1. Graph Capabilities Are Limited**
```python
# Weaviate references are simple cross-collection links
# Not a full graph database
collection.data.insert(
    properties={"name": "calculate_patient_dosage"},
    references={
        "references": [{"target": "patient_class_uuid"}]
    }
)
```
- No Cypher-like query language
- Limited relationship types (only references)
- No relationship properties
- No graph algorithms (centrality, pathfinding)
- No recursive queries

**2. Schema Rigidity**
- Requires upfront schema definition
- Schema changes are difficult
- No dynamic property addition
- Limited to property graph model (no hyperedges)

**3. Less Mature Ecosystem**
- Smaller community than Neo4j
- Fewer tools and integrations
- Limited visualization options
- Steeper learning curve for GraphQL

#### Complexities
- **Schema Design**: Requires careful upfront planning
- **Vector Management**: Manual vectorization or integration with embedding service
- **GraphQL Queries**: Complex nested queries can be difficult
- **gRPC Configuration**: Additional complexity for high-performance setups

---

## Part 2: Side-by-Side Comparison

### Core Capabilities Matrix

| Capability | Neo4j | LightRAG | Weaviate |
|------------|-------|----------|----------|
| **Graph Storage** | ✅ Excellent | ⚠️ Basic (NetworkX) | ⚠️ Limited (references) |
| **Graph Traversal** | ✅ Excellent (Cypher) | ⚠️ Basic (NetworkX) | ⚠️ Limited (GraphQL) |
| **Graph Algorithms** | ✅ Extensive | ❌ None | ❌ None |
| **Vector Search** | ⚠️ Basic (slow) | ✅ Good (nano-vectordb) | ✅ Excellent (HNSW) |
| **Hybrid Search** | ❌ No | ✅ Yes (local+global) | ✅ Yes (BM25+vector) |
| **RAG Integration** | ❌ No | ✅ Built-in | ⚠️ Manual |
| **Scalability** | ✅ Good (Enterprise) | ❌ Poor (in-memory) | ✅ Good (distributed) |
| **Stability** | ✅ Excellent | ❌ Poor (unstable) | ✅ Excellent |
| **API Protocol** | ✅ REST + Bolt | ⚠️ Python only | ✅ REST + gRPC |
| **Query Language** | ✅ Cypher (powerful) | ❌ Library methods | ⚠️ GraphQL (complex) |
| **Embedding Service** | ❌ External required | ✅ Built-in | ✅ Built-in or manual |

### Infrastructure Complexity

| Aspect | Neo4j | LightRAG | Weaviate |
|--------|-------|----------|----------|
| **Setup** | ⭐⭐ Simple (Docker) | ⭐⭐⭐ Medium (custom API) | ⭐⭐ Simple (Docker) |
| **Configuration** | ⭐⭐⭐ Medium (env vars) | ⭐⭐⭐⭐ Complex (multiple backends) | ⭐⭐ Simple (env vars) |
| **Maintenance** | ⭐⭐ Low (mature) | ⭐⭐⭐⭐⭐ High (patching required) | ⭐⭐ Low (stable) |
| **Monitoring** | ⭐⭐⭐ Good (built-in) | ⭐ Poor (custom) | ⭐⭐⭐ Good (built-in) |
| **Backup/Restore** | ⭐⭐⭐ Good (native) | ⭐⭐ Manual (custom) | ⭐⭐⭐ Good (native) |
| **Scaling** | ⭐⭐ Enterprise only | ⭐ Not possible | ⭐⭐⭐ Good (horizontal) |
| **Security** | ⭐⭐⭐⭐ RBAC, SSL | ⭐⭐ Basic (API key) | ⭐⭐⭐ RBAC, API keys |

### Development Complexity

| Aspect | Neo4j | LightRAG | Weaviate |
|--------|-------|----------|----------|
| **Learning Curve** | ⭐⭐⭐⭐ Steep (Cypher) | ⭐⭐ Medium (Python) | ⭐⭐⭐ Medium (GraphQL) |
| **Documentation** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Fair | ⭐⭐⭐⭐ Good |
| **Community Support** | ⭐⭐⭐⭐⭐ Large | ⭐⭐ Small | ⭐⭐⭐ Medium |
| **Debugging** | ⭐⭐⭐ Good tools | ⭐ Poor (library issues) | ⭐⭐⭐ Good logs |
| **Testing** | ⭐⭐⭐ Testcontainers | ⭐⭐ Difficult (instability) | ⭐⭐⭐ Testcontainers |
| **Integration** | ⭐⭐⭐⭐ Many drivers | ⭐ Python only | ⭐⭐⭐⭐ Many clients |

---

## Part 3: Why Each Alone Is Insufficient for DVA

### DVA Requirements

1. **Code Entity Storage**: Functions, classes, modules with metadata
2. **Relationships**: Implements, references, calls, inherits
3. **Semantic Search**: Find code by meaning (e.g., "calculate dosage")
4. **Graph Traversal**: Navigate call graphs, dependency chains
5. **Scalability**: Support 100K+ code entities
6. **Stability**: Production-ready with minimal maintenance
7. **Integration**: MCP server, CLI, web UI
8. **Performance**: Sub-second query response times

### Neo4j Alone: Why It Fails

**Missing Critical Capability: Vector Search**
```
DVA Need: "Find functions related to medication dosage"
Neo4j Approach:
  1. Manually generate embeddings with Vertex AI
  2. Store embeddings as node properties
  3. Use CALL db.index.vector.queryNodes() (slow)
  4. Results: ~10-100x slower than Weaviate
```

**Problem**: No native, fast vector search. Requires:
- External embedding service
- Custom synchronization logic
- Poor performance at scale

**Complexity Added**: Need to build and maintain embedding pipeline

---

### LightRAG Alone: Why It Fails

**Missing Critical Capability: Stability**
```
Current LightRAG Issues:
- NetworkX serialization fails intermittently
- Async operations have race conditions
- Memory leaks in vector operations
- Breaking changes in v1.4.16

Impact on DVA:
- Production deployment risk
- Constant patching required
- Data loss potential
- Unpredictable behavior
```

**Problem**: Library is unstable, not production-ready.

**Complexity Added**: 
- Custom FastAPI wrapper needed
- Manual patching of library code
- Custom monitoring for library issues
- Fallback strategies for failures

---

### Weaviate Alone: Why It Fails

**Missing Critical Capability: Graph Traversal**
```
DVA Need: "Find all functions that call Patient.calculate_dosage()"
Weaviate Approach:
  1. Store references between objects
  2. Use GraphQL to traverse: 
     {
       Get {
         CodeEntity {
           name
           references {
             ... on CodeEntity {
               name
             }
           }
         }
       }
     }
  3. Limitations:
        - No relationship properties
        - No recursive queries
        - No graph algorithms
        - Complex GraphQL syntax
```

**Problem**: Limited graph capabilities compared to Neo4j.

**Complexity Added**:
- Complex GraphQL queries for graph operations
- Manual relationship management
- No graph algorithms (centrality, pathfinding)
- Schema rigidity

---

## Part 4: Recommended Architecture

### Current Architecture (Neo4j + LightRAG)

```
┌─────────────────────────────────────────────────────────┐
│                    DVA KG Stack                          │
│                                                          │
│  ┌──────────────┐         ┌──────────────┐             │
│  │    Neo4j     │         │   LightRAG   │             │
│  │  (Graph DB)  │         │ (RAG Library)│             │
│  │              │         │              │             │
│  │ - Entities   │         │ - Vector DB   │             │
│  │ - Relations  │         │ - Graph Store │             │
│  │ - Cypher     │         │ - LLM Integ.  │             │
│  └──────────────┘         └──────────────┘             │
│         ▲                        ▲                      │
│         │                        │                      │
│         └──────────┬─────────────┘                      │
│                    │                                    │
│         ┌──────────▼─────────────┐                      │
│         │   KG MCP Server (:8131) │                     │
│         │   (Unified Interface)   │                     │
│         └──────────────────────────┘                     │
└─────────────────────────────────────────────────────────┘

Issues:
- LightRAG unstable, requires patching
- Dual infrastructure complexity
- Data synchronization challenges
```

### Recommended Architecture (Neo4j + Weaviate)

```
┌─────────────────────────────────────────────────────────┐
│                    DVA KG Stack (Future)                │
│                                                          │
│  ┌──────────────┐         ┌──────────────┐             │
│  │    Neo4j     │         │   Weaviate   │             │
│  │  (Graph DB)  │         │ (Vector DB)  │             │
│  │              │         │              │             │
│  │ - Entities   │         │ - Vectors    │             │
│  │ - Relations  │         │ - Embeddings │             │
│  │ - Graph Algo │         │ - Hybrid Srch│             │
│  │ - Cypher     │         │ - References │             │
│  └──────────────┘         └──────────────┘             │
│         ▲                        ▲                      │
│         │                        │                      │
│         └──────────┬─────────────┘                      │
│                    │                                    │
│         ┌──────────▼─────────────┐                      │
│         │   KG MCP Server (:8131) │                     │
│         │   (Unified Interface)   │                     │
│         └──────────────────────────┘                     │
└─────────────────────────────────────────────────────────┘

Benefits:
- Neo4j: Mature graph operations, Cypher, algorithms
- Weaviate: Fast vector search, hybrid search, stable
- Clear separation of concerns
- Both production-ready
```

### Migration Strategy

**Phase 1: Add Weaviate Alongside** (Current)
- Deploy Weaviate infrastructure
- Validate schema and test data
- Run parallel queries to validate

**Phase 2: Migrate Vector Operations** (Next)
- Move semantic search from LightRAG to Weaviate
- Keep Neo4j for graph operations
- Update KG MCP to use both systems

**Phase 3: Deprecate LightRAG** (Future)
- Remove LightRAG dependencies
- Clean up infrastructure
- Document new architecture

---

## Part 5: Complexity Trade-offs

### Neo4j + LightRAG (Current)

**Pros:**
- Graph operations are powerful (Cypher)
- RAG capabilities built-in
- Single library for graph + vectors

**Cons:**
- LightRAG instability (requires constant patching)
- Dual infrastructure complexity
- Data synchronization issues
- Poor scalability (NetworkX in-memory)

**Complexity Score: 8/10** (High due to LightRAG instability)

---

### Neo4j + Weaviate (Recommended)

**Pros:**
- Both systems are production-ready and stable
- Clear separation of concerns
- Excellent performance for respective use cases
- Strong community support for both
- Scalable architecture

**Cons:**
- Dual infrastructure complexity
- Need to manage two systems
- Data synchronization required
- Higher learning curve (two query languages)

**Complexity Score: 6/10** (Medium, but manageable)

---

### Weaviate Only (Not Recommended)

**Pros:**
- Single infrastructure
- Built-in vector + graph-like capabilities
- Stable and production-ready

**Cons:**
- Limited graph capabilities
- No graph algorithms
- Schema rigidity
- Complex GraphQL queries
- Poor graph traversal performance

**Complexity Score: 5/10** (Low initially, but high for complex queries)

---

### Neo4j Only (Not Recommended)

**Pros:**
- Single infrastructure
- Excellent graph capabilities
- Mature ecosystem
- Powerful query language

**Cons:**
- No native vector search
- Requires external embedding pipeline
- Poor vector search performance
- No hybrid search
- Limited RAG capabilities

**Complexity Score: 7/10** (High due to custom embedding pipeline)

---

## Part 6: Decision Framework

### When to Use Each System

**Use Neo4j when:**
- You need complex graph traversals
- You need graph algorithms (centrality, pathfinding)
- You have existing Cypher expertise
- You need ACID transactions
- You require mature graph tooling

**Use Weaviate when:**
- You need fast vector search
- You need hybrid search (BM25 + vector)
- You need multi-modal vectors
- You want built-in embedding integration
- You prefer GraphQL over Cypher

**Use LightRAG when:**
- You need quick RAG prototype (not production)
- You want graph-enhanced retrieval out-of-the-box
- You're okay with library instability
- You have small datasets (<10K entities)
- You're building a proof-of-concept

### Recommended for DVA

**Primary System: Neo4j**
- Graph operations are core to DVA use case
- Mature and stable
- Excellent for code entity relationships
- Powerful Cypher queries

**Secondary System: Weaviate**
- Semantic search is critical for developer experience
- Fast vector search at scale
- Stable and production-ready
- Good complement to Neo4j

**Avoid: LightRAG**
- Too unstable for production
- Limited scalability
- Adds unnecessary complexity
- Better alternatives available

---

## Part 7: Implementation Complexity Comparison

### Query Complexity

**Neo4j (Graph Traversal)**
```cypher
// Find all functions that call Patient.calculate_dosage()
MATCH (f:Code:Function)-[:CALLS]->(m:Code:Method {name: 'calculate_dosage'})
MATCH (m)-[:BELONGS_TO]->(c:Code:Class {name: 'Patient'})
RETURN f.name, f.file_path
ORDER BY f.name
```
- **Complexity**: Medium
- **Learning Curve**: Steep (Cypher)
- **Performance**: Excellent (graph traversal)

**Weaviate (Vector Search)**
```graphql
{
  Get {
    CodeEntity(
      nearVector: {
        vector: [0.1, 0.2, ...],
        distance: 0.3
      }
      limit: 5
    ) {
      name
      content
      _additional {
        distance
      }
    }
  }
}
```
- **Complexity**: Medium
- **Learning Curve**: Medium (GraphQL)
- **Performance**: Excellent (HNSW index)

**LightRAG (Hybrid Search)**
```python
result = client.query(
    query="Find functions that calculate patient dosage",
    mode="hybrid",
    top_k=10
)
```
- **Complexity**: Low
- **Learning Curve**: Low (Python)
- **Performance**: Good (but unstable)

---

### Data Ingestion Complexity

**Neo4j**
```python
# Simple entity insertion
client.execute_cypher("""
  CREATE (e:Code:Function {
    id: $id,
    name: $name,
    file_path: $path
  })
""", params)
```
- **Complexity**: Low
- **Performance**: Good

**Weaviate**
```python
# Requires vectors upfront
collection.data.insert(
    properties={"name": "calculate_dosage"},
    vector=embedding_vector  # Must generate separately
)
```
- **Complexity**: Medium (need vectors)
- **Performance**: Good

**LightRAG**
```python
# Automatic vectorization
client.insert("calculate_dosage function code...")
```
- **Complexity**: Low
- **Performance**: Good (but unstable)

---

### Infrastructure Complexity

**Neo4j**
- Docker container: 1
- Ports: 7474 (HTTP), 7687 (Bolt)
- Dependencies: None
- Setup time: 2 minutes

**Weaviate**
- Docker container: 1
- Ports: 8080 (HTTP), 50051 (gRPC)
- Dependencies: None
- Setup time: 2 minutes

**LightRAG**
- Docker container: 1 (custom FastAPI wrapper)
- Ports: 8001 (HTTP)
- Dependencies: LLM API key, vector store, graph store
- Setup time: 10+ minutes (configuration + patching)

---

## Part 8: Cost Comparison

### Infrastructure Costs (Local Development)

| System | Docker Image | Memory | Storage | Total |
|--------|--------------|--------|---------|-------|
| Neo4j | 500 MB | 2 GB | 1 GB | Low |
| Weaviate | 200 MB | 1 GB | 500 MB | Low |
| LightRAG | 300 MB (Python) | 1 GB | 500 MB | Low |

### Cloud Costs (Production)

| System | Instance Type | Monthly Cost | Notes |
|--------|--------------|-------------|-------|
| Neo4j | n2-highmem-8 (32 GB RAM) | ~$300 | Enterprise required for scaling |
| Weaviate | n2-standard-4 (16 GB RAM) | ~$150 | Open-source, horizontal scaling |
| LightRAG | n2-standard-2 (8 GB RAM) | ~$75 | Not production-ready |

---

## Part 9: Conclusion

### Key Takeaways

1. **No single system meets all DVA requirements**
   - Neo4j: Excellent graph, poor vectors
   - Weaviate: Excellent vectors, limited graph
   - LightRAG: Good hybrid, but unstable

2. **Neo4j + Weaviate is the optimal combination**
   - Clear separation of concerns
   - Both production-ready and stable
   - Excellent performance for respective use cases
   - Manageable complexity

3. **LightRAG should be deprecated**
   - Too unstable for production
   - Better alternatives available
   - Adds unnecessary complexity
   - Limited scalability

4. **Complexity is unavoidable but manageable**
   - Dual infrastructure is necessary
   - Clear separation reduces cognitive load
   - Both systems have excellent documentation
   - Strong community support

### Recommended Action Plan

**Immediate (Week 1):**
- Keep current Neo4j + LightRAG for now
- Validate Weaviate infrastructure (✅ Complete)
- Test Weaviate with real data

**Short-term (Month 1):**
- Migrate semantic search to Weaviate
- Keep Neo4j for graph operations
- Update KG MCP to use both systems

**Medium-term (Month 2):**
- Deprecate LightRAG
- Remove LightRAG infrastructure
- Document new architecture

**Long-term (Month 3+):**
- Optimize Neo4j + Weaviate integration
- Add caching layer
- Implement data synchronization
- Monitor performance metrics

---

## Appendix: Quick Reference

### System Selection Guide

| Requirement | Best System | Alternative |
|-------------|-------------|-------------|
| Graph traversal | Neo4j | Weaviate (limited) |
| Vector search | Weaviate | Neo4j (slow) |
| Hybrid search | Weaviate | LightRAG (unstable) |
| Graph algorithms | Neo4j | None |
| RAG integration | LightRAG | Weaviate (manual) |
| Stability | Neo4j, Weaviate | LightRAG |
| Scalability | Weaviate | Neo4j (Enterprise) |
| Learning curve | LightRAG | Weaviate |

### Query Examples

**Neo4j (Graph Traversal)**
```cypher
// Find circular dependencies
MATCH (a)-[:DEPENDS_ON*]->(a)
RETURN a.name, length(path) as depth
ORDER BY depth DESC
LIMIT 10
```

**Weaviate (Vector Search)**
```graphql
{
  Get {
    CodeEntity(
      nearVector: {
        vector: $query_vector,
        distance: 0.5
      }
      limit: 10
    ) {
      name
      _additional {
        distance
      }
    }
  }
}
```

**LightRAG (Hybrid Search)**
```python
result = client.query(
    query="Find circular dependencies in code",
    mode="hybrid",
    top_k=10
)
```
