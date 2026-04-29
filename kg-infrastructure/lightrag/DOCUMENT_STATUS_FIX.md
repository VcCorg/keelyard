# Document Status Tracking Fix

## Problem Identified

The `dva kg stats` command was showing incorrect document ingestion status:
- **Completed**: Always showed 0 (incorrect)
- **Processing**: Showed 1 (correct)
- **Pending**: Not tracked at all (missing)

## Root Cause

**Status Value Mismatch:**

LightRAG uses different status values than what the code was checking for:

| What LightRAG Uses | What Code Was Checking | Result |
|-------------------|------------------------|---------|
| `"processed"` | `"completed"` | ❌ Never matched |
| `"processing"` | `"processing"` | ✅ Matched correctly |
| `"pending"` | Not checked | ❌ Not counted |
| `"failed"` | `"failed"` | ✅ Would match if present |

### Evidence from Data

Looking at `/data/lightrag/kv_store_doc_status.json`:
```json
{
  "doc-1826d6aa013dc5ff1a28ab1b9e3d707f": {
    "status": "processing",  // ✓ Correctly detected
    ...
  },
  "doc-2db5d0df5558e31b97a6a1816abc2b37": {
    "status": "processed",   // ✗ Was being ignored (not "completed")
    ...
  },
  "doc-a04464da16a8fab1b4ab285a3bf32036": {
    "status": "processed",   // ✗ Was being ignored
    ...
  }
}
```

**Result:** 7 documents with `"processed"` status were not being counted as completed!

---

## The Fix

### 1. Fixed `scripts/server.py` (Lines 423-429)

**Before:**
```python
# Count statuses
total = len(doc_status)
completed = sum(1 for doc in doc_status.values() if doc.get("status") == "completed")
processing = sum(1 for doc in doc_status.values() if doc.get("status") == "processing")
failed = sum(1 for doc in doc_status.values() if doc.get("status") == "failed")
```

**After:**
```python
# Count statuses
# Note: LightRAG uses "processed" (not "completed") and "processing" statuses
total = len(doc_status)
completed = sum(1 for doc in doc_status.values() if doc.get("status") in ["completed", "processed"])
processing = sum(1 for doc in doc_status.values() if doc.get("status") == "processing")
failed = sum(1 for doc in doc_status.values() if doc.get("status") == "failed")
pending = sum(1 for doc in doc_status.values() if doc.get("status") == "pending")
```

**Changes:**
- ✅ Now checks for both `"completed"` AND `"processed"` statuses
- ✅ Added `pending` count for documents waiting to be processed
- ✅ Added explanatory comment about LightRAG's status values

### 2. Updated Response Schema (Lines 444-450)

**Before:**
```python
return {
    "total_documents": total,
    "completed": completed,
    "processing": processing,
    "failed": failed,
    "documents": documents
}
```

**After:**
```python
return {
    "total_documents": total,
    "completed": completed,
    "processing": processing,
    "pending": pending,      # ← Added
    "failed": failed,
    "documents": documents
}
```

### 3. Updated Agentic CLI Display (kg.py Lines 788-798)

**Before:**
```python
total = doc_status.get("total_documents", 0)
completed = doc_status.get("completed", 0)
processing = doc_status.get("processing", 0)
failed = doc_status.get("failed", 0)

status_table.add_row("Total Documents", str(total))
status_table.add_row("✓ Completed", str(completed), style="green")
status_table.add_row("⏳ Processing", str(processing), style="yellow")
status_table.add_row("✗ Failed", str(failed), style="red" if failed > 0 else "dim")
```

**After:**
```python
total = doc_status.get("total_documents", 0)
completed = doc_status.get("completed", 0)
processing = doc_status.get("processing", 0)
pending = doc_status.get("pending", 0)      # ← Added
failed = doc_status.get("failed", 0)

status_table.add_row("Total Documents", str(total))
status_table.add_row("✓ Completed", str(completed), style="green")
status_table.add_row("⏳ Processing", str(processing), style="yellow")
status_table.add_row("⏸ Pending", str(pending), style="cyan" if pending > 0 else "dim")  # ← Added
status_table.add_row("✗ Failed", str(failed), style="red" if failed > 0 else "dim")
```

---

## Expected Results After Fix

### Before Fix:
```
 Document Ingestion Status 
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Status          ┃ Count ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Documents │     8 │
│ ✓ Completed     │     0 │  ← Wrong! Should be 7
│ ⏳ Processing   │     1 │  ← Correct
│ ✗ Failed        │     0 │  ← Correct
└─────────────────┴───────┘
```

### After Fix:
```
 Document Ingestion Status 
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Status          ┃ Count ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Documents │     8 │
│ ✓ Completed     │     7 │  ← Fixed! Now shows "processed" docs
│ ⏳ Processing   │     1 │  ← Still correct
│ ⏸ Pending       │     0 │  ← New! Shows queued docs
│ ✗ Failed        │     0 │  ← Still correct
└─────────────────┴───────┘
```

---

## How to Apply the Fix

### Step 1: Restart LightRAG Service

The server code has been updated, now restart the container:

```bash
cd /Users/your-user/agentic-project/lightrag-infrastructure
docker restart dva-lightrag
```

Wait ~30 seconds for the service to start, then verify:
```bash
curl http://localhost:8001/health
```

### Step 2: Test the Fixed Endpoint

```bash
curl -s http://localhost:8001/document-status | python3 -m json.tool
```

You should now see:
```json
{
    "total_documents": 8,
    "completed": 7,        // ← Should be 7 now (was 0)
    "processing": 1,
    "pending": 0,          // ← New field
    "failed": 0,
    "documents": [...]
}
```

### Step 3: Test Agentic CLI

```bash
cd /Users/your-user/agentic-project
`agent kg stats
```

Expected output:
```
 Document Ingestion Status 
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Status          ┃ Count ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Documents │     8 │
│ ✓ Completed     │     7 │  ← Fixed!
│ ⏳ Processing   │     1 │
│ ⏸ Pending       │     0 │  ← New!
│ ✗ Failed        │     0 │
└─────────────────┴───────┘
```

---

## Status Value Reference

For future reference, LightRAG uses these status values:

| Status | Meaning | When Set |
|--------|---------|----------|
| `"pending"` | Document queued for processing | When first added to queue |
| `"processing"` | Currently being processed | During entity extraction |
| `"processed"` | Successfully completed | After all processing done |
| `"failed"` | Processing failed | On error during processing |

**Note:** LightRAG does NOT use `"completed"` - it uses `"processed"` instead!

---

## Files Modified

1. **`/Users/your-user/agentic-project/lightrag-infrastructure/scripts/server.py`**
   - Lines 409-416: Added `pending` to empty state response
   - Lines 423-429: Fixed status counting logic
   - Lines 444-450: Added `pending` to response schema

2. **`/Users/your-user/agentic-project/agentic-cli/src/dva_agentic_cli/commands/kg.py`**
   - Lines 788-798: Added pending status display to CLI table

---

## Verification Checklist

After applying the fix:

- [ ] Restart LightRAG container: `docker restart dva-lightrag`
- [ ] Wait for health check: `curl http://localhost:8001/health`
- [ ] Verify endpoint response shows correct counts
- [ ] Run `dva kg stats` and verify display
- [ ] Completed count should be 7 (not 0)
- [ ] Pending row should be visible
- [ ] All 4 status types displayed: Completed, Processing, Pending, Failed

---

## Summary

**Problem:** Document status tracking was broken due to status value mismatch between LightRAG (`"processed"`) and our code (`"completed"`).

**Solution:** Updated status counting to recognize both `"completed"` and `"processed"` as completed states, and added `"pending"` tracking.

**Impact:** The `dva kg stats` command now accurately reflects the true state of document ingestion! 🎉
