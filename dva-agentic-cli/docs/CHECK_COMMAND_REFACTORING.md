# Check Command Refactoring

## Summary

Refactored `dva kg check` command to support both Neo4j and LightRAG providers, with LightRAG as the default when no configuration exists.

---

## Changes

### Before
```bash
dva kg check
# Only checked Neo4j prerequisites
# Always showed Docker, Neo4j container, Neo4j connection
```

### After
```bash
dva kg check
# Checks configured provider (or defaults to LightRAG)
# Shows provider-specific prerequisites

dva kg check --provider neo4j
# Explicitly check Neo4j

dva kg check --provider lightrag
# Explicitly check LightRAG
```

---

## Command Reference

### `dva kg check`

Check prerequisites and provider availability.

**Options**:
- `--provider TEXT`: Provider to check (neo4j, lightrag). Defaults to configured provider or lightrag.

**Behavior**:
1. If `--provider` specified: Check that provider
2. If configuration exists: Check configured provider
3. Otherwise: Check LightRAG (default)

---

## Usage Examples

### Default Check (LightRAG)

```bash
$ dva kg check

Using configured provider: lightrag

Checking LIGHTRAG Prerequisites...

LightRAG Prerequisites Check
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component         ┃ Status ┃ Message                                  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ LightRAG Server   │ ✓      │ Connected to http://localhost:8001       │
│ Working Directory │ ✓      │ /data/lightrag                           │
│ Vector Store      │ ✓      │ nano-vectordb                            │
│ Graph Store       │ ✓      │ networkx                                 │
│ Workspace         │ ✓      │ default (~/.dva-agentic/lightrag-work...) │
└───────────────────┴────────┴──────────────────────────────────────────┘

✓ All prerequisites are met!

You can now use LightRAG knowledge graph commands:
  dva kg ingest submit --path <source>
  dva kg ingest submit --path <source> --async
  dva kg query <query>
  dva kg search <text>
  dva kg workspace list
```

### Check Neo4j

```bash
$ dva kg check --provider neo4j

Checking NEO4J Prerequisites...

Neo4j Prerequisites Check
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component         ┃ Status ┃ Message                                  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Docker Installed  │ ✓      │ Docker is available: Docker version...   │
│ Docker Running    │ ✓      │ Docker daemon is running                 │
│ Neo4j Container   │ ✓      │ Neo4j container 'dva-neo4j' is running   │
│ Neo4j Connection  │ ✓      │ Neo4j is available and accessible        │
└───────────────────┴────────┴──────────────────────────────────────────┘

✓ All prerequisites are met!

You can now use Neo4j knowledge graph commands:
  dva kg ingest submit --path <source>
  dva kg query <query>
  dva kg visualize
```

### Check LightRAG (Explicit)

```bash
$ dva kg check --provider lightrag

Checking LIGHTRAG Prerequisites...
...
```

---

## Provider-Specific Checks

### LightRAG Checks

1. **LightRAG Server**: Connection to LightRAG API
2. **Working Directory**: LightRAG data directory
3. **Vector Store**: Vector database (nano-vectordb, etc.)
4. **Graph Store**: Graph database (networkx, etc.)
5. **Workspace**: Active workspace configuration

### Neo4j Checks

1. **Docker Installed**: Docker availability
2. **Docker Running**: Docker daemon status
3. **Neo4j Container**: Container existence and status
4. **Neo4j Connection**: Database connectivity

---

## Error Handling

### LightRAG Not Available

```bash
$ dva kg check

No configuration found, checking default provider: lightrag

Checking LIGHTRAG Prerequisites...

LightRAG Prerequisites Check
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component         ┃ Status ┃ Message                                  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ LightRAG Server   │ ✗      │ Cannot connect to http://localhost:8001  │
│ Workspace         │ ⚠      │ No workspace configured                  │
└───────────────────┴────────┴──────────────────────────────────────────┘

⚠ Some prerequisites are not met

Setup Instructions:
1. Start LightRAG server:
   cd lightrag-infrastructure && ./scripts/start.sh

2. Initialize configuration:
   dva kg init --provider lightrag --lightrag-url http://localhost:8001

3. Create a workspace:
   dva kg workspace create default
```

### Neo4j Not Available

```bash
$ dva kg check --provider neo4j

Checking NEO4J Prerequisites...

Neo4j Prerequisites Check
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component         ┃ Status ┃ Message                                  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Docker Installed  │ ✓      │ Docker is available                      │
│ Docker Running    │ ✓      │ Docker daemon is running                 │
│ Neo4j Container   │ ✗      │ Neo4j container not found                │
│ Neo4j Connection  │ ✗      │ Cannot connect to Neo4j                  │
└───────────────────┴────────┴──────────────────────────────────────────┘

⚠ Some prerequisites are not met

Setup Instructions:
[Shows Neo4j setup instructions]
```

---

## Implementation Details

### Files Modified

**`kg.py`**:
- Added `--provider` option to `check()` command
- Created `_check_neo4j()` helper function
- Created `_check_lightrag()` helper function
- Default behavior: Check configured provider or LightRAG

### Provider Detection Logic

```python
def check(provider: str | None = None):
    if provider is None:
        try:
            config = KGConfig.load()
            provider = config.provider  # Use configured
        except:
            provider = "lightrag"  # Default to LightRAG
    
    if provider == "neo4j":
        _check_neo4j()
    elif provider == "lightrag":
        _check_lightrag()
```

### LightRAG Check Logic

```python
def _check_lightrag():
    # Check LightRAG server
    client = LightRAGClient(base_url=lightrag_url)
    health = client.health_check()
    
    # Check workspace
    config = KGConfig.load()
    workspace_dir = config.get_workspace_dir()
    
    # Display results
    ...
```

---

## Benefits

### 1. **Provider-Aware**

Checks the right prerequisites for the configured provider:
```bash
# If configured for LightRAG
dva kg check  # Checks LightRAG

# If configured for Neo4j
dva kg check  # Checks Neo4j
```

### 2. **LightRAG as Default**

Makes LightRAG the default when no configuration exists:
```bash
# No config file
dva kg check  # Checks LightRAG (default)
```

### 3. **Explicit Override**

Can explicitly check any provider:
```bash
dva kg check --provider neo4j     # Force Neo4j check
dva kg check --provider lightrag  # Force LightRAG check
```

### 4. **Provider-Specific Guidance**

Shows relevant commands for each provider:
- **LightRAG**: Shows workspace commands, async ingestion
- **Neo4j**: Shows visualization, entity extraction

### 5. **Better Error Messages**

Provider-specific setup instructions:
- **LightRAG**: Start server, create workspace
- **Neo4j**: Start Docker, run container

---

## Workflows

### First-Time Setup (LightRAG)

```bash
# 1. Check prerequisites
dva kg check
# Shows LightRAG not available

# 2. Start LightRAG server
cd lightrag-infrastructure && ./scripts/start.sh

# 3. Initialize configuration
dva kg init --provider lightrag

# 4. Create workspace
dva kg workspace create default

# 5. Verify
dva kg check
# ✓ All prerequisites are met!
```

### First-Time Setup (Neo4j)

```bash
# 1. Check prerequisites
dva kg check --provider neo4j
# Shows Neo4j not available

# 2. Start Neo4j
cd neo4j-infrastructure && ./setup.sh

# 3. Initialize configuration
dva kg init --provider neo4j --uri bolt://localhost:7687

# 4. Verify
dva kg check --provider neo4j
# ✓ All prerequisites are met!
```

### Switching Providers

```bash
# Currently using LightRAG
dva kg check
# Checks LightRAG

# Switch to Neo4j
dva kg init --provider neo4j --uri bolt://localhost:7687

# Now checks Neo4j
dva kg check
# Checks Neo4j

# Explicitly check LightRAG
dva kg check --provider lightrag
# Checks LightRAG
```

---

## Testing

### Test Default Behavior

```bash
# No config
rm ~/.dva-agentic/kg-config.json
dva kg check
# Should check LightRAG (default)
```

### Test Configured Provider

```bash
# Configure LightRAG
dva kg init --provider lightrag
dva kg check
# Should check LightRAG

# Configure Neo4j
dva kg init --provider neo4j --uri bolt://localhost:7687
dva kg check
# Should check Neo4j
```

### Test Explicit Provider

```bash
# Force Neo4j check
dva kg check --provider neo4j

# Force LightRAG check
dva kg check --provider lightrag
```

---

## Summary

✅ **Provider-aware checking** - Checks configured provider  
✅ **LightRAG as default** - Better default for most users  
✅ **Explicit override** - Can force check any provider  
✅ **Provider-specific guidance** - Relevant setup instructions  
✅ **Better error messages** - Clear next steps for each provider  

The refactoring makes `dva kg check` more intelligent and user-friendly by automatically detecting the configured provider and defaulting to LightRAG for new users.
