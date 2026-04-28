# Async Ingestion Quick Start

## 🚀 Get Started in 5 Minutes

### 1. Submit Your First Async Job

```bash
# Single file
dva kg async submit --path /path/to/document.pdf --provider lightrag

# Directory (recursive)
dva kg async submit --path /path/to/docs --provider lightrag

# Data source (configured via 'dva data create')
dva kg async submit --source my-dataset --provider lightrag
```

**Output:**
```
✓ Job submitted successfully!
  Job ID: abc123-def456
  Status: pending

Track progress with: dva kg async status abc123-def456
```

---

### 2. Check Job Status

```bash
dva kg async status abc123-def456
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
dva kg async list
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
dva kg async submit --source backend-repo --provider both
dva kg async submit --source frontend-repo --provider both
dva kg async submit --source docs-repo --provider lightrag

# All run in parallel (up to 4 concurrent)
```

### Large Dataset Background Processing

```bash
# Submit and continue working
dva kg async submit --path /data/medical-records --provider lightrag

# Use CLI immediately
dva kg query "patient information"

# Check progress anytime
dva kg async status <job-id>
```

### Wait for Completion

```bash
# Block until done
dva kg async submit --path /docs --provider both --wait

# Shows results when complete
```

---

## 🎯 Key Commands

| Command | Purpose |
|---------|---------|
| `dva kg async submit` | Submit background job |
| `dva kg async status <id>` | Check job status |
| `dva kg async list` | List all jobs |
| `dva kg async cancel <id>` | Cancel job |
| `dva kg async cleanup` | Remove old jobs |

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
cd dva-agentic-cli
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
dva kg async submit --source your-dataset --provider lightrag
```

Track progress:

```bash
dva kg async list
```

That's it! 🚀
