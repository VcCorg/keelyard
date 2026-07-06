# KEEL KG MCP Server - Quick Start Guide

Get your Knowledge Graph MCP server running in 5 minutes!

## Prerequisites

- ✅ Docker installed and running
- ✅ Agentic CLI configured (`keel kg init`)
- ✅ Agentic CLI located at `../agentic-cli` (relative to this directory)

## Option 1: MCP Server Only (Fastest)

**Use this if you already have Neo4j or LightRAG running.**

```bash
cd kg-mcp-infrastructure

# 1. Create config
cp .env.example .env

# 2. Edit .env (set KG_PROVIDER, NEO4J_URI, etc.)
nano .env

# 3. Start MCP server
./setup.sh
# Choose option 1

# 4. Verify
make health
```

**Done!** MCP server is running on `http://localhost:8125`

## Option 2: Full Stack (Everything)

**Use this to start MCP + Neo4j + LightRAG together.**

```bash
cd kg-mcp-infrastructure

# 1. Create config
cp .env.example .env

# 2. Edit .env with your API keys
nano .env

# 3. Start everything
./setup.sh
# Choose option 2

# 4. Wait ~30 seconds for services to start

# 5. Verify
make health
make test
```

**Done!** Full stack is running:
- MCP Server: `http://localhost:8125`
- Neo4j: `http://localhost:7474`
- LightRAG: `http://localhost:8001`

## Configure Your IDE

### Claude Desktop

1. Open config file:
   ```bash
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. Add MCP server:
   ```json
   {
     "mcpServers": {
       "keel-kg": {
         "url": "http://localhost:8125/mcp",
         "transport": "http"
       }
     }
   }
   ```

3. Restart Claude Desktop

4. Test: Ask Claude "Query my knowledge graph for all people"

### Windsurf

1. Open Settings → MCP Servers

2. Add new server:
   - Name: `keel-kg`
   - URL: `http://localhost:8125/mcp`
   - Transport: `http`

3. Restart Windsurf

4. Test: Use MCP tools in chat

## Test MCP Tools

### From Command Line

```bash
# Query knowledge graph
curl -X POST http://localhost:8125/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kg_query",
    "arguments": {
      "query": "Find all people",
      "limit": 5
    }
  }'

# Search knowledge graph
curl -X POST http://localhost:8125/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kg_search",
    "arguments": {
      "text": "machine learning",
      "semantic": true
    }
  }'

# Get statistics
curl -X POST http://localhost:8125/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kg_stats",
    "arguments": {}
  }'
```

### From IDE

Once configured, you can use natural language:

**Claude Desktop**:
- "Query my knowledge graph for all engineers"
- "Search my KG for machine learning topics"
- "Show me KG statistics"

**Windsurf**:
- Use MCP tool palette
- Select `kg_query`, `kg_search`, or `kg_stats`

## Common Commands

```bash
# Check status
make status

# View logs
make logs

# Follow logs
make logs-follow

# Restart (after code changes)
make restart

# Stop
make stop

# Test endpoints
make test
```

## Development Tips

### Making Changes to KG Code

KG modules are **volume-mounted** from `../agentic-cli`, so changes are instant:

```bash
# 1. Edit KG code in CLI
cd ../agentic-cli/src/agentic_cli/kg
nano query.py  # Make your changes

# 2. Restart container (no rebuild!)
cd ../../kg-mcp-infrastructure
make restart

# 3. Changes are live!
make test
```

**No Docker rebuild needed!** Just restart the container.

## Troubleshooting

### MCP Server Not Starting

```bash
# Check logs
make logs

# Verify Docker network
docker network ls | grep keel-network

# Recreate network
docker network create keel-network
```

### Can't Connect to Neo4j

```bash
# Check Neo4j is running
curl http://localhost:7474

# Check from MCP container
docker exec keel-kg-mcp curl http://keel-neo4j:7474
```

### IDE Not Seeing Tools

1. Verify MCP server is healthy:
   ```bash
   make health
   ```

2. Check IDE MCP config has correct URL

3. Restart IDE

4. Check IDE logs for MCP errors

## Next Steps

1. **Ingest Data**:
   ```bash
   agent kg ingest --source my-dataset --extract-entities
   ```

2. **Query from IDE**:
   - Ask Claude to query your KG
   - Use natural language

3. **Explore**:
   - Try different queries
   - Search semantically
   - View statistics

## Need Help?

- 📖 [Full README](README.md)
- 🔧 [Troubleshooting Guide](README.md#troubleshooting)
- 📚 [KG Documentation](../agentic-cli/docs/KNOWLEDGE_GRAPH.md)

---

**That's it!** Your Knowledge Graph is now accessible via MCP protocol. 🚀
