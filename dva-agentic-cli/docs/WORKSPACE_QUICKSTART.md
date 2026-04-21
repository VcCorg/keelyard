# Workspace Quick Start Guide

## What are Workspaces?

Workspaces allow you to maintain **multiple isolated knowledge graphs** for different purposes:
- 🏭 **Production**: Live production data
- 🧪 **Evaluation**: Test datasets for agent evaluation
- 🔬 **Experiments**: Try different data patterns
- 📊 **Staging**: Pre-production testing

**Note**: Workspaces are **only available for LightRAG provider**. Neo4j uses a single database.

---

## Prerequisites

1. **LightRAG provider configured**:
   ```bash
   dva kg init --provider lightrag --lightrag-url http://localhost:8001
   ```

2. **LightRAG server running**:
   ```bash
   cd lightrag-infrastructure
   ./setup.sh
   ```

---

## Quick Start (5 minutes)

### 1. Create Your First Workspace

```bash
# Create a production workspace
dva kg workspace create production \
  --env production \
  --description "Production knowledge graph" \
  --tags prod,cwow
```

**Output**:
```
✓ Workspace 'production' created

╭─ Workspace Details ─────────────────────────╮
│ Name:        production                     │
│ Environment: production                     │
│ Created:     2025-01-15T10:00:00Z          │
│ Tags:        prod, cwow                     │
│ Path:        /data/lightrag/production      │
╰─────────────────────────────────────────────╯

To switch to this workspace: dva kg workspace switch production
```

### 2. Create Evaluation Workspaces

```bash
# Baseline evaluation dataset
dva kg workspace create eval-baseline \
  --env evaluation \
  --description "Baseline evaluation dataset"

# Experiment dataset
dva kg workspace create eval-experiment-1 \
  --env evaluation \
  --description "Enhanced data experiment"
```

### 3. List All Workspaces

```bash
dva kg workspace list
```

**Output**:
```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name              ┃ Environment ┃ Documents ┃ Entities ┃ Created    ┃ Active ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ default           │ development │         0 │        0 │ 2025-01-15 │   ✓    │
│ eval-baseline     │ evaluation  │         0 │        0 │ 2025-01-15 │        │
│ eval-experiment-1 │ evaluation  │         0 │        0 │ 2025-01-15 │        │
│ production        │ production  │         0 │        0 │ 2025-01-15 │        │
└───────────────────┴─────────────┴───────────┴──────────┴────────────┴────────┘

Active workspace: default
Base directory: /data/lightrag
```

### 4. Switch to a Workspace

```bash
dva kg workspace switch production
```

**Output**:
```
✓ Switched to workspace 'production'
Environment: production
Path: /data/lightrag/production
```

### 5. Ingest Data into Active Workspace

```bash
# Ingest into currently active workspace (production)
dva kg ingest --source cwow-docs
```

**Output**:
```
Active workspace: production
✓ Ingested 148 documents into production workspace
```

### 6. Ingest into Specific Workspace

```bash
# Ingest into eval-baseline without switching
dva kg ingest --source cwow-docs --workspace eval-baseline
```

**Output**:
```
ℹ Using workspace: eval-baseline
✓ Ingested 148 documents into eval-baseline workspace
```

### 7. Query Different Workspaces

```bash
# Query production
dva kg query "How to identify active patients?" --workspace production

# Query baseline
dva kg query "How to identify active patients?" --workspace eval-baseline

# Compare results
```

### 8. Show Current Workspace

```bash
dva kg workspace current
```

**Output**:
```
╭─ Current Workspace ──────────────────────────────╮
│ Name:         production                         │
│ Environment:  production                         │
│ Description:  Production knowledge graph         │
│ Tags:         prod, cwow                         │
│ Documents:    148                                │
│ Entities:     0                                  │
│ Relations:    0                                  │
│ Created:      2025-01-15T10:00:00Z              │
│ Last Updated: 2025-01-15T12:00:00Z              │
│ Path:         /data/lightrag/production          │
╰──────────────────────────────────────────────────╯
```

---

## Common Workflows

### Agent Evaluation Workflow

```bash
# 1. Create evaluation workspaces
dva kg workspace create eval-v1 --env evaluation --description "Version 1"
dva kg workspace create eval-v2 --env evaluation --description "Version 2"

# 2. Ingest different datasets
dva kg ingest --source baseline-data --workspace eval-v1
dva kg ingest --source enhanced-data --workspace eval-v2

# 3. Run evaluation queries
for workspace in eval-v1 eval-v2; do
  echo "Testing: $workspace"
  dva kg query "patient status query" --workspace $workspace > results-$workspace.txt
done

# 4. Compare results
diff results-eval-v1.txt results-eval-v2.txt
```

### Clone Workspace for Experiments

```bash
# Clone production for testing
dva kg workspace create test-experiment --parent production

# Now test-experiment has all production data
dva kg workspace switch test-experiment

# Make changes without affecting production
dva kg ingest --source experimental-data
```

### Update Workspace Metadata

```bash
# Update description and tags
dva kg workspace update production \
  --description "Updated production KG" \
  --tags prod,cwow,v2 \
  --env production
```

### Delete Workspace

```bash
# Switch away from workspace first
dva kg workspace switch default

# Delete workspace
dva kg workspace delete eval-experiment-1

# Confirm deletion
# Output: ✓ Workspace 'eval-experiment-1' deleted
```

---

## Command Reference

### Create Workspace
```bash
dva kg workspace create <name> [OPTIONS]

Options:
  -d, --description TEXT   Workspace description
  -t, --tags TEXT         Comma-separated tags
  -e, --env TEXT          Environment (development|evaluation|production|staging)
  -p, --parent TEXT       Parent workspace to clone from
```

### List Workspaces
```bash
dva kg workspace list
```

### Switch Workspace
```bash
dva kg workspace switch <name>
```

### Show Current Workspace
```bash
dva kg workspace current
```

### Show Workspace Info
```bash
dva kg workspace info <name>
```

### Update Workspace
```bash
dva kg workspace update <name> [OPTIONS]

Options:
  -d, --description TEXT   New description
  -t, --tags TEXT         New tags
  -e, --env TEXT          New environment
```

### Delete Workspace
```bash
dva kg workspace delete <name> [OPTIONS]

Options:
  -y, --yes    Skip confirmation
  -f, --force  Force delete default workspace
```

---

## Tips & Best Practices

### 1. Naming Convention
Use descriptive, hierarchical names:
- ✅ `production`, `staging`, `development`
- ✅ `eval-baseline`, `eval-experiment-1`, `eval-test-2`
- ✅ `cwow-v1`, `cwow-v2`, `cwow-staging`
- ❌ `test`, `temp`, `workspace1`

### 2. Environment Tags
Use environments to organize workspaces:
- `production`: Live data
- `evaluation`: Test datasets
- `staging`: Pre-production
- `development`: Dev/testing

### 3. Tagging Strategy
Tag workspaces for easy filtering:
```bash
--tags baseline,cwow,census
--tags experiment,enhanced,v2
--tags production,live,validated
```

### 4. Workspace Lifecycle
```
development → staging → production
     ↓
evaluation-v1, evaluation-v2, ...
```

### 5. Disk Space Management
Monitor workspace sizes:
```bash
du -sh /data/lightrag/*
```

Delete unused workspaces:
```bash
dva kg workspace delete old-experiment --yes
```

---

## Troubleshooting

### Error: "Workspaces only supported for LightRAG"
**Problem**: Trying to use workspaces with Neo4j provider

**Solution**: Switch to LightRAG:
```bash
dva kg init --provider lightrag --lightrag-url http://localhost:8001
```

### Error: "Workspace does not exist"
**Problem**: Workspace not created yet

**Solution**: Create the workspace:
```bash
dva kg workspace create <name>
```

### Error: "Cannot delete active workspace"
**Problem**: Trying to delete currently active workspace

**Solution**: Switch to another workspace first:
```bash
dva kg workspace switch default
dva kg workspace delete <name>
```

### Workspace Not Showing Data
**Problem**: Ingested into wrong workspace

**Solution**: Check active workspace:
```bash
dva kg workspace current
```

Switch to correct workspace:
```bash
dva kg workspace switch <correct-workspace>
```

---

## Next Steps

1. **Read the full documentation**: `docs/WORKSPACE_IMPLEMENTATION_SUMMARY.md`
2. **Review design decisions**: `docs/KG_VERSIONING_SEGMENTATION_DESIGN.md`
3. **Check test coverage**: `tests/test_workspace.py`
4. **Explore evaluation workflows**: Create multiple workspaces and compare results

---

## FAQ

**Q: Can I use workspaces with Neo4j?**  
A: No, workspaces are only for LightRAG. Neo4j uses a single database instance.

**Q: How much disk space does each workspace use?**  
A: Depends on data size. ~1GB for 148 documents. Use `du -sh /data/lightrag/*` to check.

**Q: Can I query across multiple workspaces?**  
A: Not currently. Each query targets one workspace. You can run multiple queries and compare results.

**Q: What happens to my existing data?**  
A: Existing data in `/data/lightrag` becomes the "default" workspace automatically.

**Q: Can I rename a workspace?**  
A: Not directly. Clone to new name, then delete old workspace.

**Q: How do I backup a workspace?**  
A: Copy the workspace directory: `cp -r /data/lightrag/production /backup/production`

**Q: Can I share workspaces between systems?**  
A: Yes, copy the workspace directory and metadata from `workspaces.json`.

---

## Summary

✅ **Isolated KG environments** for different purposes  
✅ **Easy switching** between workspaces  
✅ **Clone workspaces** for experiments  
✅ **Perfect for agent evaluation** workflows  
✅ **LightRAG only** - Neo4j unaffected  

Start using workspaces today to organize your knowledge graphs!
