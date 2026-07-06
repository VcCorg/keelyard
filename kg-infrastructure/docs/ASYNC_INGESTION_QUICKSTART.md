# Async Ingestion Quick Start

## 🚀 Get Started in 5 Minutes

### 1. Submit Your First Async Job

```bash
# Single file
`agent kg async submit --path /path/to/document.pdf --provider lightrag

# Directory (recursive)
`agent kg async submit --path /path/to/docs --provider lightrag

# Data source (configured via 'agent data create')
`agent kg async submit --source my-dataset --provider lightrag
```

**Output:**
```
✓ Job submitted successfully!
  Job ID: abc123-def456
  Status: pending

Track progress with: agent kg async status abc123-def456
```

---

### 2. Check Job Status

```bash
`agent kg async status abc123-def456
```

**Output:**
```
┌─ Ingestion Job Status ─────────────────────┐
│ Job ID: abc123-def456                      │
│ Source: /path/to/docs                      │
│ Provider: lightrag                         │
│ Status: running                            │
│ Progress: lightrag                         │
└────────────────────────────────────────────┘
```

---

### 3. List All Jobs

```bash
`agent kg async list
```

**Output:**
```
┌─ Ingestion Jobs (3 total) ─────────────────┐
│ Job ID    │ Source      │ Status      │    │
├───────────┼─────────────┼─────────────┼────┤
│ abc123... │ /docs       │ ✓ Completed │    │
│ def456... │ my-dataset  │ 🔄 Running  │    │
│ ghi789... │ /pdfs       │ ⏳ Pending  │    │
└───────────┴─────────────┴─────────────┴────┘
```

---

## 💡 Common Use Cases

### Parallel Multi-Repo Ingestion

```bash
# Submit all repos at once
`agent kg async submit --source backend-repo --provider both
`agent kg async submit --source frontend-repo --provider both
`agent kg async submit --source docs-repo --provider lightrag

# All run in parallel (up to 4 concurrent)
```

### Large Dataset Background Processing

```bash
# Submit and continue working
`agent kg async submit --path /data/medical-records --provider lightrag

# Use CLI immediately
`agent kg query "patient information"

# Check progress anytime
`agent kg async status <job-id>
```

### Wait for Completion

```bash
# Block until done
`agent kg async submit --path /docs --provider both --wait

# Shows results when complete
```

---

## 🎯 Key Commands

| Command | Purpose |
|---------|---------|
| `keel kg async submit` | Submit background job |
| `keel kg async status <id>` | Check job status |
| `keel kg async list` | List all jobs |
| `keel kg async cancel <id>` | Cancel job |
| `keel kg async cleanup` | Remove old jobs |

---

## 🔧 Options

### Provider Selection

```bash
--provider lightrag    # LightRAG only (fast)
--provider neo4j       # Neo4j only (relationships)
--provider both        # Both systems (redundancy)
```

### Source Options

```bash
--path /file.pdf       # Direct file path
--source my-dataset    # Configured data source
```

### Processing Options

```bash
--recursive            # Process subdirectories (default: true)
--no-extract-entities  # Skip entity extraction (faster)
--wait                 # Block until complete
```

---

## ✅ Validation

Test concurrent ingestion support:

```bash
cd agentic-cli
python scripts/validate_concurrent_ingestion.py
```

Expected: `✅ ALL TESTS PASSED`

---

## 📚 Full Documentation

See `docs/ASYNC_INGESTION.md` for:
- Detailed architecture
- Performance tuning
- Error handling
- API reference
- Troubleshooting

---

## 🎉 You're Ready!

Start ingesting in the background:

```bash
`agent kg async submit --source your-dataset --provider lightrag
```

Track progress:

```bash
`agent kg async list
```

That's it! 🚀
