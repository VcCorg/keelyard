# Workspace Directory Fix

## Issue

The workspace commands were failing with:
```
OSError: [Errno 30] Read-only file system: '/data'
```

## Root Cause

The default workspace base directory was set to `/data/lightrag`, which is:
- ❌ Read-only on macOS
- ❌ Requires root permissions
- ❌ Not portable across systems

## Solution

Changed the default workspace base directory to use the user's home directory:

**Before**: `/data/lightrag`  
**After**: `~/.dva-agentic/lightrag-workspaces`

## Changes Made

### 1. KGConfig (`src/dva_agentic_cli/kg/config.py`)

```python
# Before
workspace_base_dir: str = Field(
    default="/data/lightrag",
    description="Base directory for workspaces (LightRAG only)"
)

# After
workspace_base_dir: str = Field(
    default_factory=lambda: os.path.expanduser("~/.dva-agentic/lightrag-workspaces"),
    description="Base directory for workspaces (LightRAG only)"
)
```

### 2. WorkspaceManager (`src/dva_agentic_cli/kg/workspace.py`)

```python
# Before
def __init__(self, base_dir: str = "/data/lightrag"):

# After
def __init__(self, base_dir: Optional[str] = None):
    if base_dir is None:
        base_dir = os.path.expanduser("~/.dva-agentic/lightrag-workspaces")
```

### 3. Tests (`tests/test_workspace.py`)

Updated test to use the new default directory.

## Benefits

✅ **Works on all platforms** (macOS, Linux, Windows)  
✅ **No root permissions required**  
✅ **User-specific workspaces**  
✅ **Follows XDG conventions**  
✅ **Consistent with other DVA config** (`~/.dva-agentic/`)

## Directory Structure

```
~/.dva-agentic/
├── config.json                    # Main config
├── kg-config.json                 # KG config
└── lightrag-workspaces/           # Workspace base dir
    ├── workspaces.json            # Workspace metadata
    ├── default/                   # Default workspace
    │   └── ...
    ├── production/                # Production workspace
    │   └── ...
    └── eval-baseline/             # Evaluation workspace
        └── ...
```

## Verification

All commands now work correctly:

```bash
# List workspaces
$ dva kg workspace list
No workspaces found
Create a workspace: dva kg workspace create <name>

# Create workspace
$ dva kg workspace create test-workspace --description "Test" --env development
✓ Workspace 'test-workspace' created
Path: /Users/your-user/.dva-agentic/lightrag-workspaces/test-workspace

# List workspaces
$ dva kg workspace list
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name           ┃ Environment ┃ Documents ┃ Entities ┃ Created    ┃ Active ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ test-workspace │ development │         0 │        0 │ 2025-11-30 │        │
└────────────────┴─────────────┴───────────┴──────────┴────────────┴────────┘

# Show current workspace
$ dva kg workspace current
╭─ Current Workspace ──────────────────────────────╮
│ Name:         default                            │
│ Environment:  development                        │
│ Documents:    0                                  │
│ Path:         ~/.dva-agentic/lightrag-workspaces │
╰──────────────────────────────────────────────────╯
```

## Test Results

All 26 tests pass:
```
========================= 26 passed in 0.35s =========================
workspace.py: 92% coverage
```

## Migration

For users who may have set a custom `workspace_base_dir`:

1. **No action needed** if using default settings
2. **Custom directory users**: Your custom directory will continue to work
3. **Docker users**: Can override with environment variable or config

## Backward Compatibility

✅ Existing configurations with custom `workspace_base_dir` continue to work  
✅ Tests updated and passing  
✅ Documentation reflects new default  

## Status

✅ **Fixed and tested**  
✅ **All commands working**  
✅ **Tests passing**  
✅ **Ready for use**
