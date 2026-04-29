# Ingest Command Refactoring

## Summary

Refactored the ingestion system to use a cleaner command group structure with `submit`, `list`, `status`, and `cancel` subcommands. All ingestion operations (sync and async) are tracked in a unified system.

---

## New Command Structure

### Before (Confusing)
```bash
`agent kg ingest --path /data              # Main ingest command
`agent kg ingest-list                      # Separate list command
`agent kg ingest-status <id>               # Separate status command
`agent kg ingest-cancel <id>               # Separate cancel command
```

### After (Clean)
```bash
`agent kg ingest submit --path /data       # Submit ingestion
`agent kg ingest list                      # List all operations
`agent kg ingest status <id>               # Check status
`agent kg ingest cancel <id>               # Cancel operation
```

---

## Command Reference

### `dva kg ingest`

Main command group for all ingestion operations.

```bash
$ agent kg ingest --help

Usage: agent kg ingest [OPTIONS] COMMAND [ARGS]...

  Data ingestion commands

Commands:
  submit  Submit data for ingestion into the knowledge graph
  list    List all ingestion operations (sync and async)
  status  Check the status of an ingestion operation
  cancel  Cancel a running or pending ingestion operation
```

---

### `dva kg ingest submit`

Submit data for ingestion (sync or async).

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
# Sync ingestion (default)
`agent kg ingest submit --path /data/file.pdf

# Async ingestion
`agent kg ingest submit --path /data/large-dataset --async

# With workspace
`agent kg ingest submit --path /data --workspace production --async

# From data source
`agent kg ingest submit --source my-dataset --async

# Git repository
`agent kg ingest submit --source backend-repo --async
```

---

### `dva kg ingest list`

List all ingestion operations (sync and async).

**Options**:
- `--status TEXT`: Filter by status (pending, running, completed, failed, cancelled)
- `--async-only`: Show only async operations
- `--sync-only`: Show only sync operations
- `--limit INT`: Maximum number of operations to show (default: 20)

**Examples**:

```bash
# All operations
`agent kg ingest list

# Only sync operations
`agent kg ingest list --sync-only

# Only async operations
`agent kg ingest list --async-only

# Filter by status
`agent kg ingest list --status running
`agent kg ingest list --status completed
`agent kg ingest list --status failed

# Combined filters
`agent kg ingest list --async-only --status running --limit 10
```

**Output**:
```
Ingestion Operations (5)
┏━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Job ID   ┃ Mode  ┃ Status    ┃ Provider ┃ Source              ┃ Created          ┃ Duration ┃
┡━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ ca67f3ef │ async │ running   │ lightrag │ /tmp/test.txt       │ 2025-11-30 11:28 │   10s... │
│ 4f9c8ce7 │ sync  │ completed │ lightrag │ /data/file.pdf      │ 2025-11-30 11:28 │    22.0s │
│ fd4f5143 │ async │ completed │ lightrag │ /data/large-set     │ 2025-11-30 11:19 │    18.5s │
└──────────┴───────┴───────────┴──────────┴─────────────────────┴──────────────────┴──────────┘

View details: agent kg ingest status <job-id>
```

---

### `dva kg ingest status`

Check the status of an ingestion operation.

**Arguments**:
- `job_id`: Job ID to check (supports partial ID matching)

**Options**:
- `--verbose, -v`: Show detailed information including metadata and results

**Examples**:

```bash
# Basic status
`agent kg ingest status ca67f3ef

# Full job ID
`agent kg ingest status ca67f3ef-5a9e-49fa-bde6-51ba66ae58c5

# Verbose output
`agent kg ingest status ca67f3ef --verbose
```

**Output**:
```
╭─────────────────────── Ingestion Operation ca67f3ef ───────────────────────╮
│ Job ID: ca67f3ef-5a9e-49fa-bde6-51ba66ae58c5                              │
│ Mode: Async                                                                │
│ Status: completed                                                          │
│ Provider: lightrag                                                         │
│ Source: /tmp/test.txt                                                      │
│ Format: auto-detect                                                        │
│ Created: 2025-11-30 11:28:15                                               │
│ Started: 2025-11-30 11:28:15                                               │
│ Completed: 2025-11-30 11:28:33                                             │
│ Duration: 18.0s                                                            │
│ Workspace: production                                                      │
╰────────────────────────────────────────────────────────────────────────────╯
```

---

### `dva kg ingest cancel`

Cancel a running or pending ingestion operation.

**Arguments**:
- `job_id`: Job ID to cancel

**Notes**:
- Only async operations can be cancelled
- Sync operations run in foreground and cannot be cancelled
- Can cancel from different terminal

**Examples**:

```bash
# Cancel async operation
`agent kg ingest cancel ca67f3ef

# Error if sync operation
`agent kg ingest cancel 4f9c8ce7
# ⚠ Cannot cancel sync operation
# Sync operations run in foreground and cannot be cancelled
```

---

## Benefits

### 1. **Cleaner Command Structure**

All ingestion-related commands are grouped under `ingest`:
```
`agent kg ingest
├── submit   (submit ingestion)
├── list     (list operations)
├── status   (check status)
└── cancel   (cancel operation)
```

### 2. **Intuitive Workflow**

```bash
# Submit
`agent kg ingest submit --path /data --async

# List
`agent kg ingest list

# Status
`agent kg ingest status abc123

# Cancel
`agent kg ingest cancel abc123
```

### 3. **Unified Tracking**

Both sync and async operations tracked together:
```bash
`agent kg ingest list
# Shows both sync and async with mode column
```

### 4. **Consistent Interface**

All commands follow the same pattern:
```bash
`agent kg ingest <subcommand> [options]
```

### 5. **Partial ID Matching**

Convenience feature for status and cancel:
```bash
# Full ID
`agent kg ingest status ca67f3ef-5a9e-49fa-bde6-51ba66ae58c5

# Partial ID (first 8 chars)
`agent kg ingest status ca67f3ef
```

---

## Implementation Details

### Files Modified

1. **`kg.py`**:
   - Created `ingest_app` Typer group
   - Renamed `ingest()` to `ingest_submit()`
   - Moved `ingest-list` to `ingest list`
   - Moved `ingest-status` to `ingest status`
   - Moved `ingest-cancel` to `ingest cancel`

2. **`async_ingest.py`**:
   - Added `is_async` field to `IngestionJob`
   - Added `workspace` field to `IngestionJob`
   - Updated `create_job()` to accept these parameters
   - Added partial ID matching to `get_job()`
   - Added `get_job()`, `list_jobs()`, `cancel_job()` to manager

### Data Model

```python
class IngestionJob(BaseModel):
    job_id: str
    source: str
    provider: str
    status: JobStatus
    is_async: bool      # True for async, False for sync
    workspace: str      # Target workspace (LightRAG only)
    created_at: datetime
    started_at: datetime
    completed_at: datetime
    duration: float
    error: str
    result: dict
    metadata: dict
```

### Storage

Operations stored in:
```
~/.dva-agentic/jobs/
├── ca67f3ef-5a9e-49fa-bde6-51ba66ae58c5.json
├── 4f9c8ce7-1234-5678-abcd-ef1234567890.json
└── ...
```

---

## Usage Examples

### Basic Workflow

```bash
# 1. Submit sync ingestion
`agent kg ingest submit --path /data/file.pdf

# 2. Submit async ingestion
`agent kg ingest submit --path /data/large-dataset --async

# 3. List all operations
`agent kg ingest list

# 4. Check specific operation
`agent kg ingest status abc123

# 5. Cancel if needed
`agent kg ingest cancel abc123
```

### Advanced Filtering

```bash
# Show only running operations
`agent kg ingest list --status running

# Show only async operations
`agent kg ingest list --async-only

# Show only failed sync operations
`agent kg ingest list --sync-only --status failed

# Show last 5 completed operations
`agent kg ingest list --status completed --limit 5
```

### With Workspaces

```bash
# Submit to specific workspace
`agent kg ingest submit --path /data --workspace production --async

# List shows workspace
`agent kg ingest list

# Status shows workspace
`agent kg ingest status abc123
```

### With Data Sources

```bash
# Create data source
`agent data create --name my-docs --source-type doc --source-location /data/docs

# Ingest from data source
`agent kg ingest submit --source my-docs --async

# Track operation
`agent kg ingest list
`agent kg ingest status abc123
```

---

## Migration Guide

### Old Commands → New Commands

| Old Command | New Command |
|-------------|-------------|
| `dva kg ingest --path /data` | `dva kg ingest submit --path /data` |
| `dva kg ingest --path /data --async` | `dva kg ingest submit --path /data --async` |
| `dva kg ingest-list` | `dva kg ingest list` |
| `dva kg ingest-status <id>` | `dva kg ingest status <id>` |
| `dva kg ingest-cancel <id>` | `dva kg ingest cancel <id>` |

### Update Scripts

```bash
# Old
`agent kg ingest --path /data --async
`agent kg ingest-list
`agent kg ingest-status abc123

# New
`agent kg ingest submit --path /data --async
`agent kg ingest list
`agent kg ingest status abc123
```

---

## Testing

### Test Sync Ingestion

```bash
# Create test file
echo "Test document" > /tmp/test.txt

# Submit sync
`agent kg ingest submit --path /tmp/test.txt

# Verify tracking
`agent kg ingest list --sync-only
```

### Test Async Ingestion

```bash
# Submit async
`agent kg ingest submit --path /tmp/test.txt --async

# Check immediately
`agent kg ingest status <job-id>

# Wait and check again
sleep 10
`agent kg ingest status <job-id>
```

### Test Filtering

```bash
# All operations
`agent kg ingest list

# Only sync
`agent kg ingest list --sync-only

# Only async
`agent kg ingest list --async-only

# By status
`agent kg ingest list --status completed
`agent kg ingest list --status running
```

### Test Partial ID

```bash
# Get job ID
`agent kg ingest list --limit 1

# Use first 8 characters
`agent kg ingest status ca67f3ef
```

---

## Comparison

### Before (Confusing)

```
`agent kg
├── ingest (main command with --async flag)
├── ingest-list (separate command)
├── ingest-status (separate command)
└── ingest-cancel (separate command)
```

**Problems**:
- Inconsistent naming (`ingest` vs `ingest-list`)
- Not clear that list/status/cancel are related to ingest
- Harder to discover related commands

### After (Clean)

```
`agent kg
└── ingest (command group)
    ├── submit (submit ingestion)
    ├── list (list operations)
    ├── status (check status)
    └── cancel (cancel operation)
```

**Benefits**:
- Clear hierarchy
- All ingest commands grouped together
- Easy to discover with `dva kg ingest --help`
- Consistent naming pattern

---

## Summary

✅ **Cleaner command structure** with logical grouping  
✅ **Intuitive workflow** with submit/list/status/cancel  
✅ **Unified tracking** for sync and async operations  
✅ **Consistent interface** across all commands  
✅ **Partial ID matching** for convenience  
✅ **Better discoverability** with command groups  

The refactoring provides a much cleaner and more intuitive interface for managing ingestion operations, following industry-standard CLI patterns (similar to `kubectl`, `docker`, `git`, etc.).
