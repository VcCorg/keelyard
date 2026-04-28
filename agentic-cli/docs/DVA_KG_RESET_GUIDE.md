# DVA Knowledge Graph Reset & Data Management Guide

## Overview

This guide covers how to reset/clear ingested data in the DVA Knowledge Graph system for both Neo4j and LightRAG providers.

---

## Current Reset Capabilities

### ✅ Available: Configuration Reset

**Command:**
```bash
`agent kg config --reset
```

**What it does:**
- Deletes `~/.dva-agentic/kg-config.json`
- Resets KG configuration to defaults
- **Does NOT delete ingested data**

**Use when:**
- You want to reconfigure provider settings
- You need to switch between Neo4j and LightRAG
- You want to reset connection parameters

---

### ✅ Available: LightRAG Data Clear

**Implementation exists** but **not exposed as CLI command**.

**Current code:** `src/dva_agentic_cli/kg/lightrag_client.py` (line 276-293)

```python
def clear(self) -> Dict[str, Any]:
    """
    Clear all LightRAG data.
    
    Returns:
        Clear result
    """
    try:
        response = self.client.delete(f"{self.base_url}/clear")
        response.raise_for_status()
        result = response.json()
        
        logger.info("LightRAG data cleared")
        return result
        
    except Exception as e:
        logger.error(f"Clear failed: {e}")
        raise
```

**Status:** ⚠️ **Method exists but no CLI command to call it**

---

### ❌ Not Available: Neo4j Data Clear

**Status:** No built-in command to clear Neo4j data.

**Workaround:** Use Cypher queries directly or Docker commands.

---

## How to Reset Ingested Data

### Option 1: Reset LightRAG Data (Recommended)

#### Method A: Add CLI Command (Recommended - Needs Implementation)

I can add a new command: `dva kg clear --provider lightrag`

#### Method B: Manual Docker Reset (Current Workaround)

```bash
# Stop and remove LightRAG container
docker stop dva-lightrag
docker rm dva-lightrag

# Remove LightRAG data volume
docker volume rm dva-lightrag-data
# OR if using bind mount:
rm -rf /path/to/lightrag/data/*

# Restart LightRAG
docker run -d \
  --name dva-lightrag \
  -p 8001:8001 \
  -v dva-lightrag-data:/data/lightrag \
  lightrag:latest
```

#### Method C: Direct API Call (Current Workaround)

```bash
# Call LightRAG clear endpoint directly
curl -X DELETE http://localhost:8001/clear
```

#### Method D: Python Script (Current Workaround)

```python
from dva_agentic_cli.kg.lightrag_client import LightRAGClient
from dva_agentic_cli.kg.config import KGConfig

config = KGConfig.load()
client = LightRAGClient(base_url=config.lightrag_url)
result = client.clear()
print(f"Cleared: {result}")
client.close()
```

---

### Option 2: Reset Neo4j Data

#### Method A: Cypher Query (Recommended)

```bash
# Connect to Neo4j browser: http://localhost:7474

# Delete all nodes and relationships
MATCH (n) DETACH DELETE n

# Verify deletion
MATCH (n) RETURN count(n)
```

#### Method B: Docker Reset (Nuclear Option)

```bash
# Stop Neo4j
docker stop neo4j

# Remove Neo4j data
docker volume rm neo4j_data
# OR if using bind mount:
rm -rf /path/to/neo4j/data/*

# Restart Neo4j
docker start neo4j
```

#### Method C: Neo4j CLI

```bash
# Access Neo4j container
docker exec -it neo4j bash

# Stop Neo4j service
neo4j stop

# Clear data directory
rm -rf /data/databases/neo4j/*

# Start Neo4j service
neo4j start
```

---

## Recommended: Add Clear Command

I can implement a new `dva kg clear` command that handles both providers:

### Proposed Implementation

**Command:**
```bash
# Clear LightRAG data
`agent kg clear --provider lightrag

# Clear Neo4j data
`agent kg clear --provider neo4j

# Clear both (if configured)
`agent kg clear --all

# With confirmation prompt
`agent kg clear --provider lightrag --yes
```

**Features:**
- ✅ Provider-aware clearing
- ✅ Confirmation prompt (safety)
- ✅ Stats before/after clearing
- ✅ Backup option before clearing
- ✅ Selective clearing (by persona, by source, etc.)

**Implementation location:**
- Add to `src/dva_agentic_cli/commands/kg.py`
- Use existing `LightRAGClient.clear()` method
- Add Neo4j clear using Cypher: `MATCH (n) DETACH DELETE n`

---

## Current Workarounds Summary

### For LightRAG

| Method | Difficulty | Data Loss | Recommended |
|--------|-----------|-----------|-------------|
| Docker reset | Easy | Complete | ✅ Yes |
| API call | Easy | Complete | ✅ Yes |
| Python script | Medium | Complete | ⚠️ If needed |

**Recommended:**
```bash
# Quick reset
docker exec dva-lightrag rm -rf /data/lightrag/*
docker restart dva-lightrag
```

### For Neo4j

| Method | Difficulty | Data Loss | Recommended |
|--------|-----------|-----------|-------------|
| Cypher query | Easy | Complete | ✅ Yes |
| Docker reset | Easy | Complete | ✅ Yes |
| Neo4j CLI | Medium | Complete | ⚠️ If needed |

**Recommended:**
```bash
# Via Neo4j browser (http://localhost:7474)
MATCH (n) DETACH DELETE n
```

---

## Data Management Best Practices

### 1. Check Stats Before Clearing

```bash
# See what you're about to delete
`agent kg stats
```

**Output example:**
```
Knowledge Graph Statistics:
  Provider: lightrag
  Entities: 8,006
  Relations: 16,550
  Documents: 3,168
```

### 2. Backup Before Major Changes

**Neo4j:**
```bash
# Create backup
docker exec neo4j neo4j-admin database dump neo4j --to-path=/backups

# Copy backup out
docker cp neo4j:/backups/neo4j.dump ./neo4j-backup-$(date +%Y%m%d).dump
```

**LightRAG:**
```bash
# Backup data directory
docker exec dva-lightrag tar czf /tmp/lightrag-backup.tar.gz /data/lightrag
docker cp dva-lightrag:/tmp/lightrag-backup.tar.gz ./lightrag-backup-$(date +%Y%m%d).tar.gz
```

### 3. Selective Re-ingestion

Instead of clearing everything, re-ingest specific sources:

```bash
# Re-ingest specific data source
`agent kg async submit --source cwow-patient-model --provider lightrag

# This will add/update data (may create duplicates in LightRAG)
```

**Note:** LightRAG currently doesn't deduplicate, so re-ingestion creates duplicates.

### 4. Test with Small Datasets First

```bash
# Test ingestion with small dataset
`agent kg ingest --path /path/to/small-test.pdf --provider lightrag

# Check results
`agent kg stats
`agent kg search "test query"

# If good, clear and ingest full dataset
```

---

## Proposed CLI Commands

### 1. Clear Command

```bash
`agent kg clear [OPTIONS]

Options:
  --provider TEXT        Provider to clear (neo4j, lightrag, both)  [required]
  --yes / --no-yes      Skip confirmation prompt  [default: no-yes]
  --backup / --no-backup Create backup before clearing  [default: backup]
  --persona TEXT        Clear only specific persona (developer, business)
  --source TEXT         Clear only specific data source
  --help                Show this message and exit.
```

**Examples:**
```bash
# Clear all LightRAG data (with confirmation)
`agent kg clear --provider lightrag

# Clear without confirmation
`agent kg clear --provider lightrag --yes

# Clear with backup
`agent kg clear --provider lightrag --backup

# Clear only developer persona
`agent kg clear --provider lightrag --persona developer

# Clear specific data source
`agent kg clear --provider lightrag --source cwow-patient-model
```

### 2. Backup Command

```bash
`agent kg backup [OPTIONS]

Options:
  --provider TEXT       Provider to backup (neo4j, lightrag, both)  [required]
  --output PATH        Output path for backup file
  --help               Show this message and exit.
```

**Examples:**
```bash
# Backup LightRAG data
`agent kg backup --provider lightrag --output ./backups/lightrag-backup.tar.gz

# Backup Neo4j data
`agent kg backup --provider neo4j --output ./backups/neo4j-backup.dump
```

### 3. Restore Command

```bash
`agent kg restore [OPTIONS]

Options:
  --provider TEXT       Provider to restore (neo4j, lightrag)  [required]
  --input PATH         Input backup file  [required]
  --yes / --no-yes     Skip confirmation prompt  [default: no-yes]
  --help               Show this message and exit.
```

**Examples:**
```bash
# Restore LightRAG data
`agent kg restore --provider lightrag --input ./backups/lightrag-backup.tar.gz

# Restore Neo4j data
`agent kg restore --provider neo4j --input ./backups/neo4j-backup.dump
```

---

## Implementation Priority

### High Priority (Implement Now)

1. ✅ **`dva kg clear`** - Essential for development/testing
   - Clear all data for provider
   - Confirmation prompt
   - Stats before/after

### Medium Priority (Nice to Have)

2. **`dva kg backup`** - Safety feature
   - Backup before clearing
   - Scheduled backups

3. **`dva kg restore`** - Recovery feature
   - Restore from backup
   - Validation

### Low Priority (Future Enhancement)

4. **Selective clearing** - Advanced feature
   - Clear by persona
   - Clear by source
   - Clear by date range

5. **Incremental ingestion** - Prevent duplicates
   - Detect existing entities
   - Update instead of create
   - Delta ingestion

---

## Quick Reference

### Current Commands

| Command | Purpose | Data Impact |
|---------|---------|-------------|
| `dva kg config --reset` | Reset configuration | None |
| `dva kg config --show` | Show configuration | None |
| `dva kg init` | Initialize provider | None |
| `dva kg ingest` | Ingest data | Adds data |
| `dva kg async submit` | Async ingest | Adds data |
| `dva kg query` | Query data | None |
| `dva kg search` | Search data | None |
| `dva kg stats` | Show statistics | None |

### Missing Commands (Need Implementation)

| Command | Purpose | Priority |
|---------|---------|----------|
| `dva kg clear` | Clear ingested data | 🔴 High |
| `dva kg backup` | Backup data | 🟡 Medium |
| `dva kg restore` | Restore data | 🟡 Medium |
| `dva kg deduplicate` | Remove duplicates | 🟢 Low |
| `dva kg validate` | Validate data integrity | 🟢 Low |

---

## Summary

**Current State:**
- ✅ Configuration reset available: `dva kg config --reset`
- ⚠️ LightRAG clear method exists but not exposed as CLI command
- ❌ Neo4j clear not implemented
- ❌ No backup/restore commands

**Workarounds:**
- **LightRAG:** Docker reset, API call, or Python script
- **Neo4j:** Cypher query or Docker reset

**Recommendation:**
Implement `dva kg clear` command to properly expose data clearing functionality with safety features (confirmation, backup, stats).

**Would you like me to implement the `dva kg clear` command now?**
