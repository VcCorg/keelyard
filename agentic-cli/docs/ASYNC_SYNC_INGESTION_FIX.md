# Async/Sync Ingestion Implementation Fix

## Problem Summary

The async ingestion command (`dva kg async submit --source <data-source>`) was failing for Git repositories with:
```
FileNotFoundError: File not found: https://bitbucket.example.com/scm/cgp/cwow-patient-model-spanner.git
```

While the sync command (`dva kg ingest --source <data-source>`) worked correctly for the same Git repository.

## Root Cause Analysis

### Issue 1: Missing Git URL Detection in `detect_format()`

**Location:** `src/dva_agentic_cli/kg/ingest.py:21-40`

The `detect_format()` function did not recognize Git repository URLs. When given a Git URL like `https://bitbucket.example.com/scm/cgp/cwow-patient-model-spanner.git`, it would default to `"text"` format, causing the async worker to call `parse_text()` which expects a file path, not a URL.

**Original logic:**
```python
def detect_format(source: str) -> str:
    if Path(source).is_dir():
        return "directory"
    
    if source_lower.endswith(".pdf"):
        return "pdf"
    # ... other formats
    else:
        return "text"  # ← Git URLs fell through to here
```

### Issue 2: Async Submit Not Setting Format Explicitly

**Location:** `src/dva_agentic_cli/commands/kg_async.py:93-98`

When resolving a data source, the async submit command received the source type (`git`, `confluence`, `doc`) but didn't set the `format` parameter accordingly. This meant the async worker had to rely on `detect_format()`, which was broken for Git URLs.

**Original logic:**
```python
if data_source:
    resolved_source, src_type, src_metadata = resolve_data_source(data_source)
    source_type = "data_source"
    metadata = src_metadata or {}
    # ← Missing: format should be set based on src_type
```

The sync command (`kg.py:460-475`) already had this logic correctly implemented, which is why it worked.

## Solution Implemented

### Fix 1: Enhanced `detect_format()` with Git URL Recognition

**File:** `src/dva_agentic_cli/kg/ingest.py`

Added Git URL detection before checking file extensions:

```python
def detect_format(source: str) -> str:
    """Auto-detect source format from file extension or URL."""
    # Check if it's a directory
    if Path(source).is_dir():
        return "directory"
    
    source_lower = source.lower()
    
    # Check for Git repository URLs
    if (source_lower.startswith("https://") or 
        source_lower.startswith("http://") or 
        source_lower.startswith("git@") or 
        source_lower.startswith("git://") or
        source_lower.startswith("ssh://")):
        # Check if it's a Git URL (ends with .git or contains git hosting domains)
        if (source_lower.endswith(".git") or 
            "github.com" in source_lower or 
            "gitlab.com" in source_lower or 
            "bitbucket" in source_lower):
            return "git"
    
    # ... rest of format detection
```

**Supported Git URL formats:**
- HTTPS: `https://github.com/user/repo.git`
- SSH: `git@github.com:user/repo.git`
- Git protocol: `git://github.com/user/repo.git`
- SSH protocol: `ssh://git@github.com/user/repo.git`

**Supported Git hosting platforms:**
- GitHub
- GitLab
- Bitbucket (including enterprise instances like `bitbucket.example.com`)

### Fix 2: Explicit Format Setting in Async Submit

**File:** `src/dva_agentic_cli/commands/kg_async.py`

Added format detection based on source type when resolving data sources:

```python
if data_source:
    console.print(f"[dim]Resolving data source '{data_source}'...[/dim]")
    resolved_source, src_type, src_metadata = resolve_data_source(data_source)
    source_type = "data_source"
    metadata = src_metadata or {}
    
    # Auto-detect format based on source type if not explicitly specified
    if not format:
        if src_type == "git":
            format = "git"
        elif src_type == "confluence":
            format = "confluence"
        # For "doc" type, let detect_format handle it
    
    console.print(f"[green]✓[/green] Resolved to: [cyan]{resolved_source}[/cyan]")
```

This ensures the async worker receives the correct format and doesn't need to rely solely on auto-detection.

## Implementation Comparison

### Sync Command Flow (Working Before Fix)

```
dva kg ingest --source cwow-patient-model
    ↓
resolve_data_source() → (url, "git", metadata)
    ↓
resolved_format = "git"  ← Explicitly set
    ↓
if config.provider == "lightrag":
    if resolved_format == "git":
        parse_git_repository(url, branch, tag, ...)  ← Direct call
```

### Async Command Flow (Fixed)

```
dva kg async submit --source cwow-patient-model
    ↓
resolve_data_source() → (url, "git", metadata)
    ↓
format = "git"  ← NOW explicitly set
    ↓
submit_ingestion(source=url, format="git", metadata=...)
    ↓
async_worker.py:
    format = job.format or detect_format(job.source)
    ↓
    format = "git"  ← Either from job or detect_format (both work now)
    ↓
    if format == "git":
        parse_git_repository(url, branch, tag, ...)  ← Correct path
```

## Testing

### Manual Test
```bash
# Test detect_format() function
python -c "
from dva_agentic_cli.kg.ingest import detect_format
print(detect_format('https://bitbucket.example.com/scm/cgp/repo.git'))  # Should print: git
print(detect_format('https://github.com/user/repo.git'))  # Should print: git
print(detect_format('git@github.com:user/repo.git'))  # Should print: git
"
```

### Integration Test
```bash
# Configure data source
dva data create --name test-repo \
    --source-type git \
    --source-location https://github.com/user/repo.git \
    --git-branch main

# Test async ingestion
dva kg async submit --source test-repo --provider lightrag

# Check status
dva kg async status <job-id>
```

## Benefits of This Fix

1. **Consistency:** Async and sync ingestion now use the same logic
2. **Robustness:** Double protection - explicit format setting + auto-detection
3. **Extensibility:** Easy to add support for more Git hosting platforms
4. **Maintainability:** Centralized format detection logic

## Files Modified

1. `src/dva_agentic_cli/kg/ingest.py` - Enhanced `detect_format()` function
2. `src/dva_agentic_cli/commands/kg_async.py` - Added explicit format setting in `submit_ingestion()`

## Related Code

- **Sync ingestion:** `src/dva_agentic_cli/commands/kg.py:460-475` (already correct)
- **Async worker:** `src/dva_agentic_cli/kg/async_worker.py:119-146` (now receives correct format)
- **Data source resolution:** `src/dva_agentic_cli/commands/kg.py:32-88` (shared by both)
- **Git parser:** `src/dva_agentic_cli/kg/parsers.py` (parse_git_repository function)

## Future Improvements

1. Add unit tests for `detect_format()` with various Git URL formats
2. Add integration tests for async Git ingestion
3. Consider adding support for other Git hosting platforms (Azure DevOps, Gitea, etc.)
4. Add validation for Git URL format before attempting to clone
