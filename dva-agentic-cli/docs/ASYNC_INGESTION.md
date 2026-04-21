# Asynchronous Knowledge Graph Ingestion

## Overview

The DVA KG CLI now supports **asynchronous, parallel ingestion** of documents into both Neo4j and LightRAG knowledge graphs. This allows you to:

- ✅ Ingest large datasets without blocking the CLI
- ✅ Process multiple repositories in parallel
- ✅ Ingest to both Neo4j and LightRAG simultaneously
- ✅ Track ingestion progress and status
- ✅ Resume work while ingestion runs in background

---

## Architecture

### Components

1. **AsyncIngestionManager** - Manages background ingestion workers
2. **JobQueue** - Tracks job status and persists to disk
3. **ThreadPoolExecutor** - Executes ingestion jobs in parallel threads
4. **CLI Commands** - User interface for job management

### Data Flow

```
User submits job → JobQueue creates job → ThreadPoolExecutor runs ingestion
                                                    ↓
                                          Ingest to Neo4j (optional)
                                                    ↓
                                          Ingest to LightRAG (optional)
                                                    ↓
                                          Update job status → Save to disk
```

### Job Storage

Jobs are persisted to: `~/.dva-agentic/jobs/<job_id>.json`

This allows:
- Job status survives CLI restarts
- Historical job tracking
- Resume monitoring after disconnection

---

## CLI Commands

### 1. Submit Ingestion Job

```bash
# Submit single file
dva kg async submit --path /path/to/file.pdf

# Submit directory (recursive)
dva kg async submit --path /path/to/docs --provider both

# Submit data source
dva kg async submit --source my-dataset --provider lightrag

# Submit and wait for completion
dva kg async submit --path /docs --wait

# Submit to both providers
dva kg async submit --source cwow-patient-docs --provider both
```

**Options:**
- `--path` - Direct path to file or directory
- `--source` - Data source name (configured via `dva data create`)
- `--provider` - Target: `neo4j`, `lightrag`, or `both` (default: lightrag)
- `--format` - Force format (auto-detected if not specified)
- `--extract-entities` - Extract entities with LLM (Neo4j only, default: true)
- `--build-relationships` - Build entity relationships (Neo4j only, default: true)
- `--recursive` - Process subdirectories (default: true)
- `--wait` - Block until job completes

### 2. Check Job Status

```bash
# Check specific job
dva kg async status abc123-def456

# Verbose output with full details
dva kg async status abc123-def456 --verbose
```

**Output:**
- Job ID and source
- Current status (pending, running, completed, failed)
- Timestamps (created, started, completed)
- Duration
- Progress information
- Results (if completed)
- Error message (if failed)

### 3. List Jobs

```bash
# List all jobs (last 20)
dva kg async list

# List only running jobs
dva kg async list --status running

# List last 50 jobs
dva kg async list --limit 50

# Filter by status
dva kg async list --status completed
dva kg async list --status failed
```

**Status Values:**
- `pending` - Job queued, not started
- `running` - Currently processing
- `completed` - Successfully finished
- `failed` - Error occurred
- `cancelled` - User cancelled

### 4. Cancel Job

```bash
# Cancel a job
dva kg async cancel abc123-def456
```

**Note:** Running jobs cannot be immediately stopped but will be marked for cancellation.

### 5. Cleanup Old Jobs

```bash
# Delete completed/failed jobs older than 30 days
dva kg async cleanup

# Custom retention period
dva kg async cleanup --days 7

# Skip confirmation
dva kg async cleanup --days 7 --force
```

---

## Usage Examples

### Example 1: Parallel Multi-Repository Ingestion

```bash
# Submit multiple repos in parallel
dva kg async submit --source backend-repo --provider both
dva kg async submit --source frontend-repo --provider both
dva kg async submit --source api-docs --provider lightrag

# Check status
dva kg async list --status running

# Monitor specific job
dva kg async status <job-id> --verbose
```

### Example 2: Large Document Collection

```bash
# Submit large directory for background processing
dva kg async submit --path /data/medical-records --provider lightrag

# Continue working while ingestion runs
dva kg query "patient information"

# Check progress later
dva kg async status <job-id>
```

### Example 3: Dual Provider Ingestion

```bash
# Ingest to both Neo4j and LightRAG
dva kg async submit --source cwow-patient-docs --provider both --wait

# Results will show stats for both providers
```

---

## Infrastructure Support

### LightRAG Concurrent Operations

**Supported:** ✅ Yes

LightRAG's HTTP API is stateless and thread-safe:
- Multiple concurrent `POST /insert` requests are handled independently
- Each request processes documents atomically
- No shared state between requests
- FastAPI handles concurrent requests via async workers

**Validation:**
```bash
# Test concurrent inserts
curl -X POST http://localhost:8001/insert -d '{"text":"doc1"}' &
curl -X POST http://localhost:8001/insert -d '{"text":"doc2"}' &
curl -X POST http://localhost:8001/insert -d '{"text":"doc3"}' &
```

### Neo4j Concurrent Operations

**Supported:** ✅ Yes

Neo4j is designed for concurrent access:
- ACID transactions ensure data consistency
- Multiple concurrent sessions are supported
- Connection pooling handles parallel requests
- Write locks prevent conflicts

**Best Practices:**
- Use separate sessions per thread (handled automatically)
- Batch operations within transactions
- Monitor connection pool size

**Configuration:**
```python
# Neo4j driver handles concurrency automatically
driver = GraphDatabase.driver(uri, auth=(user, password))
# Connection pool size: default 100
```

---

## Performance Considerations

### Parallel Workers

Default: **4 workers**

Adjust based on:
- CPU cores available
- Network bandwidth
- Target system capacity (Neo4j/LightRAG)
- Document size and complexity

**Modify in code:**
```python
manager = AsyncIngestionManager(max_workers=8)
```

### Memory Usage

Each worker processes one job at a time:
- **Small files** (< 1MB): ~50-100MB per worker
- **Large files** (> 10MB): ~500MB-1GB per worker
- **Directories**: Depends on file count and size

**Recommendation:** Start with 4 workers, monitor memory, adjust as needed.

### Throughput Estimates

Based on typical document sizes:

| Document Type | Size | Throughput (4 workers) |
|--------------|------|------------------------|
| Text files | 10KB | ~1000 docs/min |
| PDFs | 1MB | ~100 docs/min |
| Large PDFs | 10MB | ~20 docs/min |
| Code repos | 50MB | ~5 repos/min |

**Factors affecting speed:**
- Entity extraction (LLM calls)
- Network latency
- Target system write speed
- Document complexity

---

## Job Status Lifecycle

```
PENDING → RUNNING → COMPLETED
                 ↓
                FAILED
                 ↓
              CANCELLED
```

### Status Transitions

1. **PENDING** - Job created, waiting for worker
2. **RUNNING** - Worker processing job
3. **COMPLETED** - Successfully finished
4. **FAILED** - Error occurred during processing
5. **CANCELLED** - User cancelled before completion

### Progress Tracking

Jobs track progress through stages:
- `neo4j` - Ingesting to Neo4j
- `lightrag` - Ingesting to LightRAG
- `completed` - All stages finished
- `failed` - Error in specific stage

---

## Error Handling

### Automatic Retry

Currently: **No automatic retry**

Failed jobs remain in FAILED status. To retry:
```bash
# Check error
dva kg async status <job-id>

# Resubmit with same parameters
dva kg async submit --source <source> --provider <provider>
```

### Common Errors

1. **Connection refused**
   - Cause: Neo4j or LightRAG not running
   - Fix: Start infrastructure, resubmit job

2. **Timeout**
   - Cause: Large document, slow LLM
   - Fix: Increase timeout, split documents

3. **Out of memory**
   - Cause: Too many workers, large files
   - Fix: Reduce workers, process in batches

4. **Invalid format**
   - Cause: Unsupported file type
   - Fix: Convert to supported format

---

## Monitoring

### Real-time Monitoring

```bash
# Watch running jobs
watch -n 5 'dva kg async list --status running'

# Monitor specific job
watch -n 2 'dva kg async status <job-id>'
```

### Logs

Application logs include:
- Job submission
- Worker start/stop
- Progress updates
- Errors and warnings

**Location:** Check CLI output or configure logging

---

## Best Practices

### 1. Use Data Sources

Configure sources once, reuse many times:
```bash
# Configure
dva data create --name medical-docs --source-type doc --source-location /data/medical

# Use repeatedly
dva kg async submit --source medical-docs --provider lightrag
dva kg async submit --source medical-docs --provider neo4j
```

### 2. Batch Related Documents

Group related documents in directories:
```
/data/
  ├── patient-records/
  ├── clinical-guidelines/
  └── research-papers/
```

Submit each directory as separate job for better tracking.

### 3. Choose Provider Wisely

- **LightRAG only**: Fast, simple queries, large datasets
- **Neo4j only**: Complex relationships, graph analytics
- **Both**: Maximum flexibility, redundancy

### 4. Monitor Resource Usage

```bash
# Check system resources
htop

# Check Neo4j memory
docker stats dva-neo4j

# Check LightRAG
docker stats dva-lightrag
```

### 5. Clean Up Regularly

```bash
# Weekly cleanup
dva kg async cleanup --days 7

# Monthly cleanup
dva kg async cleanup --days 30
```

---

## Troubleshooting

### Jobs Stuck in PENDING

**Cause:** All workers busy

**Solution:**
```bash
# Check running jobs
dva kg async list --status running

# Wait for completion or cancel
dva kg async cancel <job-id>
```

### Jobs Failing Immediately

**Cause:** Infrastructure not available

**Solution:**
```bash
# Check Neo4j
docker ps | grep neo4j

# Check LightRAG
curl http://localhost:8001/health

# Restart if needed
cd neo4j-infrastructure && make restart
cd lightrag-infrastructure && make restart
```

### Slow Ingestion

**Cause:** Large files, entity extraction

**Solution:**
- Disable entity extraction: `--no-extract-entities`
- Use LightRAG only: `--provider lightrag`
- Split large files into smaller chunks
- Increase workers (if resources available)

---

## API Reference

### AsyncIngestionManager

```python
from dva_agentic_cli.kg.async_ingest import get_manager

manager = get_manager(max_workers=4)

# Submit job
job = manager.submit_ingestion(
    source="/path/to/docs",
    provider="lightrag",
    recursive=True
)

# Check status
status = manager.get_job_status(job.job_id)

# Wait for completion
completed = manager.wait_for_job(job.job_id, timeout=3600)

# List jobs
jobs = manager.list_jobs(status=JobStatus.RUNNING)

# Cancel job
manager.cancel_job(job.job_id)
```

### IngestionJob Model

```python
class IngestionJob:
    job_id: str
    source: str
    source_type: str
    format: Optional[str]
    provider: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    progress: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
```

---

## Future Enhancements

### Planned Features

- [ ] Automatic retry with exponential backoff
- [ ] Job priorities and scheduling
- [ ] Distributed workers across multiple machines
- [ ] Real-time progress streaming
- [ ] Job dependencies and workflows
- [ ] Email/webhook notifications
- [ ] Resource usage tracking
- [ ] Incremental ingestion (skip duplicates)

### Contributions Welcome

See `CONTRIBUTING.md` for guidelines.

---

## Summary

The async ingestion system provides:

✅ **Non-blocking** - Continue working while ingestion runs
✅ **Parallel** - Process multiple sources simultaneously  
✅ **Persistent** - Jobs survive CLI restarts
✅ **Flexible** - Support both Neo4j and LightRAG
✅ **Trackable** - Monitor progress and status
✅ **Scalable** - Adjust workers based on resources

**Get Started:**
```bash
# Submit your first async job
dva kg async submit --source my-dataset --provider lightrag

# Track progress
dva kg async list

# Check results
dva kg async status <job-id> --verbose
```
