# Neo4j Infrastructure Quick Start

Get Neo4j up and running in 5 minutes for DVA Agentic CLI.

## Prerequisites

- Docker installed and running
- Docker Compose installed

## Quick Setup

```bash
# 1. Navigate to this directory
cd neo4j-infrastructure

# 2. Run the setup script
chmod +x setup.sh
./setup.sh
```

That's it! Neo4j is now running.

## Access Neo4j

- **Browser UI**: http://localhost:7474
- **Bolt Protocol**: bolt://localhost:7687
- **Username**: neo4j
- **Password**: password

## Configure DVA CLI

```bash
dva kg init \
  --provider neo4j \
  --uri bolt://localhost:7687 \
  --username neo4j \
  --password password
```

## Verify Setup

```bash
# Check if Neo4j is running
make health

# Or use DVA CLI
dva kg check
dva kg stats
```

## Common Commands

```bash
# Start Neo4j
make start

# Stop Neo4j
make stop

# View logs
make logs

# Check status
make status

# Restart
make restart
```

## Troubleshooting

### Neo4j won't start

```bash
# Check if ports are available
lsof -i :7474
lsof -i :7687

# Check Docker logs
make logs
```

### Connection refused

```bash
# Wait for Neo4j to fully start (30-60 seconds)
make health

# Restart if needed
make restart
```

### Out of memory

Edit `docker-compose.yml` and increase heap size:

```yaml
- NEO4J_server_memory_heap_max__size=4G
```

Then restart:

```bash
make restart
```

## Next Steps

1. **Ingest data**: `dva kg ingest document.pdf`
2. **Query**: `dva kg query "Find all entities"`
3. **Search**: `dva kg search "AI" --semantic`
4. **Visualize**: `dva kg visualize --output graph.html`

## Full Documentation

See [README.md](README.md) for complete documentation.
