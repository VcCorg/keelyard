# Knowledge Graph Clear Command

## Overview

The `keel kg clear` command provides a safe and comprehensive way to delete all data from your knowledge graph, supporting both Neo4j and LightRAG providers.

---

## Command Syntax

```bash
`agent kg clear [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--provider` | TEXT | configured | Provider to clear: `neo4j`, `lightrag`, or `both` |
| `--yes` | FLAG | false | Skip confirmation prompt |
| `--show-stats` | FLAG | true | Show statistics before and after clearing |
| `--help` | FLAG | - | Show help message |

---

## Usage Examples

### Basic Usage (With Confirmation)

```bash
# Clear configured provider with confirmation prompt
`agent kg clear
```

**Output:**
```
Current Statistics:

LightRAG:
  Entities: 8006
  Relations: 16550
  Documents: 3168

⚠ Warning: This will delete ALL data from lightrag.
This operation cannot be undone.

Are you sure you want to continue? [y/N]: y

Clearing lightrag...
✓ LightRAG data cleared successfully

Final Statistics:

LightRAG:
  Entities: 0
  Relations: 0
  Documents: 0

✓ Successfully cleared lightrag
```

### Clear Specific Provider

```bash
# Clear LightRAG
`agent kg clear --provider lightrag

# Clear Neo4j
`agent kg clear --provider neo4j

# Clear both providers
`agent kg clear --provider both
```

### Skip Confirmation (Automated Scripts)

```bash
# Clear without confirmation prompt
`agent kg clear --provider lightrag --yes

# Useful for CI/CD or automated testing
`agent kg clear --provider both --yes
```

### Without Statistics

```bash
# Clear without showing before/after stats (faster)
`agent kg clear --provider lightrag --no-show-stats --yes
```

---

## Safety Features

### 1. Confirmation Prompt

By default, the command requires explicit confirmation:

```
⚠ Warning: This will delete ALL data from lightrag.
This operation cannot be undone.

Are you sure you want to continue? [y/N]:
```

**Skip with:** `--yes` flag

### 2. Before/After Statistics

Shows what you're deleting and confirms deletion:

```
Current Statistics:
  Entities: 8006
  Relations: 16550
  Documents: 3168

[... clearing ...]

Final Statistics:
  Entities: 0
  Relations: 0
  Documents: 0
```

**Disable with:** `--no-show-stats` flag

### 3. Provider Validation

Validates provider names before execution:

```bash
`agent kg clear --provider invalid
# ✗ Invalid provider: invalid
# Valid providers: neo4j, lightrag
```

### 4. Error Handling

Gracefully handles errors and provides clear messages:

```bash
# If LightRAG is not running
✗ Error clearing lightrag: Connection refused

# If Neo4j credentials are wrong
✗ Error clearing neo4j: Authentication failed
```

---

## Provider-Specific Behavior

### LightRAG

**What gets deleted:**
- All entities and their embeddings
- All relationships
- All documents and chunks
- All vector indices
- LLM response cache

**Implementation:**
- Calls LightRAG `/clear` API endpoint
- Clears all data directories
- Resets vector databases

**Recovery:**
- Data is permanently deleted
- Must re-ingest to restore

### Neo4j

**What gets deleted:**
- All nodes (all labels)
- All relationships (all types)
- All node properties
- All relationship properties
- All indexes remain (structure preserved)

**Implementation:**
- Executes Cypher: `MATCH (n) DETACH DELETE n`
- Deletes nodes and their relationships atomically
- Preserves database schema and constraints

**Recovery:**
- Data is permanently deleted
- Must re-ingest to restore
- Indexes and constraints remain

---

## Common Use Cases

### 1. Development/Testing

Clear data between test runs:

```bash
# Run test ingestion
`agent kg ingest --path test-data.pdf

# Test queries
`agent kg query "test"

# Clear for next test
`agent kg clear --yes

# Run next test
`agent kg ingest --path test-data-2.pdf
```

### 2. Re-ingestion After Schema Changes

Clear before re-ingesting with updated schema:

```bash
# Clear old data
`agent kg clear --provider lightrag --yes

# Re-ingest with new schema
`agent kg async submit --source cwow-patient-model --provider lightrag
```

### 3. Switching Providers

Clear one provider before switching:

```bash
# Clear LightRAG
`agent kg clear --provider lightrag --yes

# Switch to Neo4j
`agent kg init --provider neo4j --uri bolt://localhost:7687

# Ingest to Neo4j
`agent kg ingest --source my-data --provider neo4j
```

### 4. Removing Duplicate Data

Clear and re-ingest to remove duplicates:

```bash
# Check for duplicates
`agent kg stats

# Clear all data
`agent kg clear --yes

# Re-ingest once
`agent kg async submit --source my-data
```

### 5. CI/CD Pipeline

Automated testing with clean state:

```bash
#!/bin/bash
# test-kg.sh

# Clear previous test data
`agent kg clear --provider lightrag --yes --no-show-stats

# Ingest test data
`agent kg ingest --path test-fixtures/sample.pdf

# Run tests
pytest tests/test_kg_queries.py

# Clear after tests
`agent kg clear --provider lightrag --yes --no-show-stats
```

---

## Best Practices

### 1. Always Check Stats First

```bash
# Check what you're about to delete
`agent kg stats

# Then clear
`agent kg clear
```

### 2. Backup Before Clearing (Production)

```bash
# For Neo4j
docker exec neo4j neo4j-admin database dump neo4j --to-path=/backups
docker cp neo4j:/backups/neo4j.dump ./backup-$(date +%Y%m%d).dump

# For LightRAG
docker exec keel-lightrag tar czf /tmp/lightrag-backup.tar.gz /data/lightrag
docker cp keel-lightrag:/tmp/lightrag-backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz

# Then clear
`agent kg clear
```

### 3. Use --yes in Scripts Only

```bash
# ✅ Good: Interactive use with confirmation
`agent kg clear

# ✅ Good: Automated script with --yes
`agent kg clear --yes

# ❌ Bad: Always using --yes interactively (risky)
alias clear-kg='agent kg clear --yes'  # Don't do this!
```

### 4. Verify Clearing

```bash
# Clear
`agent kg clear --yes

# Verify it's empty
`agent kg stats

# Should show 0 entities/nodes
```

### 5. Clear Both Providers When Switching

```bash
# When switching from LightRAG to Neo4j
`agent kg clear --provider both --yes

# Then reconfigure
`agent kg init --provider neo4j
```

---

## Troubleshooting

### Issue: "Connection refused" Error

**Problem:** Provider is not running.

**Solution:**
```bash
# For LightRAG
docker ps | grep lightrag
docker start keel-lightrag

# For Neo4j
docker ps | grep neo4j
docker start neo4j

# Then retry
`agent kg clear
```

### Issue: "Authentication failed" Error

**Problem:** Invalid credentials for Neo4j.

**Solution:**
```bash
# Reconfigure with correct credentials
`agent kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password

# Then retry
`agent kg clear --provider neo4j
```

### Issue: Stats Show Non-Zero After Clearing

**Problem:** Clear operation may have failed partially.

**Solution:**
```bash
# For LightRAG: Restart container
docker restart keel-lightrag

# For Neo4j: Run Cypher directly
# Open http://localhost:7474 and run:
MATCH (n) DETACH DELETE n

# Verify
`agent kg stats
```

### Issue: "Provider not configured" Error

**Problem:** No provider configured.

**Solution:**
```bash
# Configure a provider first
`agent kg init --provider lightrag --lightrag-url http://localhost:8001

# Then clear
`agent kg clear
```

### Issue: Timeout During Clear

**Problem:** Large dataset taking too long.

**Solution:**
```bash
# For LightRAG: Increase timeout
`agent kg init --provider lightrag --lightrag-timeout 600

# For Neo4j: Clear in batches (manual)
# Open http://localhost:7474 and run:
CALL apoc.periodic.iterate(
  "MATCH (n) RETURN n",
  "DETACH DELETE n",
  {batchSize: 1000}
)
```

---

## Comparison with Alternatives

### vs. Docker Reset

| Method | Speed | Safety | Preserves Config |
|--------|-------|--------|------------------|
| `keel kg clear` | Fast | ✅ Safe | ✅ Yes |
| Docker reset | Slow | ⚠️ Risky | ❌ No |

**Docker reset:**
```bash
docker stop keel-lightrag
docker rm keel-lightrag
docker volume rm keel-lightrag-data
# Loses all configuration
```

### vs. Manual Cypher

| Method | Ease | Safety | Multi-Provider |
|--------|------|--------|----------------|
| `keel kg clear` | ✅ Easy | ✅ Safe | ✅ Yes |
| Manual Cypher | ⚠️ Complex | ⚠️ Risky | ❌ No |

**Manual Cypher:**
```cypher
// Must know exact syntax
MATCH (n) DETACH DELETE n
// No confirmation, no stats
```

### vs. API Calls

| Method | Ease | Safety | Consistency |
|--------|------|--------|-------------|
| `keel kg clear` | ✅ Easy | ✅ Safe | ✅ Yes |
| Direct API | ⚠️ Complex | ⚠️ Risky | ⚠️ Varies |

**Direct API:**
```bash
# Must know endpoint
curl -X DELETE http://localhost:8001/clear
# No confirmation, no stats
```

---

## Integration Examples

### Python Script

```python
import subprocess

def clear_kg(provider="lightrag", confirm=True):
    """Clear knowledge graph data."""
    cmd = ["keel", "kg", "clear", "--provider", provider]
    
    if not confirm:
        cmd.append("--yes")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Cleared {provider}")
    else:
        print(f"✗ Error: {result.stderr}")
    
    return result.returncode == 0

# Usage
clear_kg("lightrag", confirm=False)
```

### Bash Script

```bash
#!/bin/bash
# clear-and-reingest.sh

set -e

echo "Clearing existing data..."
`agent kg clear --provider lightrag --yes

echo "Re-ingesting data..."
`agent kg async submit --source cwow-patient-model --provider lightrag

echo "Waiting for ingestion to complete..."
sleep 60

echo "Checking stats..."
`agent kg stats

echo "Done!"
```

### Makefile

```makefile
.PHONY: clear-kg reingest test-kg

clear-kg:
	keel kg clear --provider lightrag --yes

reingest: clear-kg
	keel kg async submit --source my-data --provider lightrag

test-kg: clear-kg
	keel kg ingest --path test-data.pdf
	pytest tests/test_kg.py
	keel kg clear --yes
```

---

## Performance

### Clearing Speed

| Provider | Data Size | Time | Notes |
|----------|-----------|------|-------|
| LightRAG | 1K docs | ~2s | Fast API call |
| LightRAG | 10K docs | ~5s | Clears vectors |
| LightRAG | 100K docs | ~15s | Larger datasets |
| Neo4j | 1K nodes | ~1s | Single query |
| Neo4j | 10K nodes | ~3s | Atomic delete |
| Neo4j | 100K nodes | ~10s | May need batching |

### Stats Overhead

- **With stats:** +2-5 seconds (fetches before/after)
- **Without stats:** Immediate (just clears)

**Recommendation:** Use `--no-show-stats` for automated scripts.

---

## Security Considerations

### 1. Confirmation Required

Default behavior requires explicit confirmation to prevent accidental deletion.

### 2. No Selective Deletion

Currently clears ALL data. Cannot selectively delete:
- ❌ By persona
- ❌ By source
- ❌ By date range

**Future enhancement:** Add selective clearing options.

### 3. No Backup

Command does not create automatic backups. Always backup manually before clearing production data.

### 4. Irreversible

Once cleared, data cannot be recovered unless you have backups.

---

## Future Enhancements

### Planned Features

1. **Selective Clearing**
   ```bash
   agent kg clear --persona developer
   agent kg clear --source cwow-patient-model
   agent kg clear --before 2025-01-01
   ```

2. **Automatic Backup**
   ```bash
   agent kg clear --backup
   # Creates backup before clearing
   ```

3. **Dry Run**
   ```bash
   agent kg clear --dry-run
   # Shows what would be deleted without actually deleting
   ```

4. **Progress Indicator**
   ```bash
   agent kg clear
   # Clearing: [████████████████████] 100% (8006/8006 entities)
   ```

5. **Restore Command**
   ```bash
   agent kg restore --backup backup-20250127.tar.gz
   ```

---

## Summary

The `keel kg clear` command provides:

✅ **Safe deletion** with confirmation prompts  
✅ **Multi-provider support** (Neo4j, LightRAG, both)  
✅ **Before/after statistics** for verification  
✅ **Automation-friendly** with `--yes` flag  
✅ **Error handling** with clear messages  
✅ **Consistent behavior** across providers  

**Use when:**
- Testing and development
- Re-ingesting data
- Removing duplicates
- Switching providers
- Cleaning up after experiments

**Avoid when:**
- Working with production data without backups
- Unsure about what you're deleting
- Need selective deletion (not yet supported)
