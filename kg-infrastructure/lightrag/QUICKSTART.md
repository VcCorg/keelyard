# LightRAG Quick Start Guide

Get LightRAG running in 5 minutes!

## Step 1: Setup

```bash
# Run setup script
./setup.sh
```

## Step 2: Configure API Key

```bash
# Edit .env file
nano .env

# Add your OpenAI API key
OPENAI_API_KEY=sk-your-actual-key-here
```

## Step 3: Restart

```bash
make restart
```

## Step 4: Test

```bash
# Check health
make health

# Test connection
make test
```

## Step 5: Use It!

### Insert a Document

```bash
curl -X POST http://localhost:8001/insert \
  -H "Content-Type: application/json" \
  -d '{"text": "LightRAG is a lightweight retrieval-augmented generation system that combines vector search with knowledge graphs for efficient information retrieval."}'
```

### Query

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is LightRAG?",
    "mode": "hybrid"
  }'
```

### Python Client

```python
from lib.lightrag_client import LightRAGClient

client = LightRAGClient()

# Insert
client.insert("Your document text here")

# Query
result = client.query("Your question?", mode="hybrid")
print(result['result'])
```

## Common Commands

```bash
make start    # Start LightRAG
make stop     # Stop LightRAG
make logs     # View logs
make health   # Check health
make backup   # Backup data
```

## Next Steps

- Read the full [README.md](README.md)
- Explore different query modes (naive, local, global, hybrid)
- Try production mode with Milvus: `make start-prod`
- Integrate with Agentic agents

## Troubleshooting

**Service won't start?**
```bash
docker-compose logs lightrag
```

**Connection refused?**
```bash
make health
# Wait a few seconds and try again
```

**Need help?**
- Check [README.md](README.md) for detailed documentation
- Review logs with `make logs`
