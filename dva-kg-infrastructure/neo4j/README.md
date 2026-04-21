# Neo4j Infrastructure for DVA Agentic CLI

This project provides a Docker-based Neo4j setup for the DVA Agentic CLI knowledge graph feature.

## Prerequisites

- Docker (20.10+)
- Docker Compose (2.0+)

## Quick Start

```bash
# Run the setup script
chmod +x setup.sh
./setup.sh

# Or manually with make
make start
```

Neo4j will be available at:
- **Browser UI**: http://localhost:7474
- **Bolt Protocol**: bolt://localhost:7687
- **Credentials**: neo4j / password

## Configuration

### Default Settings

The default configuration includes:
- Neo4j 5.14 Community Edition
- APOC plugin enabled
- Vector index support for embeddings
- 2GB heap memory
- 1GB page cache

### Customization

Edit `.env` file to customize:

```bash
# Copy example
cp .env.example .env

# Edit settings
nano .env
```

Available settings:
- `NEO4J_AUTH` - Username/password (default: neo4j/password)
- `NEO4J_HEAP_INITIAL` - Initial heap size (default: 512m)
- `NEO4J_HEAP_MAX` - Maximum heap size (default: 2G)
- `NEO4J_PAGECACHE` - Page cache size (default: 1G)
- `NEO4J_HTTP_PORT` - HTTP port (default: 7474)
- `NEO4J_BOLT_PORT` - Bolt port (default: 7687)

## Management Commands

### Start/Stop

```bash
# Start Neo4j
make start

# Stop Neo4j
make stop

# Restart Neo4j
make restart
```

### Monitoring

```bash
# Check status
make status

# View logs
make logs

# Check health
make health

# Test connection
make test
```

### Data Management

```bash
# Backup data
make backup

# Restore from backup
make restore

# Clean all data (WARNING: deletes everything)
make clean
```

## Integration with DVA CLI

### 1. Configure DVA CLI

```bash
dva kg init \
  --provider neo4j \
  --uri bolt://localhost:7687 \
  --username neo4j \
  --password password \
  --embeddings vertex-ai
```

### 2. Verify Connection

```bash
dva kg config --show
dva kg stats
```

### 3. Start Using

```bash
# Ingest data
dva kg ingest document.pdf

# Query
dva kg query "Find all entities"

# Search
dva kg search "artificial intelligence" --semantic
```

## Docker Compose Details

### Services

- **neo4j**: Neo4j database server

### Volumes

- `neo4j_data`: Database files
- `neo4j_logs`: Log files
- `neo4j_import`: Import directory
- `neo4j_plugins`: Plugin directory

### Networks

- `dva-network`: Bridge network for service communication

## Health Checks

The container includes automatic health checks:
- HTTP endpoint check every 10 seconds
- 5 retries with 5-second timeout
- 30-second startup grace period

## Performance Tuning

### Memory Settings

Adjust based on your system resources:

```yaml
# In docker-compose.yml
environment:
  - NEO4J_server_memory_heap_initial__size=512m
  - NEO4J_server_memory_heap_max__size=2G
  - NEO4J_server_memory_pagecache_size=1G
```

Recommendations:
- **Small datasets** (<1GB): 512m heap, 512m cache
- **Medium datasets** (1-10GB): 2G heap, 2G cache
- **Large datasets** (>10GB): 4G heap, 4G cache

### Connection Pooling

Neo4j automatically manages connection pooling. Default settings work well for most use cases.

## Troubleshooting

### Container Won't Start

```bash
# Check Docker logs
docker-compose logs neo4j

# Check if ports are available
lsof -i :7474
lsof -i :7687

# Restart Docker daemon
# macOS: Restart Docker Desktop
# Linux: sudo systemctl restart docker
```

### Connection Refused

```bash
# Wait for Neo4j to fully start (can take 30-60 seconds)
make health

# Check if container is running
docker ps | grep dva-neo4j

# Check firewall settings
# Ensure ports 7474 and 7687 are not blocked
```

### Out of Memory

```bash
# Increase heap size in docker-compose.yml
NEO4J_server_memory_heap_max__size=4G

# Restart
make restart
```

### Data Corruption

```bash
# Stop Neo4j
make stop

# Restore from backup
make restore

# Or start fresh
make clean
make start
```

## Security Considerations

### Production Deployment

For production use:

1. **Change default password**:
   ```yaml
   NEO4J_AUTH=neo4j/your-secure-password
   ```

2. **Enable SSL/TLS**:
   ```yaml
   - NEO4J_dbms_ssl_policy_bolt_enabled=true
   - NEO4J_dbms_ssl_policy_bolt_base__directory=/ssl
   ```

3. **Restrict network access**:
   ```yaml
   ports:
     - "127.0.0.1:7474:7474"
     - "127.0.0.1:7687:7687"
   ```

4. **Regular backups**:
   ```bash
   # Set up cron job
   0 2 * * * cd /path/to/neo4j-infrastructure && make backup
   ```

### Access Control

Neo4j supports role-based access control (RBAC). Configure in Neo4j Browser:

```cypher
// Create read-only user
CREATE USER reader SET PASSWORD 'password' CHANGE NOT REQUIRED;
GRANT ROLE reader TO reader;

// Create admin user
CREATE USER admin SET PASSWORD 'password' CHANGE NOT REQUIRED;
GRANT ROLE admin TO admin;
```

## Backup and Restore

### Automatic Backups

```bash
# Create backup
make backup

# Backups are stored in ./backups/ directory
# Format: neo4j-backup-YYYYMMDD-HHMMSS.dump
```

### Manual Backup

```bash
# Using neo4j-admin
docker exec dva-neo4j neo4j-admin database dump neo4j \
  --to-path=/var/lib/neo4j/import

# Copy from container
docker cp dva-neo4j:/var/lib/neo4j/import/neo4j.dump ./backup.dump
```

### Restore

```bash
# Interactive restore
make restore

# Manual restore
docker cp backup.dump dva-neo4j:/var/lib/neo4j/import/restore.dump
docker exec dva-neo4j neo4j-admin database load neo4j \
  --from-path=/var/lib/neo4j/import \
  --overwrite-destination=true
make restart
```

## Monitoring

### Metrics

Access Neo4j metrics at:
- http://localhost:7474/metrics

### Query Monitoring

```cypher
// Show running queries
CALL dbms.listQueries();

// Show slow queries
CALL dbms.listQueries() 
YIELD query, elapsedTimeMillis 
WHERE elapsedTimeMillis > 1000 
RETURN query, elapsedTimeMillis;
```

### Resource Usage

```bash
# Container stats
docker stats dva-neo4j

# Detailed metrics
docker exec dva-neo4j neo4j-admin server memory-recommendation
```

## Upgrading

### Neo4j Version

```bash
# Stop current version
make stop

# Update version in docker-compose.yml
# NEO4J_VERSION=5.15-community

# Pull new image
docker-compose pull

# Start with new version
make start
```

### Data Migration

```bash
# Backup current data
make backup

# Upgrade Neo4j version
# (edit docker-compose.yml)

# Start new version
make start

# If issues occur, restore backup
make restore
```

## Support

- Neo4j Documentation: https://neo4j.com/docs/
- DVA CLI Documentation: ../dva-agentic-cli/docs/KNOWLEDGE_GRAPH.md
- Docker Documentation: https://docs.docker.com/

## License

Same as DVA Agentic CLI project.
