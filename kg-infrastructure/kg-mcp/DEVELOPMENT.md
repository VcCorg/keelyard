# Development Guide - Volume Mount Architecture

## Overview

The KG MCP Server uses a **runtime volume mount** architecture for KG modules. This means the KG code is NOT copied into the Docker image, but instead mounted at runtime from the Agentic CLI source.

## Architecture

```
Host Machine                          Docker Container
─────────────────                     ────────────────

agentic-cli/                      /app/
├── src/                              ├── src/
│   └── dva_agentic_cli/              │   ├── mcp_server.py (copied)
│       └── kg/                       │   └── kg/ (volume mounted ↓)
│           ├── query.py    ────────────────→ query.py
│           ├── search.py   ────────────────→ search.py
│           ├── neo4j_client.py ────────────→ neo4j_client.py
│           └── ...         ────────────────→ ...
```

## Benefits

### 1. **Instant Code Reflection**
- Edit KG code in CLI
- Restart container
- Changes are live (no rebuild!)

### 2. **Single Source of Truth**
- KG code lives in `agentic-cli` only
- No duplicate copies to maintain
- No sync issues

### 3. **Faster Development**
- No Docker image rebuild for KG changes
- Restart takes ~5 seconds vs rebuild ~2 minutes
- Faster iteration cycle

### 4. **Consistent Behavior**
- CLI and MCP server use same code
- Bug fixes apply to both
- Feature additions work everywhere

## How It Works

### Docker Compose Configuration

```yaml
# docker-compose.yml
services:
  kg-mcp-server:
    volumes:
      # Runtime mount - KG modules from CLI
      - ../agentic-cli/src/dva_agentic_cli/kg:/app/src/kg:ro
```

### Dockerfile

```dockerfile
# Dockerfile
# Only copy MCP server code (not KG modules)
COPY src/mcp_server.py /app/src/
COPY src/__init__.py /app/src/

# Create directory for runtime mount
RUN mkdir -p /app/src/kg
```

### Runtime Behavior

1. **Container starts**
2. **Volume mount happens**: Host `kg/` → Container `/app/src/kg`
3. **Python imports work**: `from kg.query import execute_query`
4. **Code executes** from mounted volume

## Development Workflow

### Scenario 1: Modify KG Query Logic

```bash
# 1. Edit the code
cd agentic-cli/src/dva_agentic_cli/kg
nano query.py
# Make changes to execute_query()

# 2. Restart MCP container
cd ../../kg-mcp-infrastructure
make restart

# 3. Test
make test
# OR
curl -X POST http://localhost:8125/mcp/tools/call \
  -d '{"name":"kg_query","arguments":{"query":"test"}}'
```

**Time**: ~10 seconds total

### Scenario 2: Modify MCP Server

```bash
# 1. Edit MCP server
cd kg-mcp-infrastructure/mcp-server/src
nano mcp_server.py
# Make changes to MCP endpoints

# 2. Rebuild and restart
cd ../..
make build
make restart

# 3. Test
make test
```

**Time**: ~2 minutes (rebuild required)

### Scenario 3: Add New KG Module

```bash
# 1. Create new module in CLI
cd agentic-cli/src/dva_agentic_cli/kg
nano new_feature.py
# Create new functionality

# 2. Update MCP server to use it
cd ../../../kg-mcp-infrastructure/mcp-server/src
nano mcp_server.py
# Import and use new_feature

# 3. Rebuild and restart
cd ../..
make build
make restart
```

## What Gets Copied vs Mounted

### Copied into Image (at build time):
- ✅ `mcp_server.py` - Main MCP server
- ✅ `__init__.py` - Package init
- ✅ `requirements.txt` - Dependencies
- ✅ System packages (curl, git)

### Mounted at Runtime:
- 📁 `kg/` directory - All KG modules
- 📁 `~/.dva-agentic/` - DVA config
- 📁 `~/.config/gcloud/` - Google credentials

## Troubleshooting

### Issue: "Module not found: kg"

**Cause**: Volume mount failed or path incorrect

**Solution**:
```bash
# Check if CLI exists at expected location
ls ../agentic-cli/src/dva_agentic_cli/kg

# Check container mount
docker exec dva-kg-mcp ls -la /app/src/kg

# Verify docker-compose.yml path
cat docker-compose.yml | grep "kg:"
```

### Issue: "Changes not reflected"

**Cause**: Container not restarted or Python cached

**Solution**:
```bash
# Restart container
make restart

# Or force recreate
docker-compose up -d --force-recreate

# Check if files are mounted
docker exec dva-kg-mcp cat /app/src/kg/query.py
```

### Issue: "Permission denied"

**Cause**: Volume mount permissions

**Solution**:
```bash
# Check host permissions
ls -la ../agentic-cli/src/dva_agentic_cli/kg

# Mount is read-only (:ro) which is correct
# If issues persist, remove :ro flag temporarily
```

## Best Practices

### 1. **Always Test After Changes**
```bash
make restart && make test
```

### 2. **Use Version Control**
```bash
# Commit changes to CLI repo
cd ../agentic-cli
git add src/dva_agentic_cli/kg/query.py
git commit -m "Fix query logic"

# MCP server automatically uses new version
cd ../kg-mcp-infrastructure
make restart
```

### 3. **Document Breaking Changes**
If KG module changes break MCP server compatibility:
- Update `mcp_server.py` accordingly
- Document in CHANGELOG
- Rebuild image

### 4. **Keep Paths Relative**
Docker compose uses relative path:
```yaml
- ../agentic-cli/src/dva_agentic_cli/kg:/app/src/kg:ro
```

This works if directory structure is:
```
agentic-project/
├── agentic-cli/
└── kg-mcp-infrastructure/
```

## Performance Considerations

### Volume Mount Performance
- **Read performance**: Excellent (native filesystem)
- **Write performance**: N/A (read-only mount)
- **Startup time**: No impact
- **Runtime overhead**: Negligible

### When to Rebuild

**Rebuild NOT needed**:
- ✅ KG module changes
- ✅ Config changes
- ✅ Data changes

**Rebuild needed**:
- ⚠️ MCP server changes
- ⚠️ Dependency changes (requirements.txt)
- ⚠️ Dockerfile changes
- ⚠️ System package changes

## Comparison: Copy vs Mount

| Aspect | Copy (Old) | Mount (New) |
|--------|-----------|-------------|
| Code changes | Rebuild required | Restart only |
| Build time | ~2 minutes | ~2 minutes |
| Restart time | ~5 seconds | ~5 seconds |
| Sync issues | Possible | None |
| Development speed | Slow | Fast |
| Production ready | Yes | Yes |
| Disk usage | Duplicate code | Single copy |

## Advanced: Development Mode

For even faster iteration, use `--reload`:

```bash
# Run MCP server with auto-reload
docker-compose run --rm \
  -p 8125:8125 \
  kg-mcp-server \
  python -m uvicorn src.mcp_server:app \
    --host 0.0.0.0 \
    --port 8125 \
    --reload
```

Now changes to both MCP server AND KG modules reload automatically!

## Summary

The volume mount architecture provides:
- ✅ **Faster development** (no rebuilds for KG changes)
- ✅ **Single source of truth** (code lives in CLI)
- ✅ **Instant reflection** (restart vs rebuild)
- ✅ **Better workflow** (edit → restart → test)

This is the recommended approach for development and works perfectly in production too.

---

**Last Updated**: November 23, 2025
**Architecture**: Runtime Volume Mount
**Status**: ✅ Implemented
