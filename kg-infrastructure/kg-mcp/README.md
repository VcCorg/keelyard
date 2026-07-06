# KEEL Knowledge Graph MCP Server

Docker-based MCP (Model Context Protocol) server that exposes KEEL Knowledge Graph operations to IDEs and AI assistants.

## Overview

This MCP server provides a standardized interface for interacting with your Knowledge Graph (Neo4j or LightRAG) from IDEs like Claude Desktop, Windsurf, and other MCP-compatible tools.

### Features

- **Multi-Provider Support**: Works with both Neo4j and LightRAG backends
- **MCP Protocol**: Standard protocol for AI assistant integration
- **Docker-Based**: Isolated, reproducible environment
- **Easy Setup**: Automated setup scripts and Makefile commands
- **Health Monitoring**: Built-in health checks and status endpoints

### Architecture

```
IDE/AI Assistant (Claude Desktop, Windsurf, etc.)
    ↓ HTTP/SSE (localhost:8125)
MCP Server Container (keel-kg-mcp)
    ↓ Internal Docker Network
    ├─→ Neo4j Container (keel-neo4j:7687)
    └─→ LightRAG Container (keel-lightrag:8001)
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Neo4j or LightRAG running (or use full stack mode)
- Agentic CLI configured (`keel kg init`)

### Installation

1. **Clone and setup**:
   ```bash
   cd kg-mcp-infrastructure
   ./setup.sh
   ```

2. **Choose startup mode**:
   - **Option 1**: MCP only (assumes Neo4j/LightRAG already running)
   - **Option 2**: Full stack (starts everything)

3. **Verify**:
   ```bash
   make health
   make test
   ```

### Manual Setup

```bash
# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Create Docker network
docker network create keel-network

# Start MCP server only
make start

# OR start full stack
make start-full
```

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# KG Provider
KG_PROVIDER=neo4j  # or lightrag

# Neo4j Configuration
NEO4J_URI=bolt://keel-neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LightRAG Configuration
LIGHTRAG_URL=http://keel-lightrag:8001

# Vertex AI (for entity extraction)
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-flash

# MCP Server
MCP_PORT=8125
MCP_LOG_LEVEL=INFO
```

## Usage

### Management Commands

```bash
# Start/Stop
make start          # Start MCP server
make start-full     # Start full stack
make stop           # Stop MCP server
make stop-full      # Stop full stack
make restart        # Restart MCP server

# Monitoring
make status         # Show container status
make logs           # View logs
make logs-follow    # Follow logs
make health         # Check health

# Testing
make test           # Test MCP endpoints

# Cleanup
make clean          # Remove containers and images
```

### Available MCP Tools

The server exposes these tools via MCP protocol:

#### 1. `kg_query`
Query the knowledge graph using natural language or Cypher.

**Input**:
```json
{
  "query": "Find all people who work at Acme Corp",
  "format": "natural",  // or "cypher"
  "limit": 10,
  "persona": "developer"  // optional: "developer", "business"
}
```

**Example**:
```bash
curl -X POST http://localhost:8125/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kg_query",
    "arguments": {
      "query": "Find all people",
      "format": "natural",
      "limit": 5
    }
  }'
```

#### 2. `kg_search`
Search the knowledge graph semantically or by exact match.

**Input**:
```json
{
  "text": "machine learning",
  "semantic": true,
  "limit": 10
}
```

#### 3. `kg_stats`
Get knowledge graph statistics.

**Input**:
```json
{}
```

#### 4. `kg_ingest`
Ingest data from configured sources (coming soon).

**Input**:
```json
{
  "source": "my-dataset",
  "extract_entities": true,
  "build_relationships": true
}
```

## IDE Integration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### Windsurf

Add to Windsurf MCP configuration:

```json
{
  "mcp": {
    "servers": {
      "keel-kg": {
        "url": "http://localhost:8125/mcp",
        "transport": "http"
      }
    }
  }
}
```

### VS Code (with MCP extension)

```json
{
  "mcp.servers": [
    {
      "name": "keel-kg",
      "url": "http://localhost:8125/mcp",
      "transport": "http"
    }
  ]
}
```

## API Endpoints

### Health & Status

- `GET /health` - Health check
- `GET /status` - Detailed status

### MCP Protocol

- `POST /mcp/initialize` - MCP handshake
- `POST /mcp/tools/list` - List available tools
- `POST /mcp/tools/call` - Execute a tool

## Development

### Project Structure

```
kg-mcp-infrastructure/
├── docker-compose.yml          # MCP server only
├── docker-compose.full.yml     # Full stack
├── .env.example                # Configuration template
├── setup.sh                    # Setup script
├── Makefile                    # Management commands
├── README.md                   # This file
└── mcp-server/
    ├── Dockerfile
    ├── requirements.txt
    └── src/
        ├── mcp_server.py       # Main MCP server
        └── kg/                 # KG modules (mounted at runtime from ../agentic-cli)
            ├── query.py        # ↓ Volume mounted from CLI
            ├── search.py       # ↓ Changes reflected on restart
            ├── neo4j_client.py # ↓ No rebuild needed
            └── lightrag_client.py
```

**Note**: KG modules are **volume-mounted at runtime** from `../agentic-cli/src/agentic_cli/kg/`. 
This means:
- ✅ Code changes in CLI are immediately reflected after container restart
- ✅ No need to rebuild Docker image for KG module changes
- ✅ Single source of truth for KG code

### Development Workflow

#### Making Changes to KG Code

Since KG modules are volume-mounted from `agentic-cli`, changes are reflected immediately:

```bash
# 1. Edit KG code in CLI
cd ../agentic-cli/src/agentic_cli/kg
nano query.py  # Make your changes

# 2. Restart MCP container (no rebuild needed!)
cd ../kg-mcp-infrastructure
make restart

# 3. Test changes
make test
```

**No Docker rebuild required!** Just restart the container.

#### Making Changes to MCP Server Code

If you modify `mcp_server.py`, you need to rebuild:

```bash
# 1. Edit MCP server
nano mcp-server/src/mcp_server.py

# 2. Rebuild and restart
make build
make restart
```

### Building from Source

```bash
# Build image
docker-compose build

# Run locally (without Docker)
cd mcp-server
pip install -r requirements.txt
python -m uvicorn src.mcp_server:app --reload --port 8125
```

### Testing

```bash
# Test health
curl http://localhost:8125/health

# Test MCP initialize
curl -X POST http://localhost:8125/mcp/initialize \
  -H "Content-Type: application/json" \
  -d '{"protocolVersion": "2024-11-05"}'

# List tools
curl -X POST http://localhost:8125/mcp/tools/list

# Call tool
curl -X POST http://localhost:8125/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kg_query",
    "arguments": {"query": "Find all people", "limit": 5}
  }'
```

## Troubleshooting

### MCP Server Not Starting

1. **Check Docker network**:
   ```bash
   docker network ls | grep keel-network
   ```

2. **Check logs**:
   ```bash
   make logs
   ```

3. **Verify Neo4j/LightRAG**:
   ```bash
   # Neo4j
   curl http://localhost:7474
   
   # LightRAG
   curl http://localhost:8001/health
   ```

### Connection Issues

1. **Verify provider configuration**:
   ```bash
   curl http://localhost:8125/status
   ```

2. **Check environment variables**:
   ```bash
   docker exec keel-kg-mcp env | grep KG_PROVIDER
   ```

3. **Test connectivity**:
   ```bash
   # From MCP container to Neo4j
   docker exec keel-kg-mcp curl http://keel-neo4j:7474
   
   # From MCP container to LightRAG
   docker exec keel-kg-mcp curl http://keel-lightrag:8001/health
   ```

### IDE Not Connecting

1. **Verify MCP server is running**:
   ```bash
   make health
   ```

2. **Check IDE MCP configuration**:
   - Ensure URL is `http://localhost:8125/mcp`
   - Transport should be `http`

3. **Check IDE logs** for MCP connection errors

## Advanced Configuration

### Custom Port

Change MCP port in `.env`:
```bash
MCP_PORT=9000
```

Update docker-compose.yml ports:
```yaml
ports:
  - "9000:9000"
```

### Multiple Providers

Run separate instances for each provider:

```bash
# Neo4j instance
KG_PROVIDER=neo4j docker-compose up -d

# LightRAG instance (different port)
MCP_PORT=8126 KG_PROVIDER=lightrag docker-compose up -d
```

### Production Deployment

1. **Use environment-specific configs**:
   ```bash
   cp .env.example .env.production
   # Edit .env.production
   ```

2. **Enable authentication** (add to mcp_server.py):
   ```python
   from fastapi.security import HTTPBearer
   ```

3. **Use reverse proxy** (nginx, traefik):
   ```nginx
   location /mcp {
       proxy_pass http://localhost:8125;
   }
   ```

## Contributing

See main KEEL project for contribution guidelines.

## License

See main KEEL project for license information.

## Support

- **Issues**: GitHub Issues
- **Documentation**: [Agentic CLI Docs](../agentic-cli/README.md)
- **Knowledge Graph**: [KG Documentation](../agentic-cli/docs/KNOWLEDGE_GRAPH.md)
