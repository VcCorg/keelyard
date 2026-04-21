# Unified Ingestion Tracking

## Summary

Refactored the ingestion system to track **all ingestion operations** (both sync and async) in a unified tracking system. The `--async` flag is now a parameter of the main `ingest` command rather than a separate subcommand structure.

---

## Key Changes

### 1. **Unified Tracking System**

All ingestion operations are now tracked in a single system:
- **Sync operations**: Run in foreground, tracked with `is_async=False`
- **Async operations**: Run in background, tracked with `is_async=True`

### 2. **Simplified Command Structure**

**Before**:
```bash
dva kg ingest --path /data              # Sync (not tracked)
dva kg async submit --path /data        # Async (tracked separately)
dva kg async list                       # Only async operations
```

**After**:
```bash
dva kg ingest --path /data              # Sync (tracked)
dva kg ingest --path /data --async      # Async (tracked)
dva kg ingest-list                      # All operations (sync + async)
```

### 3. **New Commands**

| Command | Description |
|---------|-------------|
| `dva kg ingest --async` | Run ingestion asynchronously |
| `dva kg ingest-list` | List all ingestion operations |
| `dva kg ingest-status <id>` | Check operation status |
| `dva kg ingest-cancel <id>` | Cancel async operation |

---

## Architecture

### Data Model

**IngestionJob** now includes:
```python
class IngestionJob(BaseModel):
    job_id: str
    source: str
    provider: str
    status: JobStatus  # pending, running, completed, failed, cancelled
    is_async: bool     # NEW: True for async, False for sync
    workspace: str     # NEW: Target workspace (LightRAG only)
    created_at: datetime
    started_at: datetime
    completed_at: datetime
    duration: float
    error: str
    result: dict
    metadata: dict
```

### Tracking Flow

#### Sync Ingestion
```
1. User runs: dva kg ingest --path /data
2. Create job record (is_async=False, status=pending)
3. Update status to running
4. Execute ingestion
5. Update status to completed/failed
6. Store result/error
```

#### Async Ingestion
```
1. User runs: dva kg ingest --path /data --async
2. Create job record (is_async=True, status=pending)
3. Submit to background worker
4. Return immediately with job ID
5. Worker updates status as it progresses
6. User can check status anytime
```

---

## Usage Examples

### Basic Ingestion (Sync)

```bash
# Sync ingestion (default)
dva kg ingest --path /data/documents

# Tracked automatically
dva kg ingest-list --sync-only
```

### Async Ingestion

```bash
# Submit async job
dva kg ingest --path /data/large-dataset --async

# Output:
# ✓ Ingestion job submitted (async)
# Job ID: abc123...
# Status: pending
# 
# Check status: dva kg ingest-list
# View details: dva kg ingest-status abc123
```

### List Operations

```bash
# List all operations
dva kg ingest-list

# Filter by mode
dva kg ingest-list --sync-only
dva kg ingest-list --async-only

# Filter by status
dva kg ingest-list --status completed
dva kg ingest-list --status running
dva kg ingest-list --status failed

# Limit results
dva kg ingest-list --limit 10
```

### Check Status

```bash
# Full job ID
dva kg ingest-status abc123-def456-...

# Partial job ID (prefix matching)
dva kg ingest-status abc123

# Verbose output
dva kg ingest-status abc123 --verbose
```

### Cancel Operation

```bash
# Cancel async operation
dva kg ingest-cancel abc123

# Note: Cannot cancel sync operations
# (they run in foreground)
```

---

## Command Reference

### `dva kg ingest`

**Options**:
- `--path TEXT`: Direct path to data source
- `--source TEXT`: Data source name (from `dva data create`)
- `--format TEXT`: Source format (auto-detected if not specified)
- `--workspace TEXT`: Target workspace (LightRAG only)
- `--async`: Run asynchronously in background
- `--extract-entities`: Extract entities using LLM
- `--build-relationships`: Build relationships between entities
- `--recursive`: Recursively process subdirectories
- `--detailed-analysis`: Perform detailed code analysis for Git repos

**Examples**:
```bash
# Sync ingestion
dva kg ingest --path /data/file.pdf

# Async ingestion
dva kg ingest --path /data/large-dataset --async

# With workspace
dva kg ingest --path /data --workspace production --async

# From data source
dva kg ingest --source my-dataset --async
```

### `dva kg ingest-list`

**Options**:
- `--status TEXT`: Filter by status (pending, running, completed, failed, cancelled)
- `--async-only`: Show only async operations
- `--sync-only`: Show only sync operations
- `--limit INT`: Maximum number of operations to show (default: 20)

**Examples**:
```bash
# All operations
dva kg ingest-list

# Only sync operations
dva kg ingest-list --sync-only

# Only async operations
dva kg ingest-list --async-only

# Filter by status
dva kg ingest-list --status running
dva kg ingest-list --status completed

# Combined filters
dva kg ingest-list --async-only --status failed --limit 5
```

**Output**:
```
Ingestion Operations (10)
┏━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Job ID   ┃ Mode ┃ Status    ┃ Provider ┃ Source             ┃ Created          ┃ Duration ┃
┡━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ fd4f5143 │ async│ running   │ lightrag │ /tmp/test.txt      │ 2025-11-30 11:19 │    9s... │
│ c60202b1 │ sync │ completed │ lightrag │ /data/file.pdf     │ 2025-11-30 11:17 │     9.5s │
└──────────┴──────┴───────────┴──────────┴────────────────────┴──────────────────┴──────────┘
```

### `dva kg ingest-status`

**Arguments**:
- `job_id`: Job ID to check (supports partial ID matching)

**Options**:
- `--verbose, -v`: Show detailed information including metadata and results

**Examples**:
```bash
# Basic status
dva kg ingest-status abc123

# Verbose output
dva kg ingest-status abc123 --verbose
```

**Output**:
```
╭─────────────────────── Ingestion Operation abc123 ───────────────────────╮
│ Job ID: abc123-def456-...                                                │
│ Mode: Async                                                              │
│ Status: completed                                                        │
│ Provider: lightrag                                                       │
│ Source: /data/documents                                                  │
│ Format: directory                                                        │
│ Created: 2025-11-30 11:19:29                                             │
│ Started: 2025-11-30 11:19:29                                             │
│ Completed: 2025-11-30 11:19:48                                           │
│ Duration: 18.5s                                                          │
│ Workspace: production                                                    │
╰──────────────────────────────────────────────────────────────────────────╯
```

### `dva kg ingest-cancel`

**Arguments**:
- `job_id`: Job ID to cancel (async operations only)

**Examples**:
```bash
# Cancel async operation
dva kg ingest-cancel abc123

# Error if sync operation
dva kg ingest-cancel xyz789
# ⚠ Cannot cancel sync operation
# Sync operations run in foreground and cannot be cancelled
```

---

## Benefits

### 1. **Complete Visibility**

Track all ingestion operations in one place:
```bash
dva kg ingest-list
# Shows both sync and async operations
```

### 2. **Consistent Interface**

Single command for both modes:
```bash
dva kg ingest --path /data           # Sync
dva kg ingest --path /data --async   # Async
```

### 3. **Better Debugging**

View history of all operations:
```bash
# See what failed
dva kg ingest-list --status failed

# Check specific operation
dva kg ingest-status abc123 --verbose
```

### 4. **Performance Monitoring**

Track duration of all operations:
```bash
dva kg ingest-list
# Duration column shows how long each operation took
```

### 5. **Workspace Tracking**

See which workspace was used:
```bash
dva kg ingest-status abc123
# Workspace: production
```

---

## Implementation Details

### Files Modified

1. **`async_ingest.py`**:
   - Added `is_async` and `workspace` fields to `IngestionJob`
   - Updated `create_job()` to accept these parameters
   - Added partial ID matching to `get_job()`

2. **`kg.py`**:
   - Added `--async` flag to `ingest` command
   - Added job tracking for sync operations
   - Created `ingest-list`, `ingest-status`, `ingest-cancel` commands
   - Updated completion/failure tracking

3. **`kg_ingest.py`**:
   - Deprecated (async subcommands no longer used)
   - Functionality moved to main `kg.py`

### Storage

Operations are stored in:
```
~/.dva-agentic/jobs/
├── abc123-def456-....json
├── xyz789-abc123-....json
└── ...
```

Each job file contains:
```json
{
  "job_id": "abc123-def456-...",
  "source": "/data/documents",
  "provider": "lightrag",
  "status": "completed",
  "is_async": false,
  "workspace": "production",
  "created_at": "2025-11-30T11:19:29Z",
  "started_at": "2025-11-30T11:19:29Z",
  "completed_at": "2025-11-30T11:19:48Z",
  "duration": 18.5,
  "result": {...},
  "metadata": {...}
}
```

---

## Migration Guide

### For Users

**Old workflow**:
```bash
# Async ingestion
dva kg async submit --path /data
dva kg async list
dva kg async status abc123
```

**New workflow**:
```bash
# Async ingestion
dva kg ingest --path /data --async
dva kg ingest-list
dva kg ingest-status abc123
```

### For Scripts

Update any automation scripts:
```bash
# Old
if dva kg async submit --path /data; then
    echo "Submitted"
fi

# New
if dva kg ingest --path /data --async; then
    echo "Submitted"
fi
```

---

## Future Enhancements

### 1. **Cleanup Command**

```bash
dva kg ingest-cleanup --days 30
# Delete operations older than 30 days
```

### 2. **Export/Import**

```bash
dva kg ingest-export --output operations.json
dva kg ingest-import --input operations.json
```

### 3. **Statistics**

```bash
dva kg ingest-stats
# Show aggregated statistics:
# - Total operations
# - Success rate
# - Average duration
# - By provider
# - By workspace
```

### 4. **Retry Failed Operations**

```bash
dva kg ingest-retry abc123
# Retry a failed operation
```

### 5. **Batch Operations**

```bash
dva kg ingest-batch --sources file1,file2,file3 --async
# Submit multiple operations at once
```

---

## Testing

### Test Sync Ingestion

```bash
# Create test file
echo "Test document" > /tmp/test.txt

# Run sync ingestion
dva kg ingest --path /tmp/test.txt

# Verify tracking
dva kg ingest-list --sync-only
```

### Test Async Ingestion

```bash
# Submit async job
dva kg ingest --path /tmp/test.txt --async

# Check status immediately
dva kg ingest-status <job-id>

# Wait and check again
sleep 10
dva kg ingest-status <job-id>
```

### Test Filtering

```bash
# All operations
dva kg ingest-list

# Only sync
dva kg ingest-list --sync-only

# Only async
dva kg ingest-list --async-only

# By status
dva kg ingest-list --status completed
dva kg ingest-list --status running
```

### Test Partial ID Matching

```bash
# Get job ID from list
dva kg ingest-list --limit 1

# Use first 8 characters
dva kg ingest-status abc12345
```

---

## Summary

✅ **Unified tracking for all ingestion operations**  
✅ **Simple `--async` flag instead of separate commands**  
✅ **Complete visibility into sync and async operations**  
✅ **Consistent command interface**  
✅ **Better debugging and monitoring**  
✅ **Workspace tracking**  
✅ **Partial ID matching for convenience**  

The refactoring provides a cleaner, more intuitive interface for managing ingestion operations while maintaining full backward compatibility for the core ingestion functionality.
