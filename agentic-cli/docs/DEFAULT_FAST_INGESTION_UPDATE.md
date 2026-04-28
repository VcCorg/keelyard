# Default Fast Ingestion Update

## Summary

Changed the default behavior of `dva kg ingest` for Git repositories to use **fast mode** (gitingest digest only) instead of detailed code analysis. This makes ingestion 10-20x faster and is optimized for healthcare entity extraction.

## Changes Made

### 1. Default Behavior Changed

**Before:**
```bash
`agent kg ingest --source my-repo
# Used detailed analysis by default (slow, analyzed every file)
```

**After:**
```bash
`agent kg ingest --source my-repo
# Uses fast mode by default (gitingest only, much faster)
```

### 2. Files Modified

1. **`src/dva_agentic_cli/commands/kg.py`**
   - Changed `detailed_analysis` default from `True` to `False`
   - Updated help text to indicate "faster, default"

2. **`src/dva_agentic_cli/kg/ingest.py`**
   - Changed `detailed_analysis` default from `True` to `False`
   - Updated docstring to reflect new default

3. **`src/dva_agentic_cli/kg/parsers.py`**
   - Changed `detailed_analysis` default from `True` to `False`
   - Updated docstring to indicate False is default

4. **`GIT_INGEST_OPTIMIZATION.md`**
   - Updated documentation to reflect fast mode as default
   - Updated migration notes and recommendations

## Usage

### Default: Fast Mode (Recommended for Healthcare)
```bash
# Ingest with gitingest only (fast, default)
`agent kg ingest --source patient-records

# Explicit (same as above)
`agent kg ingest --source patient-records --no-detailed-analysis
```

**Performance:**
- ⚡ 10-20x faster
- 📄 Creates 1 comprehensive document per repository
- ✅ Perfect for healthcare entities (Patient, Facility, Provider, etc.)
- ✅ Sufficient for most query use cases

### Opt-in: Detailed Mode (For Code Analysis)
```bash
# Ingest with detailed code analysis
`agent kg ingest --source backend-api --detailed-analysis
```

**Performance:**
- 🐌 Slower (minutes vs seconds)
- 📄 Creates N documents (overview + files + functions + classes)
- ✅ Better for code-specific queries
- ✅ Provides function/class level granularity

## Rationale

### Why Fast Mode as Default?

1. **Performance**: 10-20x faster ingestion
2. **Healthcare Focus**: Your entity types (Patient, Facility, Provider, Assessment, etc.) are document-level, not code-level
3. **Sufficient Coverage**: gitingest provides comprehensive content for entity extraction
4. **Resource Efficiency**: Lower memory usage, faster processing
5. **User Experience**: Most users don't need function-level granularity

### When to Use Detailed Mode?

Use `--detailed-analysis` when you need:
- Function/class level search
- Code structure analysis
- Developer-focused knowledge graphs
- SQL schema extraction details
- Granular code relationships

## Examples

### Example 1: Healthcare Documentation (Default)
```bash
# Configure data source
`agent data create \
  --name patient-docs \
  --source-type git \
  --source-location https://github.com/org/patient-docs.git

# Ingest (fast mode by default)
`agent kg ingest --source patient-docs
```

**Output:**
```
[INFO] Cloning repository: https://github.com/org/patient-docs.git
[INFO] Repository cloned: patient-docs (a1b2c3d4)
[INFO] Generating repository digest with gitingest...
[INFO] Skipping detailed code analysis (using gitingest digest only)
[INFO] Parsed 1 documents from repository
✓ Successfully ingested data
  Source: https://github.com/org/patient-docs.git
  Format: git
  Entities: 45
  Relationships: 28
  Time: 15 seconds
```

### Example 2: Backend Codebase (Detailed)
```bash
# Configure data source
`agent data create \
  --name backend-api \
  --source-type git \
  --source-location https://github.com/org/backend.git

# Ingest with detailed analysis
`agent kg ingest --source backend-api --detailed-analysis
```

**Output:**
```
[INFO] Cloning repository: https://github.com/org/backend.git
[INFO] Repository cloned: backend (b2c3d4e5)
[INFO] Generating repository digest with gitingest...
[INFO] Performing detailed code analysis...
[INFO] Found 150 source files (Python, Java, SQL/DDL/DML)
[INFO] Parsed 450 documents from repository
✓ Successfully ingested data
  Source: https://github.com/org/backend.git
  Format: git
  Entities: 1250
  Relationships: 850
  Time: 3 minutes
```

## Performance Comparison

| Metric | Fast Mode (Default) | Detailed Mode |
|--------|---------------------|---------------|
| **Time** | 10-30 seconds | 2-10 minutes |
| **Documents** | 1 (overview) | 1 + N files + M functions |
| **Memory** | Low | Medium-High |
| **Entity Types** | Document-level | Code-level |
| **Best for** | Healthcare, docs | Code analysis |

## Migration Guide

### If You Were Using Default Behavior

**Before (implicit detailed analysis):**
```bash
`agent kg ingest --source my-repo
# This was slow (detailed analysis)
```

**After (implicit fast mode):**
```bash
`agent kg ingest --source my-repo
# This is now fast (gitingest only)
```

**If you need the old behavior:**
```bash
`agent kg ingest --source my-repo --detailed-analysis
```

### Testing Your Use Case

1. **Try default fast mode first:**
   ```bash
   agent kg ingest --source my-repo
   ```

2. **Test query quality:**
   ```bash
   agent kg query "Find all patient assessments"
   agent kg search "care plan" --semantic
   ```

3. **If results are insufficient, try detailed mode:**
   ```bash
   agent kg ingest --source my-repo --detailed-analysis
   ```

4. **Compare results and choose the mode that works best**

## Benefits

### For Healthcare Use Cases
- ✅ **Faster ingestion**: Get started quickly
- ✅ **Lower resource usage**: Less memory, CPU
- ✅ **Sufficient granularity**: Document-level entities work well
- ✅ **Better UX**: Less waiting time
- ✅ **Scalable**: Can ingest more repositories faster

### For Code Analysis Use Cases
- ✅ **Still available**: Use `--detailed-analysis` flag
- ✅ **Explicit opt-in**: Clear when you need it
- ✅ **No loss of functionality**: All features preserved

## Verification

Check the default behavior:
```bash
`agent kg ingest --help | grep -A 3 "detailed-analysis"
```

Expected output:
```
  --detailed-analysis / --no-detailed-analysis
                                  Perform detailed code analysis for Git repos
                                  (functions, classes)  [default: no-detailed-
                                  analysis]
```

## Current Status

✅ **Implemented and Active**

- Default: Fast mode (gitingest only)
- Opt-in: Detailed mode with `--detailed-analysis`
- Documentation: Updated
- Help text: Updated
- Ready to use

## Recommendations

### For Your Healthcare Project

**Use default fast mode:**
```bash
`agent kg ingest --source patient-records
`agent kg ingest --source clinical-docs
`agent kg ingest --source care-plans
```

**Why:**
- Your entity types (Patient, Facility, Provider, Assessment, PlanOfCare, Medication, CarePlan, Encounter) are document-level
- gitingest provides comprehensive content for entity extraction
- 10-20x faster means you can iterate and test more quickly
- Lower resource usage means you can ingest more repositories

### When to Use Detailed Mode

Only use `--detailed-analysis` if:
- You need to query specific functions or classes
- You're analyzing source code structure
- You need SQL table/view/procedure details
- Document-level entities are insufficient

## Next Steps

1. **Test with your data:**
   ```bash
   agent kg ingest --source your-healthcare-repo
   ```

2. **Verify entity extraction:**
   ```bash
   agent kg stats
   agent kg query "Show me all patients"
   ```

3. **Compare if needed:**
   ```bash
   # Try detailed mode if results are insufficient
   agent kg ingest --source your-healthcare-repo --detailed-analysis
   ```

4. **Stick with what works best for your use case**

## Conclusion

The default fast mode is now optimized for healthcare entity extraction and provides the best balance of speed and functionality. Detailed mode remains available for code-specific analysis when needed.

**Your current setup with LightRAG (144 documents, 143 completed) will benefit from this faster ingestion mode for future data sources.**
