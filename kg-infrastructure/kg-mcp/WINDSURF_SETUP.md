# Windsurf IDE MCP Configuration

This guide shows how to configure Windsurf IDE to connect to the KEEL Knowledge Graph MCP server.

## Prerequisites

- Windsurf IDE installed
- KEEL KG MCP server running (`make start` in kg-mcp-infrastructure/)
- Server accessible at `http://localhost:8125`

## Configuration Steps

### 1. Locate Windsurf MCP Config

The Windsurf MCP configuration file is located at:
```
~/.codeium/windsurf/mcp_config.json
```

### 2. Add KEEL KG MCP Server

Open `~/.codeium/windsurf/mcp_config.json` and add the following configuration to the `mcpServers` object:

```json
{
  "mcpServers": {
    "keel-kg": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", "@-",
        "http://localhost:8125/mcp"
      ],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

**Note**: This uses HTTP transport. For better performance, you can use stdio transport (coming in Phase 3 Part 3).

### 3. Alternative: HTTP SSE Configuration

For Server-Sent Events (streaming), use this configuration:

```json
{
  "mcpServers": {
    "keel-kg": {
      "url": "http://localhost:8125",
      "transport": "http",
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

### 4. Complete Example Configuration

Here's a complete example with the KEEL KG server:

```json
{
  "mcpServers": {
    "keel-kg": {
      "url": "http://localhost:8125",
      "transport": "http",
      "disabled": false,
      "alwaysAllow": [],
      "metadata": {
        "name": "KEEL Knowledge Graph",
        "description": "Access Neo4j and LightRAG knowledge graphs",
        "version": "0.1.0"
      }
    }
  }
}
```

## Verification

### 1. Restart Windsurf

After updating the config, restart Windsurf IDE to load the new MCP server.

### 2. Check MCP Server Status

In Windsurf, you should see the KEEL KG MCP server in the MCP servers list.

### 3. Test MCP Tools

Try using the MCP tools in Windsurf:

**Query Knowledge Graph:**
```
Use the kg_query tool to find all people in the knowledge graph
```

**Search Knowledge Graph:**
```
Use the kg_search tool to search for "machine learning"
```

**Get Graph Statistics:**
```
Use the kg_stats tool to show me the knowledge graph statistics
```

**Access Resources:**
```
Show me the Neo4j schema from the resources
```

## Available MCP Features

### Tools (4)
- `kg_query` - Query using natural language or Cypher
- `kg_search` - Semantic or exact search
- `kg_stats` - Graph statistics
- `kg_ingest` - Ingest data (placeholder)

### Resources (5)
- `kg://schema/neo4j` - Neo4j graph schema
- `kg://schema/lightrag` - LightRAG schema
- `kg://template/person` - Person entity template
- `kg://template/organization` - Organization entity template
- `kg://queries/common` - Common Cypher queries

### Providers
- **Neo4j**: Graph database backend
- **LightRAG**: RAG-based knowledge graph

## Multi-Provider Usage

You can specify which provider to use for each operation:

**Query Neo4j:**
```
Use kg_query with provider=neo4j to find all developers
```

**Query LightRAG:**
```
Use kg_query with provider=lightrag to find information about AI
```

## Troubleshooting

### Server Not Found

**Problem**: Windsurf can't connect to MCP server

**Solution**:
1. Check server is running: `make status`
2. Check server health: `make health`
3. Verify port 8125 is accessible: `curl http://localhost:8125/health`

### Tools Not Appearing

**Problem**: MCP tools don't show up in Windsurf

**Solution**:
1. Restart Windsurf IDE
2. Check MCP config syntax is valid JSON
3. Check server logs: `make logs`

### Connection Timeout

**Problem**: Requests timeout

**Solution**:
1. Increase timeout in config:
```json
{
  "mcpServers": {
    "keel-kg": {
      "url": "http://localhost:8125",
      "transport": "http",
      "timeout": 30000,
      "disabled": false
    }
  }
}
```

### Provider Not Available

**Problem**: "Provider unavailable" error

**Solution**:
1. Check which providers are configured:
```bash
curl http://localhost:8125/status | jq '.providers'
```

2. Ensure Neo4j or LightRAG is running:
```bash
# For Neo4j
cd ../neo4j-infrastructure && make status

# For LightRAG
cd ../lightrag-docker && docker-compose ps
```

## Advanced Configuration

### Custom Environment Variables

If you need custom environment variables for the MCP server:

```json
{
  "mcpServers": {
    "keel-kg": {
      "url": "http://localhost:8125",
      "transport": "http",
      "env": {
        "NEO4J_URI": "bolt://custom-neo4j:7687",
        "LIGHTRAG_URL": "http://custom-lightrag:8001"
      },
      "disabled": false
    }
  }
}
```

### Multiple MCP Servers

You can configure multiple MCP servers:

```json
{
  "mcpServers": {
    "keel-kg": {
      "url": "http://localhost:8125",
      "transport": "http",
      "disabled": false
    },
    "other-mcp-server": {
      "url": "http://localhost:9000",
      "transport": "http",
      "disabled": false
    }
  }
}
```

## Security Considerations

### Local Development

For local development, the current HTTP configuration is fine.

### Production

For production deployments:

1. **Use HTTPS**: Configure TLS/SSL
2. **Add Authentication**: Implement API keys or OAuth
3. **Network Isolation**: Use VPN or private networks
4. **Rate Limiting**: Add rate limits to prevent abuse

## Next Steps

1. ✅ Configure Windsurf MCP
2. ✅ Test MCP tools
3. ✅ Access MCP resources
4. 🔜 Try multi-provider queries
5. 🔜 Explore advanced features

## Support

For issues or questions:
- Check server logs: `make logs`
- Check server status: `make status`
- Review documentation: `README.md`, `QUICKSTART.md`

---

**Version**: 0.1.0  
**Last Updated**: 2024-11-24  
**Status**: Ready for use ✅
