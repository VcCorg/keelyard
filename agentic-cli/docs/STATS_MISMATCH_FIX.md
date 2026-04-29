# DVA KG Stats Mismatch Fix

## Issue

There was a discrepancy between the statistics displayed by `dva kg stats` and `dva kg clear`:

### Before Fix:
- **`dva kg stats`** showed: `Total Documents: 148`
- **`dva kg clear`** showed: `Documents: 0`

This mismatch was confusing because the same knowledge graph was showing different document counts.

## Root Cause

The issue was in how the `dva kg clear` command fetched statistics:

1. **`dva kg stats` command** (lines 929-969):
   - Calls `client.get_stats()` - returns basic LightRAG info
   - Calls `client.get_document_status()` - returns document ingestion status
   - Displays documents from `doc_status.get('total_documents', 0)`

2. **`dva kg clear` command** (lines 1051-1059, 1121-1128):
   - Only called `client.get_stats()`
   - Tried to access `stats.get('document_count', 0)` which doesn't exist
   - Always returned 0 for documents

## LightRAG API Endpoints

The LightRAG API has two separate endpoints:

### `/stats` Endpoint
Returns basic configuration info:
```json
{
  "working_dir": "/data/lightrag",
  "initialized": true,
  "vector_store": "nano-vectordb",
  "graph_store": "networkx",
  "data_files": 12,
  "entity_count": 0,     // Not always present
  "relation_count": 0    // Not always present
}
```

### `/document-status` Endpoint
Returns document ingestion status:
```json
{
  "total_documents": 148,
  "completed": 148,
  "processing": 0,
  "pending": 0,
  "failed": 0,
  "documents": [...]
}
```

## Fix Applied

Modified `dva kg clear` command to fetch document counts from the correct endpoint:

### File: `src/dva_agentic_cli/commands/kg.py`

**Lines 1051-1060** (Current Statistics):
```python
elif p == "lightrag":
    from dva_agentic_cli.kg.lightrag_client import LightRAGClient
    client = LightRAGClient(base_url=config.lightrag_url, timeout=config.lightrag_timeout)
    stats = client.get_stats()
    doc_status = client.get_document_status()  # ← Added this line
    client.close()
    console.print(f"[cyan]LightRAG:[/cyan]")
    console.print(f"  Entities: {stats.get('entity_count', 0)}")
    console.print(f"  Relations: {stats.get('relation_count', 0)}")
    console.print(f"  Documents: {doc_status.get('total_documents', 0)}")  # ← Changed from stats
```

**Lines 1121-1130** (Final Statistics):
```python
elif p == "lightrag":
    from dva_agentic_cli.kg.lightrag_client import LightRAGClient
    client = LightRAGClient(base_url=config.lightrag_url, timeout=config.lightrag_timeout)
    stats = client.get_stats()
    doc_status = client.get_document_status()  # ← Added this line
    client.close()
    console.print(f"[cyan]LightRAG:[/cyan]")
    console.print(f"  Entities: {stats.get('entity_count', 0)}")
    console.print(f"  Relations: {stats.get('relation_count', 0)}")
    console.print(f"  Documents: {doc_status.get('total_documents', 0)}")  # ← Changed from stats
```

## After Fix

Now both commands show consistent statistics:

### `dva kg stats`:
```
   Knowledge Graph Statistics    
           (LightRAG)            
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Metric       ┃          Value ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Working Dir  │ /data/lightrag │
│ Initialized  │           True │
│ Vector Store │  nano-vectordb │
│ Graph Store  │       networkx │
│ Data Files   │             12 │
└──────────────┴────────────────┘

 Document Ingestion Status 
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Status          ┃ Count ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Documents │   148 │
│ ✓ Completed     │   148 │
│ ⏳ Processing   │     0 │
│ ⏸ Pending       │     0 │
│ ✗ Failed        │     0 │
└─────────────────┴───────┘
```

### `dva kg clear`:
```
Current Statistics:

LightRAG:
  Entities: 0
  Relations: 0
  Documents: 148  ← Now matches!
```

## Testing

To verify the fix:
```bash
# Check current stats
`agent kg stats

# Try to clear (cancel when prompted)
`agent kg clear

# Verify both show the same document count
```

## Impact

- ✅ Consistent statistics across all `dva kg` commands
- ✅ Accurate document counts in `dva kg clear`
- ✅ Better user experience and trust in the CLI
- ✅ No breaking changes to existing functionality

## Related Files

- `src/dva_agentic_cli/commands/kg.py` - Main fix location
- `src/dva_agentic_cli/kg/lightrag_client.py` - Client methods used
- `docs/STATS_MISMATCH_FIX.md` - This documentation
