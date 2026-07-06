# Knowledge Graph Provider Support

## Overview

Agentic CLI supports two knowledge graph providers: **Neo4j** and **LightRAG**. This document outlines which commands work with each provider.

## Provider Comparison

| Command | Neo4j | LightRAG | Notes |
|---------|-------|----------|-------|
| `keel kg init` | ✅ | ✅ | Configure provider settings |
| `keel kg config` | ✅ | ✅ | View/manage configuration |
| `keel kg check` | ✅ | ⚠️ | Neo4j-focused validation |
| `keel kg ingest` | ✅ | ✅ | Full support for both |
| `keel kg query` | ✅ | ✅ | Different query modes |
| `keel kg search` | ✅ | ✅ | Semantic search |
| `keel kg stats` | ✅ | ✅ | Provider-specific stats |
| `keel kg tool` | ✅ | ❌ | Neo4j only |
| `keel kg visualize` | ✅ | ❌ | Neo4j only |

## Command Details

### ✅ Fully Supported (Both Providers)

#### `keel kg init`
Configure your knowledge graph provider.

**Neo4j:**
```bash
`agent kg init --provider neo4j \
  --uri bolt://localhost:7687 \
  --username neo4j \
  --password password
```

**LightRAG:**
```bash
`agent kg init --provider lightrag \
  --lightrag-url http://localhost:8001
```

#### `keel kg config`
View or reset configuration.

```bash
# Show current configuration
`agent kg config --show

# Reset configuration
`agent kg config --reset
```

Works identically for both providers.

#### `keel kg ingest`
Ingest documents into the knowledge graph.

**Neo4j:**
```bash
# With entity extraction and relationship building
`agent kg ingest --path /data/documents \
  --extract-entities \
  --build-relationships
```

**LightRAG:**
```bash
# Automatic entity and relationship extraction
`agent kg ingest --path /data/documents
```

Both support:
- Single files
- Directories (recursive/non-recursive)
- PDF, text, CSV, JSON files
- Data source integration (`--source`)

#### `keel kg query`
Query the knowledge graph.

**Neo4j:**
```bash
# Natural language query (converted to Cypher)
`agent kg query "Find all people who work at Google"

# Direct Cypher query
`agent kg query "MATCH (n:Person) RETURN n LIMIT 10" --format cypher
```

**LightRAG:**
```bash
# Natural language query with different modes
`agent kg query "What are the main topics?" --mode hybrid
`agent kg query "Find specific information" --mode local
`agent kg query "Get overview" --mode global
```

**LightRAG Modes:**
- `naive` - Simple retrieval
- `local` - Local context search
- `global` - Global knowledge search
- `hybrid` - Combined approach (default)

#### `keel kg search`
Semantic search in the knowledge graph.

**Neo4j:**
```bash
# Semantic search using embeddings
`agent kg search "artificial intelligence" --semantic

# Exact text matching
`agent kg search "AI" --exact
```

**LightRAG:**
```bash
# Semantic search
`agent kg search "machine learning concepts"
```

#### `keel kg stats`
Display knowledge graph statistics.

**Neo4j Output:**
```
Knowledge Graph Statistics (Neo4j)
┌──────────────────────┬───────┐
│ Metric               │ Count │
├──────────────────────┼───────┤
│ Total Nodes          │ 6759  │
│ Total Relationships  │ 6461  │
│ Node Types           │ 8     │
│ Relationship Types   │ 12    │
└──────────────────────┴───────┘
```

**LightRAG Output:**
```
Knowledge Graph Statistics (LightRAG)
┌──────────────┬───────────────────┐
│ Metric       │ Value             │
├──────────────┼───────────────────┤
│ Working Dir  │ /data/lightrag    │
│ Initialized  │ True              │
│ Vector Store │ nano-vectordb     │
│ Graph Store  │ networkx          │
│ Data Files   │ 2                 │
└──────────────┴───────────────────┘
```

### ⚠️ Partial Support

#### `keel kg check`
Validates prerequisites and availability.

Currently focused on Neo4j validation. Shows helpful message for LightRAG users to use infrastructure validation instead:

```bash
# For Neo4j
`agent kg check

# For LightRAG, use infrastructure validation
cd lightrag-infrastructure
make validate
```

### ❌ Neo4j Only

#### `keel kg tool`
Generate ADK tool classes for knowledge graph operations.

**Why Neo4j only?**
- Generates Python code with Cypher queries
- Requires Neo4j-specific client operations
- LightRAG uses REST API (different pattern)

**Usage:**
```bash
# Switch to Neo4j first
`agent kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password

# Generate tool
`agent kg tool --name knowledge_graph --output tools/kg_tool.py
```

**Workaround for LightRAG:**
Use the LightRAG client directly in your code:
```python
from agentic_cli.kg.lightrag_client import LightRAGClient

client = LightRAGClient(base_url="http://localhost:8001")
result = client.query("Your query here")
```

#### `keel kg visualize`
Generate interactive graph visualization.

**Why Neo4j only?**
- Uses PyVis to visualize graph structure
- Requires graph traversal and node/relationship data
- LightRAG uses different internal representation

**Usage:**
```bash
# Switch to Neo4j first
`agent kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password

# Create visualization
`agent kg visualize --output graph.html
```

**Error Message:**
If you try to visualize with LightRAG:
```
⚠ Visualization is only supported for Neo4j provider
  Current provider: lightrag

To use visualization:
  1. Switch to Neo4j: agent kg init --provider neo4j ...
  2. Ingest your data: agent kg ingest --path /your/data
  3. Run visualization: agent kg visualize
```

## Switching Between Providers

You can easily switch between providers without losing data:

```bash
# Currently using LightRAG
`agent kg stats
# Shows LightRAG stats

# Switch to Neo4j
`agent kg init --provider neo4j \
  --uri bolt://localhost:7687 \
  --username neo4j \
  --password password

# Now using Neo4j
`agent kg stats
# Shows Neo4j stats

# Switch back to LightRAG
`agent kg init --provider lightrag \
  --lightrag-url http://localhost:8001
```

**Note:** Each provider maintains its own data store. Switching providers doesn't migrate data.

## Best Practices

### Choose Neo4j When You Need:
- ✅ Complex graph queries (Cypher)
- ✅ Graph algorithms (shortest path, centrality, etc.)
- ✅ Visual graph exploration
- ✅ ADK tool generation
- ✅ Advanced relationship modeling
- ✅ APOC plugin functionality

### Choose LightRAG When You Need:
- ✅ Fast document ingestion
- ✅ Simple semantic search
- ✅ RAG (Retrieval-Augmented Generation)
- ✅ Lightweight setup
- ✅ Quick prototyping
- ✅ Hybrid search modes

## Migration Between Providers

### From LightRAG to Neo4j

1. **Export data from LightRAG** (if needed)
2. **Start Neo4j infrastructure**
   ```bash
   cd neo4j-infrastructure
   make start
   make validate
   ```
3. **Configure Agentic CLI**
   ```bash
   agent kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password
   ```
4. **Re-ingest data**
   ```bash
   agent kg ingest --path /your/data --extract-entities --build-relationships
   ```

### From Neo4j to LightRAG

1. **Start LightRAG infrastructure**
   ```bash
   cd lightrag-infrastructure
   make start
   make validate
   ```
2. **Configure Agentic CLI**
   ```bash
   agent kg init --provider lightrag --lightrag-url http://localhost:8001
   ```
3. **Re-ingest data**
   ```bash
   agent kg ingest --path /your/data
   ```

## Troubleshooting

### Command Not Working with Current Provider

**Error:**
```
✗ This command only supports Neo4j provider
  Current provider: lightrag
```

**Solution:**
1. Check current provider: `keel kg config --show`
2. Switch provider if needed: `keel kg init --provider neo4j ...`
3. Or use provider-specific infrastructure commands

### Provider Not Configured

**Error:**
```
✗ Unknown provider: none
Run 'agent kg init' to configure a provider.
```

**Solution:**
```bash
# Configure Neo4j
`agent kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password

# Or configure LightRAG
`agent kg init --provider lightrag --lightrag-url http://localhost:8001
```

### Connection Failed

**Neo4j:**
```bash
# Validate infrastructure
cd neo4j-infrastructure
make validate

# Check configuration
`agent kg config --show
```

**LightRAG:**
```bash
# Validate infrastructure
cd lightrag-infrastructure
make validate

# Check configuration
`agent kg config --show
```

## Future Enhancements

Planned improvements for provider support:

- [ ] LightRAG visualization support
- [ ] LightRAG tool generation
- [ ] Data export/import between providers
- [ ] Unified query language
- [ ] Provider-agnostic abstractions
- [ ] Multi-provider support (use both simultaneously)

## Summary

| Feature | Neo4j | LightRAG |
|---------|-------|----------|
| **Setup Complexity** | Medium | Low |
| **Query Language** | Cypher + NL | Natural Language |
| **Search Modes** | Semantic + Exact | Semantic + Hybrid |
| **Visualization** | ✅ Interactive | ❌ Not yet |
| **Tool Generation** | ✅ Yes | ❌ Not yet |
| **Performance** | Excellent | Very Fast |
| **Use Case** | Complex graphs | Fast RAG |

Choose the provider that best fits your use case, and remember you can always switch between them!
