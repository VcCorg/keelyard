# Neo4j Infrastructure Validation Guide

## Overview

The Neo4j infrastructure now includes comprehensive validation commands to ensure your setup is working correctly.

## Quick Validation

```bash
# Run comprehensive validation
make validate

# Quick health check
make health

# Test queries
make test
```

## Validation Commands

### `make validate` - Comprehensive Validation

Performs 7 detailed checks:

1. **Docker Status**
   - Verifies Docker is installed
   - Checks Docker daemon is running

2. **Container Status**
   - Confirms Neo4j container is running
   - Shows container health status

3. **HTTP Endpoint (Browser)**
   - Tests Neo4j Browser accessibility
   - Verifies port 7474 is responding

4. **Bolt Connection (Database)**
   - Tests database connectivity
   - Verifies bolt://localhost:7687 is accessible
   - Validates credentials

5. **Database Operations**
   - Executes test queries
   - Shows node and relationship counts
   - Confirms query execution works

6. **Database Info**
   - Retrieves Neo4j version
   - Shows edition (community/enterprise)
   - Displays kernel information

7. **APOC Plugin**
   - Checks if APOC plugin is installed
   - Shows APOC version if available
   - Marks as optional if not present

### Example Output

```
==========================================
Neo4j Infrastructure Validation
==========================================

1. Docker Status
-------------------
Docker version 28.5.1, build e180ab8
✓ Docker installed
✓ Docker daemon running

2. Container Status
-------------------
✓ Neo4j container running
  Status: Up 12 days (healthy)

3. HTTP Endpoint (Browser)
-------------------
✓ Neo4j Browser accessible at http://localhost:7474

4. Bolt Connection (Database)
-------------------
✓ Bolt connection successful (bolt://localhost:7687)

5. Database Operations
-------------------
✓ Query execution working
  Nodes: 6759
  Relationships: 6461

6. Database Info
-------------------
✓ Neo4j: "Neo4j Kernel", "5.14.0", "community"

7. APOC Plugin
-------------------
✓ APOC plugin installed (5.14.0)

==========================================
✓ All validation checks passed!
==========================================

Neo4j is ready for use:
  Browser: http://localhost:7474
  Bolt:    bolt://localhost:7687
  User:    neo4j
  Pass:    password
```

### `make health` - Quick Health Check

Fast check of HTTP and Bolt connectivity:

```bash
$ make health
Checking Neo4j health...
✓ Neo4j HTTP (port 7474) is accessible
✓ Neo4j Bolt (port 7687) is accessible
```

### `make test` - Query Tests

Executes sample queries to verify database operations:

```bash
$ make test
Testing Neo4j queries...

1. Node count:
node_count
6759

2. Relationship count:
relationship_count
6461

3. Database info:
name, version, edition
"Neo4j Kernel", "5.14.0", "community"

✓ All tests completed
```

## Troubleshooting

### Container Not Running

```bash
✗ Neo4j container not running
```

**Solution:**
```bash
make start
```

### Bolt Connection Failed

```bash
✗ Bolt connection failed
Check credentials or wait for Neo4j to fully start
```

**Solutions:**
1. Wait 10-15 seconds for Neo4j to fully initialize
2. Check credentials in `.env` file
3. Verify container logs: `make logs`

### HTTP Not Accessible

```bash
✗ Neo4j Browser not accessible
```

**Solutions:**
1. Check if port 7474 is already in use: `lsof -i :7474`
2. Verify container is running: `make status`
3. Check firewall settings

### APOC Plugin Not Available

```bash
⚠ APOC plugin not available (optional)
```

**Note:** This is a warning, not an error. APOC is optional but recommended for advanced operations.

**To install APOC:**
1. Update `docker-compose.yml` to include APOC plugin
2. Restart container: `make restart`

## Integration with Agentic CLI

The validation commands work seamlessly with Agentic CLI:

```bash
# Validate Neo4j infrastructure
cd neo4j-infrastructure
make validate

# Configure Agentic CLI to use Neo4j
`agent kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password

# Test Agentic CLI connection
`agent kg stats
```

## Automated Validation

You can integrate validation into your workflow:

```bash
# Start and validate in one command
make start && make validate

# Restart and validate
make restart && sleep 5 && make validate
```

## CI/CD Integration

Use validation in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Start Neo4j
  run: cd neo4j-infrastructure && make start

- name: Validate Neo4j
  run: cd neo4j-infrastructure && make validate

- name: Run tests
  run: pytest tests/
```

## Comparison: Neo4j vs LightRAG Validation

| Feature | Neo4j | LightRAG |
|---------|-------|----------|
| Docker Check | ✅ | ✅ |
| Container Status | ✅ | ✅ |
| HTTP Endpoint | ✅ (Browser) | ✅ (API) |
| Database Connection | ✅ (Bolt) | ✅ (REST) |
| Query Testing | ✅ (Cypher) | ✅ (Insert) |
| Version Info | ✅ | ✅ |
| Plugin Check | ✅ (APOC) | ❌ |
| Stats Display | ✅ | ✅ |

## Best Practices

1. **Run validation after setup**
   ```bash
   ./setup.sh
   make validate
   ```

2. **Validate before important operations**
   ```bash
   make validate && agent kg ingest --path /data
   ```

3. **Regular health checks**
   ```bash
   # Add to cron for monitoring
   */5 * * * * cd /path/to/neo4j-infrastructure && make health
   ```

4. **Validate after configuration changes**
   ```bash
   # After editing docker-compose.yml or .env
   make restart
   make validate
   ```

## Exit Codes

- `0` - All checks passed
- `1` - One or more checks failed (validation stops at first failure)

## Additional Commands

```bash
# View all available commands
make help

# Check container status
make status

# View logs
make logs

# Backup database
make backup

# Restore from backup
make restore

# Clean up (removes all data)
make clean
```

## Support

For issues or questions:
1. Check logs: `make logs`
2. Run validation: `make validate`
3. Review [Neo4j documentation](https://neo4j.com/docs/)
4. Check [Agentic CLI documentation](../agentic-cli/README.md)
