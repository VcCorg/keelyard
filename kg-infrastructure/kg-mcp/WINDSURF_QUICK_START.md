# Windsurf MCP Quick Start

## 🚀 3-Step Setup

### Step 1: Copy Configuration

Copy this JSON to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "keel-kg": {
      "url": "http://localhost:8125",
      "transport": "http",
      "disabled": false,
      "timeout": 30000
    }
  }
}
```

**Or use the pre-made file:**
```bash
cat windsurf-mcp-config.json
```

### Step 2: Restart Windsurf

Close and reopen Windsurf IDE to load the new MCP server.

### Step 3: Test It!

In Windsurf, try these commands:

```
Show me the Neo4j schema from resources
```

```
Use kg_query to find all people in the knowledge graph
```

```
Use kg_stats with provider=neo4j to show graph statistics
```

## 📚 Available Tools

| Tool | Description | Example |
|------|-------------|---------|
| `kg_query` | Query with natural language or Cypher | "Find all developers" |
| `kg_search` | Semantic or exact search | "Search for machine learning" |
| `kg_stats` | Get graph statistics | "Show me graph stats" |
| `kg_ingest` | Ingest data (placeholder) | "Ingest data from file" |

## 🗂️ Available Resources

| URI | Description |
|-----|-------------|
| `kg://schema/neo4j` | Neo4j graph schema (6 node types, 6 relationships) |
| `kg://schema/lightrag` | LightRAG schema and capabilities |
| `kg://template/person` | Person entity template with examples |
| `kg://template/organization` | Organization entity template |
| `kg://queries/common` | 10 common Cypher queries |

## 🎯 Multi-Provider Usage

**Query Neo4j:**
```
Use kg_query with provider=neo4j to find all organizations
```

**Query LightRAG:**
```
Use kg_query with provider=lightrag to search for AI concepts
```

## 🔍 Example Queries

### Natural Language Queries
```
Find all people who work in technology
Show me organizations in San Francisco
What are the most common relationships in the graph?
```

### Cypher Queries (Neo4j only)
```
Use kg_query with format=cypher: MATCH (p:Person) RETURN p LIMIT 10
```

### Search Operations
```
Search the knowledge graph for "artificial intelligence"
Find entities related to "machine learning"
```

### Resource Access
```
Show me the Neo4j schema
What entity templates are available?
Show me common Cypher queries
```

## ✅ Verification

Check if MCP server is working:

```bash
# From kg-mcp-infrastructure directory
./test-mcp-windsurf.sh
```

Expected output: All 7 tests should pass ✓

## 🐛 Troubleshooting

### Server Not Running
```bash
cd kg-mcp-infrastructure
make status
make start  # if not running
```

### Can't Connect
```bash
# Check server health
curl http://localhost:8125/health

# Check server logs
make logs
```

### Tools Not Showing
1. Verify JSON syntax in `mcp_config.json`
2. Restart Windsurf completely
3. Check server is running on port 8125

## 📖 Full Documentation

- **Setup Guide**: `WINDSURF_SETUP.md`
- **MCP Resources**: `MCP_RESOURCES.md` (coming soon)
- **Phase 3 Plan**: `PHASE3_PLAN.md`
- **Quick Start**: `QUICKSTART.md`

## 🎉 You're Ready!

Your Windsurf IDE can now:
- ✅ Query Neo4j and LightRAG knowledge graphs
- ✅ Access graph schemas and templates
- ✅ Use pre-configured Cypher queries
- ✅ Switch between providers dynamically

**Happy coding with KEEL KG MCP! 🚀**
