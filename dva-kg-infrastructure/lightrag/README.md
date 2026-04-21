# LightRAG Infrastructure

Docker-based infrastructure for running LightRAG (Light Retrieval-Augmented Generation) as a knowledge graph service for the DVA Agentic platform.

## Overview

LightRAG is a lightweight RAG system that combines vector search with knowledge graph capabilities. This infrastructure provides:

- **Dockerized LightRAG API server** with REST endpoints
- **Multiple LLM provider support** (OpenAI, Anthropic, Vertex AI)
- **Flexible storage backends** (nano-vectordb, Milvus, ChromaDB)
- **Graph storage options** (NetworkX, Neo4j)
- **Python client library** for easy integration
- **Production-ready setup** with health checks and monitoring

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.10+ (for client library)
- OpenAI API key (or other LLM provider credentials)

### Installation

1. **Run the setup script:**
```bash
./setup.sh
```

2. **Configure your API keys:**
```bash
# Edit .env file
nano .env

# Add your OpenAI API key
OPENAI_API_KEY=your_actual_api_key_here
```

3. **Restart the service:**
```bash
make restart
```

4. **Verify it's running:**
```bash
make health
```

## Architecture

### Components

- **LightRAG API Server**: FastAPI-based REST API for LightRAG operations
- **Vector Store**: Stores document embeddings (default: nano-vectordb)
- **Graph Store**: Stores knowledge graph (default: NetworkX)
- **LLM Provider**: Generates responses (default: OpenAI)

### Modes

- **Development** (default): Uses lightweight in-memory stores
- **Production**: Uses Milvus for vectors and optionally Neo4j for graphs

## Configuration

### Environment Variables

Edit `.env` file to configure:

#### LLM Provider (choose one)

**OpenAI (default):**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Anthropic:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

**Google Vertex AI:**
```bash
LLM_PROVIDER=vertex_ai
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-pro
```

#### Storage Configuration

**Vector Store:**
```bash
VECTOR_STORE=nano-vectordb  # Options: nano-vectordb, milvus, chromadb
```

**Graph Store:**
```bash
GRAPH_STORE=networkx  # Options: networkx, neo4j
```

**For Neo4j graph store:**
```bash
GRAPH_STORE=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## Usage

### Make Commands

```bash
make help        # Show all commands
make start       # Start LightRAG
make stop        # Stop LightRAG
make restart     # Restart LightRAG
make status      # Show container status
make logs        # View logs
make health      # Check health
make test        # Test connection
make clean       # Remove all data
make backup      # Backup data
make restore     # Restore from backup
make install     # Install Python client
```

### API Endpoints

**Base URL:** `http://localhost:8001`

#### Insert Document
```bash
curl -X POST http://localhost:8001/insert \
  -H "Content-Type: application/json" \
  -d '{"text": "Your document text here"}'
```

#### Query Knowledge Graph
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is LightRAG?",
    "mode": "hybrid",
    "top_k": 10
  }'
```

**Query Modes:**
- `naive`: Simple retrieval
- `local`: Local context search
- `global`: Global knowledge graph search
- `hybrid`: Combines local and global (recommended)

#### Semantic Search
```bash
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "top_k": 5
  }'
```

#### Get Statistics
```bash
curl http://localhost:8001/stats
```

#### Health Check
```bash
curl http://localhost:8001/health
```

### Python Client

#### Installation
```bash
cd lightrag-infrastructure
make install
```

#### Basic Usage

```python
from lib.lightrag_client import LightRAGClient

# Initialize client
client = LightRAGClient(base_url="http://localhost:8001")

# Check health
health = client.health_check()
print(health)

# Insert documents
result = client.insert("LightRAG is a lightweight RAG system.")
print(result)

# Query
response = client.query(
    query="What is LightRAG?",
    mode="hybrid",
    top_k=10
)
print(response['result'])

# Semantic search
results = client.search("machine learning", top_k=5)
print(results)

# Get statistics
stats = client.get_stats()
print(stats)
```

#### Async Usage

```python
import asyncio
from lib.lightrag_client import AsyncLightRAGClient

async def main():
    async with AsyncLightRAGClient() as client:
        # Insert
        await client.insert("Document text")
        
        # Query
        result = await client.query("Your question")
        print(result)

asyncio.run(main())
```

## Production Deployment

### Using Milvus for Vector Storage

1. **Start with production profile:**
```bash
make start-prod
```

2. **Update .env:**
```bash
VECTOR_STORE=milvus
```

3. **Restart:**
```bash
make restart
```

### Using Neo4j for Graph Storage

1. **Start Neo4j** (from neo4j-infrastructure):
```bash
cd ../neo4j-infrastructure
make start
```

2. **Update .env:**
```bash
GRAPH_STORE=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

3. **Restart LightRAG:**
```bash
make restart
```

## Troubleshooting

### LightRAG won't start

1. **Check Docker:**
```bash
docker ps
docker-compose logs lightrag
```

2. **Verify API key:**
```bash
grep OPENAI_API_KEY .env
```

3. **Check port availability:**
```bash
lsof -i :8001
```

### Connection errors

1. **Verify service is running:**
```bash
make health
```

2. **Check firewall settings**

3. **Restart service:**
```bash
make restart
```

### Out of memory

1. **Increase Docker memory limit** in Docker Desktop settings

2. **Reduce batch size** in configuration

3. **Use production storage** (Milvus) for large datasets

## Data Management

### Backup

```bash
make backup
```

Backups are stored in `backups/` directory with timestamps.

### Restore

```bash
make restore
# Enter backup name when prompted
```

### Clear All Data

```bash
curl -X DELETE http://localhost:8001/clear
```

Or use the client:
```python
client.clear()
```

## Performance Tuning

### Adjust Worker Count

In `.env`:
```bash
MAX_ASYNC_WORKERS=8  # Increase for more parallelism
```

### Token Limits

```bash
MAX_TOKENS=32768        # Max tokens for LLM
MAX_EMBED_TOKENS=8192   # Max tokens for embeddings
```

### Storage Selection

- **Development**: nano-vectordb + networkx (fast, in-memory)
- **Production**: Milvus + Neo4j (scalable, persistent)

## Integration with DVA Agentic

LightRAG can be used as an alternative to Neo4j in the ADK agent template:

```python
from src.agents.lightrag_agent import LightRAGAgent

agent = LightRAGAgent(
    lightrag_url="http://localhost:8001"
)

result = await agent.process({
    "task": "query",
    "query": "What is machine learning?"
})
```

See the agent template documentation for more details.

## Resources

- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [LightRAG Paper](https://arxiv.org/abs/2410.05779)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)

## Support

For issues and questions:
- Check the logs: `make logs`
- Review this README
- Check the DVA Agentic documentation

## License

[Add your license here]
