# Async Ingestion Refactoring

## Summary

Refactored async ingestion commands from a top-level command group (`dva kg async`) to a subcommand under ingest (`dva kg ingest async`). This better reflects that async is an operational mode of ingestion, not a separate feature.

---

## Motivation

**Before**: Async ingestion was at the same level as the core ingest feature:
```bash
dva kg ingest --path /data/file.pdf    # Sync ingestion
dva kg async submit --path /data/file.pdf  # Async ingestion
```

**Problem**: This structure suggests async is a separate feature equal to ingestion, when it's actually just an operational mode of the same ingestion feature.

**After**: Async is now a subcommand of ingest:
```bash
dva kg ingest --path /data/file.pdf           # Sync ingestion (default)
dva kg ingest async submit --path /data/file.pdf  # Async ingestion
```

---

## Changes Made

### 1. Created New File: `kg_ingest.py`

**Purpose**: Contains all async ingestion management commands

**Structure**:
```python
ingest_app = typer.Typer()           # Main ingest group
async_app = typer.Typer()            # Async management subgroup

ingest_app.add_typer(async_app, name="async")

# Async commands
@async_app.command("submit")
@async_app.command("status")
@async_app.command("list")
@async_app.command("cancel")
@async_app.command("cleanup")
@async_app.command("logs")
```

### 2. Modified `kg.py`

**Changes**:
- Removed top-level `dva kg async` registration
- Converted `ingest` from a simple command to a Typer group
- Registered async subcommands under ingest
- Added callback to handle both direct invocation and subcommands

**Code**:
```python
# Create ingest command group
ingest_cmd = typer.Typer(help="Data ingestion commands")
kg_app.add_typer(ingest_cmd, name="ingest")

# Register async subcommands under ingest
ingest_cmd.add_typer(ingest_async_app, name="async")

# Main ingest command (sync)
@ingest_cmd.callback(invoke_without_command=True)
def ingest(ctx: typer.Context, ...):
    # If subcommand invoked (like 'async'), let it handle
    if ctx and ctx.invoked_subcommand is not None:
        return
    
    # Otherwise, run sync ingestion
    ...
```

### 3. Deprecated `kg_async.py`

**Status**: File still exists but is no longer registered at top level

**Migration Path**: Commands moved to `kg_ingest.py`

---

## Command Mapping

### Old Structure → New Structure

| Old Command | New Command |
|------------|-------------|
| `dva kg async submit` | `dva kg ingest async submit` |
| `dva kg async status <id>` | `dva kg ingest async status <id>` |
| `dva kg async list` | `dva kg ingest async list` |
| `dva kg async cancel <id>` | `dva kg ingest async cancel <id>` |
| `dva kg async cleanup` | `dva kg ingest async cleanup` |
| `dva kg async logs` | `dva kg ingest async logs` |

### Sync Ingestion (Unchanged)

```bash
# These commands work exactly as before
dva kg ingest --path /data/file.pdf
dva kg ingest --source my-dataset
dva kg ingest --workspace production --path /data
```

---

## Usage Examples

### Synchronous Ingestion (Default)

```bash
# Direct path
dva kg ingest --path /data/documents/file.pdf

# Data source
dva kg ingest --source cwow-docs

# With workspace
dva kg ingest --source cwow-docs --workspace production
```

### Asynchronous Ingestion

```bash
# Submit async job
dva kg ingest async submit --path /data/large-dataset

# Check status
dva kg ingest async status abc123

# List all jobs
dva kg ingest async list

# List by status
dva kg ingest async list --status running

# Cancel job
dva kg ingest async cancel abc123

# View logs
dva kg ingest async logs abc123

# Cleanup old jobs
dva kg ingest async cleanup --days 30
```

---

## Benefits

### 1. **Clearer Hierarchy**
```
dva kg
├── ingest (main feature)
│   ├── [default] (sync mode)
│   └── async (operational mode)
│       ├── submit
│       ├── status
│       ├── list
│       ├── cancel
│       ├── cleanup
│       └── logs
├── query
├── search
└── ...
```

### 2. **Better Discoverability**
Users exploring `dva kg ingest --help` immediately see async as an option:
```
Commands:
  async  Manage async ingestion jobs
```

### 3. **Logical Grouping**
All ingestion-related commands are under `ingest`, making it clear that async is just a mode of ingestion.

### 4. **Consistent with Industry Standards**
Similar to tools like:
- `kubectl apply` vs `kubectl apply --async`
- `terraform apply` vs `terraform apply -auto-approve`
- `docker build` vs `docker build --progress=plain`

---

## Migration Guide

### For Users

**If you were using**:
```bash
dva kg async submit --path /data
```

**Update to**:
```bash
dva kg ingest async submit --path /data
```

**Find and replace**:
```bash
# In scripts
sed -i 's/dva kg async/dva kg ingest async/g' your-script.sh
```

### For Documentation

Update all references:
- `dva kg async` → `dva kg ingest async`
- Async ingestion is now documented under the ingest command

---

## Technical Details

### Typer Callback Pattern

The refactoring uses Typer's callback pattern to support both:
1. Direct invocation: `dva kg ingest --path /data` (runs sync ingestion)
2. Subcommand invocation: `dva kg ingest async submit` (runs async command)

```python
@ingest_cmd.callback(invoke_without_command=True)
def ingest(ctx: typer.Context, ...):
    # Check if subcommand was invoked
    if ctx and ctx.invoked_subcommand is not None:
        return  # Let subcommand handle it
    
    # No subcommand, run sync ingestion
    ...
```

### File Organization

```
commands/
├── kg.py                 # Main KG commands, ingest group registration
├── kg_ingest.py          # NEW: Async management commands
├── kg_async.py           # DEPRECATED: Old async commands
├── kg_workspace.py       # Workspace management
└── ...
```

---

## Testing

### Verify New Commands

```bash
# Test help
dva kg ingest --help
dva kg ingest async --help

# Test sync ingestion (should work as before)
dva kg ingest --path /tmp/test.txt

# Test async commands
dva kg ingest async list
dva kg ingest async submit --path /tmp/test.txt
```

### Verify Old Commands Removed

```bash
# Should fail
dva kg async --help
# Error: No such command 'async'.
```

---

## Backward Compatibility

### Breaking Change ⚠️

**Old commands will NOT work**:
```bash
dva kg async submit    # ✗ Error: No such command 'async'
```

**Users must update to**:
```bash
dva kg ingest async submit  # ✓ Works
```

### Migration Script

For users with existing scripts:
```bash
#!/bin/bash
# migrate-async-commands.sh

# Find all scripts using old async commands
find . -type f \( -name "*.sh" -o -name "*.bash" \) -exec grep -l "dva kg async" {} \;

# Replace old commands with new ones
find . -type f \( -name "*.sh" -o -name "*.bash" \) -exec sed -i.bak 's/dva kg async/dva kg ingest async/g' {} \;

echo "Migration complete. Backup files created with .bak extension"
```

---

## Future Enhancements

### Potential Additions

1. **Async flag on main ingest**:
   ```bash
   dva kg ingest --path /data --async  # Auto-submit as async job
   ```

2. **Batch operations**:
   ```bash
   dva kg ingest async submit-batch --sources file1,file2,file3
   ```

3. **Job templates**:
   ```bash
   dva kg ingest async submit --template large-dataset
   ```

4. **Progress streaming**:
   ```bash
   dva kg ingest async status abc123 --follow  # Live updates
   ```

---

## Documentation Updates

### Files to Update

1. ✅ `ASYNC_INGEST_REFACTORING.md` (this file)
2. ⏳ `README.md` - Update command examples
3. ⏳ `ASYNC_INGESTION_QUICKSTART.md` - Update all commands
4. ⏳ `ASYNC_INGESTION_IMPLEMENTATION.md` - Update architecture
5. ⏳ Example scripts in `examples/`

---

## Summary

✅ **Refactored async ingestion to be a subcommand of ingest**  
✅ **Clearer command hierarchy**  
✅ **Better discoverability**  
✅ **All async commands work under `dva kg ingest async`**  
✅ **Sync ingestion unchanged**  
⚠️ **Breaking change: Old `dva kg async` commands no longer work**  

The refactoring makes the CLI more intuitive by grouping all ingestion-related commands under `ingest`, with async being an operational mode rather than a separate feature.
