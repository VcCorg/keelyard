# Multi-Provider Support - Neo4j and LightRAG

## Overview

The MCP server now supports **both Neo4j and LightRAG simultaneously**. Users can choose which provider to use for each operation via the `provider` parameter.

## Key Changes

### Before (Single Provider)
```json
{
  "status": "healthy",
  "provider": "neo4j",  // Only one provider active
  "version": "0.1.0"
}
```

### After (Multi-Provider)
```json
{
  "status": "healthy",
  "providers": {
    "neo4j": true,      // Both available!
    "lightrag": true
  },
  "version": "0.1.0"
}
```

## Architecture

### Configuration
Both providers are configured via environment variables:

```yaml
# docker-compose.yml
environment:
  # Neo4j Configuration
  - NEO4J_URI=bolt://keel-neo4j:7687
  - NEO4J_USER=neo4j
  - NEO4J_PASSWORD=password
  
  # LightRAG Configuration
  - LIGHTRAG_URL=http://keel-lightrag:8001
```

### Provider Detection
The server automatically detects which providers are available:

```python
class KGMCPServer:
    def __init__(self):
        self.neo4j_available = self._check_neo4j_available()
        self.lightrag_available = self._check_lightrag_available()
```

## Using Multiple Providers

### MCP Tool Schema

All tools now have a `provider` parameter:

```json
{
  "name": "kg_query",
  "inputSchema": {
    "properties": {
      "query": {"type": "string"},
      "provider": {
        "type": "string",
        "enum": ["neo4j", "lightrag"],
        "default": "neo4j",
        "description": "Which KG provider to use"
      }
    }
  }
}
```

### Example Usage

#### Query Neo4j
```bash
curl -X POST http://localhost:8125/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kg_query",
    "arguments": {
      "query": "Find all people",
      "provider": "neo4j",
      "format": "natural",
      "limit": 10
    }
  }'
```

**Response**:
```json
{
  "content": [{
    "type": "text",
    "text": {
      "provider": "neo4j",
      "query": "Find all people",
      "results": [...],
      "count": 10
    }
  }]
}
```

#### Query LightRAG
```bash
curl -X POST http://localhost:8125/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kg_query",
    "arguments": {
      "query": "Find all people",
      "provider": "lightrag",
      "format": "natural",
      "limit": 10
    }
  }'
```

**Response**:
```json
{
  "content": [{
    "type": "text",
    "text": {
      "provider": "lightrag",
      "query": "Find all people",
      "results": [...],
      "count": 10
    }
  }]
}
```

### From IDE (Claude Desktop, Windsurf)

Users can specify the provider in natural language:

**Neo4j**:
- "Query my Neo4j knowledge graph for all people"
- "Search Neo4j for machine learning topics"

**LightRAG**:
- "Query my LightRAG knowledge graph for all people"
- "Search LightRAG for machine learning topics"

The AI assistant will use the `provider` parameter accordingly.

## Provider-Specific Features

### Neo4j
- ✅ Cypher queries
- ✅ Semantic search (with embeddings)
- ✅ Exact text search
- ✅ Graph statistics
- ✅ Relationship traversal
- ✅ Persona filtering (developer/business)

### LightRAG
- ✅ Natural language queries
- ✅ Hybrid search
- ✅ Graph statistics
- ❌ Cypher queries (not supported)
- ❌ Persona filtering (not applicable)

## Status Endpoints

### Health Check
```bash
curl http://localhost:8125/health
```

**Response**:
```json
{
  "status": "healthy",
  "providers": {
    "neo4j": true,
    "lightrag": true
  },
  "version": "0.1.0"
}
```

### Detailed Status
```bash
curl http://localhost:8125/status
```

**Response**:
```json
{
  "status": "running",
  "providers": {
    "providers": {
      "neo4j": {
        "available": true,
        "uri": "bolt://keel-neo4j:7687"
      },
      "lightrag": {
        "available": true,
        "url": "http://keel-lightrag:8001"
      }
    }
  },
  "mcp_version": "2024-11-05",
  "server_version": "0.1.0"
}
```

## Error Handling

### Provider Not Configured

If a provider is not configured and you try to use it:

```bash
curl -X POST http://localhost:8125/mcp/tools/call \
  -d '{"name":"kg_query","arguments":{"query":"test","provider":"neo4j"}}'
```

**Response** (if Neo4j not configured):
```json
{
  "content": [{
    "type": "text",
    "text": "Error: Neo4j is not configured. Please set NEO4J_URI environment variable."
  }],
  "isError": true
}
```

### Provider-Specific Operations

If you try to use Cypher with LightRAG:

```bash
curl -X POST http://localhost:8125/mcp/tools/call \
  -d '{"name":"kg_query","arguments":{"query":"MATCH (n) RETURN n","provider":"lightrag","format":"cypher"}}'
```

The query will fail gracefully with an appropriate error message.

## Configuration Examples

### Both Providers
```yaml
# docker-compose.yml
environment:
  - NEO4J_URI=bolt://keel-neo4j:7687
  - NEO4J_USER=neo4j
  - NEO4J_PASSWORD=password
  - LIGHTRAG_URL=http://keel-lightrag:8001
```

**Result**: Both providers available

### Neo4j Only
```yaml
environment:
  - NEO4J_URI=bolt://keel-neo4j:7687
  - NEO4J_USER=neo4j
  - NEO4J_PASSWORD=password
  # LIGHTRAG_URL not set
```

**Result**: Only Neo4j available

### LightRAG Only
```yaml
environment:
  # NEO4J_URI not set
  - LIGHTRAG_URL=http://keel-lightrag:8001
```

**Result**: Only LightRAG available

## Migration from Single Provider

### Old Approach (Deprecated)
```yaml
environment:
  - KG_PROVIDER=neo4j  # ❌ No longer used
```

### New Approach
```yaml
environment:
  # Configure both (or just one)
  - NEO4J_URI=bolt://keel-neo4j:7687
  - LIGHTRAG_URL=http://keel-lightrag:8001
```

**No breaking changes**: Existing deployments will continue to work. The `KG_PROVIDER` environment variable is ignored.

## Benefits

### 1. **Flexibility**
- Use Neo4j for structured queries
- Use LightRAG for natural language
- Switch between providers per query

### 2. **Comparison**
- Query both providers with same input
- Compare results
- Choose best provider for use case

### 3. **Redundancy**
- If one provider is down, use the other
- Graceful degradation

### 4. **Experimentation**
- Test different providers
- Evaluate performance
- Choose optimal solution

## Best Practices

### 1. **Default to Neo4j**
The `provider` parameter defaults to `neo4j` for backward compatibility.

### 2. **Use Appropriate Provider**
- **Neo4j**: Structured data, complex relationships, Cypher queries
- **LightRAG**: Unstructured data, natural language, hybrid search

### 3. **Configure Both**
Even if you primarily use one provider, configure both for flexibility.

### 4. **Monitor Availability**
Check `/health` endpoint to see which providers are available.

## Testing

### Test Both Providers
```bash
# Test Neo4j
curl -X POST http://localhost:8125/mcp/tools/call \
  -d '{"name":"kg_query","arguments":{"query":"test","provider":"neo4j"}}'

# Test LightRAG
curl -X POST http://localhost:8125/mcp/tools/call \
  -d '{"name":"kg_query","arguments":{"query":"test","provider":"lightrag"}}'
```

### Test Provider Detection
```bash
# Should show both as true
curl http://localhost:8125/health
```

### Test Error Handling
```bash
# Stop Neo4j
docker stop keel-neo4j

# Try to query Neo4j (should fail gracefully)
curl -X POST http://localhost:8125/mcp/tools/call \
  -d '{"name":"kg_query","arguments":{"query":"test","provider":"neo4j"}}'

# Query LightRAG (should still work)
curl -X POST http://localhost:8125/mcp/tools/call \
  -d '{"name":"kg_query","arguments":{"query":"test","provider":"lightrag"}}'
```

## Summary

The MCP server now supports **both Neo4j and LightRAG simultaneously**, giving users the flexibility to choose the best provider for each operation. This is achieved through:

- ✅ **Provider parameter** in all MCP tools
- ✅ **Automatic provider detection**
- ✅ **Graceful error handling**
- ✅ **Backward compatibility**
- ✅ **No breaking changes**

Users can now leverage the strengths of both providers in a single MCP server!

---

**Implementation Date**: November 23, 2025
**Status**: ✅ Complete
**Breaking Changes**: None
**Backward Compatible**: Yes
