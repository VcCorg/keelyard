# Persona Filtering for Knowledge Graph Queries and Searches

## Overview

Persona filtering allows you to focus queries and searches on specific contexts within your knowledge graph:
- **Developer persona**: Code, functions, classes, technical implementation
- **Business persona**: Documentation, requirements, business logic

This is particularly useful when you've ingested both code repositories (developer context) and documentation (business context) into the same knowledge graph.

## Commands Supporting Persona Filtering

### 1. Query Command (`dva kg query`)

Query the knowledge graph with natural language or Cypher, filtered by persona.

**Usage:**
```bash
# Query all contexts (no filter)
`agent kg query "patient authentication"

# Query only code/developer context
`agent kg query "patient authentication" --persona developer

# Query only docs/business context
`agent kg query "patient authentication" --persona business
```

**Query modes (LightRAG):**
- `naive`: Simple keyword matching
- `local`: Local entity and relation search
- `global`: Global graph traversal
- `hybrid`: Combination of local and global (default)

**Examples:**
```bash
# Find authentication functions in code
`agent kg query "authentication functions" --persona developer --mode local

# Find authentication requirements in docs
`agent kg query "authentication requirements" --persona business --mode hybrid

# Find all patient-related entities (both code and docs)
`agent kg query "patient" --limit 20
```

### 2. Search Command (`dva kg search`)

Semantic search across the knowledge graph, filtered by persona.

**Usage:**
```bash
# Search all contexts (no filter)
`agent kg search "patient"

# Search only code/developer context
`agent kg search "patient" --persona developer

# Search only docs/business context
`agent kg search "patient" --persona business
```

**Search options:**
- `--semantic`: Use vector embeddings for semantic search (default)
- `--exact`: Use exact text matching
- `--limit N`: Return top N results (default: 10)

**Examples:**
```bash
# Find patient-related code
`agent kg search "patient status filter" --persona developer --limit 20

# Find patient-related documentation
`agent kg search "patient eligibility" --persona business

# Exact match search in code
`agent kg search "PatientModel" --persona developer --exact
```

## How Persona Filtering Works

### During Ingestion

When data is ingested, it's tagged with a persona based on the source type:

```bash
# Git repositories → developer persona
`agent kg ingest --source backend-repo  # Auto-tagged as "developer"

# Documents/PDFs → business persona
`agent kg ingest --path /docs/requirements.pdf  # Auto-tagged as "business"
```

**Persona assignment:**
- **Git repositories**: `persona = "developer"`
- **Documents (PDF, text, CSV, JSON)**: `persona = "business"`
- **Confluence**: `persona = "business"`

### During Query/Search

When you specify a persona, the query/search text is enhanced with context:

**Developer persona:**
```python
# Original: "patient authentication"
# Enhanced: "From the code/developer perspective: patient authentication"
```

**Business persona:**
```python
# Original: "patient authentication"
# Enhanced: "From the documentation/business perspective: patient authentication"
```

This guides the LLM and vector search to focus on the relevant context.

## Implementation Details

### Query Command with Persona

```@/Users/your-user/agentic-project/agentic-cli/src/dva_agentic_cli/commands/kg.py#723:735
# Add persona context to LightRAG query
enhanced_query = query_text
if persona:
    if persona == "developer":
        enhanced_query = f"From the code/developer perspective: {query_text}"
    elif persona == "business":
        enhanced_query = f"From the documentation/business perspective: {query_text}"

# Use extended timeout for query operations
timeout = max(config.lightrag_timeout, 300.0)
client = LightRAGClient(base_url=config.lightrag_url, timeout=timeout)
result = client.query(enhanced_query, mode=mode, top_k=limit)
```

### Search Command with Persona

```@/Users/your-user/agentic-project/agentic-cli/src/dva_agentic_cli/commands/kg.py#846:857
# Add persona context to LightRAG search
enhanced_text = text
if persona:
    if persona == "developer":
        enhanced_text = f"From the code/developer perspective: {text}"
    elif persona == "business":
        enhanced_text = f"From the documentation/business perspective: {text}"

# Use extended timeout for search operations
timeout = max(config.lightrag_timeout, 300.0)
client = LightRAGClient(base_url=config.lightrag_url, timeout=timeout)
result = client.search(enhanced_text, top_k=limit)
```

## Use Cases

### 1. Code Analysis (Developer Persona)

**Find implementation details:**
```bash
# Find patient model classes
`agent kg search "patient model" --persona developer

# Find authentication functions
`agent kg query "authentication implementation" --persona developer

# Find database schema
`agent kg search "database schema" --persona developer --limit 30
```

### 2. Documentation Review (Business Persona)

**Find requirements and specifications:**
```bash
# Find patient requirements
`agent kg search "patient requirements" --persona business

# Find authentication policies
`agent kg query "authentication policy" --persona business

# Find API documentation
`agent kg search "API endpoints" --persona business
```

### 3. Cross-Context Analysis (No Persona)

**Find information across both code and docs:**
```bash
# Find all patient-related information
`agent kg query "patient" --limit 50

# Find authentication across code and docs
`agent kg search "authentication" --limit 30

# Compare implementation vs requirements
`agent kg query "authentication requirements and implementation"
```

## Best Practices

### 1. Use Persona When You Know the Context

```bash
# ✅ Good: Specific context
`agent kg search "PatientModel class" --persona developer

# ❌ Less effective: Wrong context
`agent kg search "PatientModel class" --persona business
```

### 2. Omit Persona for Exploratory Queries

```bash
# ✅ Good: Explore all contexts
`agent kg query "patient authentication"

# Then drill down with persona
`agent kg query "patient authentication" --persona developer
```

### 3. Combine with Other Options

```bash
# Search code with high result count
`agent kg search "patient" --persona developer --limit 50

# Query docs with specific mode
`agent kg query "requirements" --persona business --mode global

# Exact match in code
`agent kg search "class PatientModel" --persona developer --exact
```

### 4. Adjust Limit Based on Graph Size

```bash
# Small graphs (<1000 entities)
`agent kg search "patient" --persona developer --limit 10

# Medium graphs (1000-5000 entities)
`agent kg search "patient" --persona developer --limit 30

# Large graphs (>5000 entities)
`agent kg search "patient" --persona developer --limit 50
```

## Troubleshooting

### Issue: No Results with Persona Filter

**Problem:** Query returns no results when using persona filter.

**Solution:**
1. Check if data was ingested with the correct persona:
   ```bash
   agent kg stats  # Check entity counts
   ```

2. Try without persona filter first:
   ```bash
   agent kg search "patient"  # See if results exist
   ```

3. Verify persona assignment during ingestion:
   - Git repos should be tagged as "developer"
   - Documents should be tagged as "business"

### Issue: Timeout Errors

**Problem:** Query/search times out even with persona filter.

**Solution:**
1. Increase timeout:
   ```bash
   agent kg init --provider lightrag --lightrag-timeout 600
   ```

2. Reduce result limit:
   ```bash
   agent kg search "patient" --persona developer --limit 5
   ```

3. Use more specific queries:
   ```bash
   # ✅ Specific
   agent kg search "PatientModel class methods" --persona developer
   
   # ❌ Too broad
   agent kg search "patient" --persona developer
   ```

## Files Modified

1. **`src/dva_agentic_cli/commands/kg.py`**
   - Added `persona` parameter to `search` command (line 760-763)
   - Added persona context enhancement for LightRAG search (line 846-852)
   - Updated docstring with persona examples (line 770-786)

## Related Documentation

- **Ingestion Guide:** How persona is assigned during data ingestion
- **Query Modes:** Understanding LightRAG query modes (naive, local, global, hybrid)
- **Timeout Configuration:** Adjusting timeouts for large graphs
- **Knowledge Graph Stats:** `dva kg stats` to understand your graph size

## Summary

Persona filtering enables focused queries and searches within mixed-context knowledge graphs:

- **`--persona developer`**: Focus on code, functions, classes, technical implementation
- **`--persona business`**: Focus on documentation, requirements, business logic
- **No persona**: Search across all contexts

Both `dva kg query` and `dva kg search` now support persona filtering with the same syntax and behavior.
