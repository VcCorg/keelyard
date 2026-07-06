# Knowledge Graph Versioning & Segmentation Design

## Executive Summary

This document proposes a comprehensive design for implementing versioning and segmentation in the KEEL Knowledge Graph system to support:
1. **Agent Evaluation** with different KG data patterns
2. **Multi-tenant KG environments** for different use cases
3. **Time-based versioning** for data evolution tracking
4. **Selective data retrieval** for targeted queries

---

## Current Architecture Analysis

### LightRAG Implementation
- **Working Directory**: Single `/data/lightrag` directory
- **Storage**: File-based (nano-vectordb for vectors, networkx for graph)
- **Metadata**: Basic metadata support in insert operations
- **No Built-in Versioning**: All data in one namespace

### Neo4j Implementation
- **Database**: Single Neo4j database instance
- **Labels**: Node labels for entity types
- **Properties**: Node/relationship properties for metadata
- **No Built-in Versioning**: All data in one graph

### Current Metadata Support
```python
# Already supported in ingestion
metadata = {
    "name": "source_name",
    "description": "...",
    "tags": ["tag1", "tag2"],
    "domain": "healthcare",
    "purpose": "...",
    "persona": "developer|business",
    "branch": "main",  # Git-specific
    "tag": "v1.0.0"    # Git-specific
}
```

---

## Proposed Solutions

## Option 1: Multi-Workspace Approach (Recommended for LightRAG)

### Concept
Create separate working directories for different KG versions/segments.

### Implementation

#### 1.1 Configuration Extension
```python
# src/agentic_cli/kg/config.py
class KGConfig(BaseModel):
    # ... existing fields ...
    
    # New fields for versioning
    workspace: str = Field(default="default", description="KG workspace name")
    workspace_base_dir: str = Field(default="/data/lightrag", description="Base directory for workspaces")
    
    def get_workspace_dir(self) -> str:
        """Get the full path to the current workspace."""
        return f"{self.workspace_base_dir}/{self.workspace}"
```

#### 1.2 Workspace Management Commands
```bash
# Create/switch workspaces
`agent kg workspace create production
`agent kg workspace create evaluation-v1
`agent kg workspace create evaluation-v2
`agent kg workspace list
`agent kg workspace switch evaluation-v1
`agent kg workspace delete evaluation-v2

# Show current workspace
`agent kg workspace current
```

#### 1.3 Workspace-Aware Ingestion
```bash
# Ingest into specific workspace
`agent kg ingest --source cwow-docs --workspace production
`agent kg ingest --source cwow-docs --workspace evaluation-v1

# Query from specific workspace
`agent kg query "patient status" --workspace production
`agent kg query "patient status" --workspace evaluation-v1
```

#### 1.4 Directory Structure
```
/data/lightrag/
├── default/              # Default workspace
│   ├── vdb_entities.json
│   ├── vdb_relationships.json
│   ├── graph_chunk_entity_relation.graphml
│   └── kv_store_*.json
├── production/           # Production workspace
│   └── ...
├── evaluation-v1/        # Evaluation workspace v1
│   └── ...
├── evaluation-v2/        # Evaluation workspace v2
│   └── ...
└── workspaces.json       # Workspace metadata
```

#### 1.5 Workspace Metadata
```json
{
  "workspaces": {
    "default": {
      "created_at": "2025-01-01T00:00:00Z",
      "description": "Default workspace",
      "tags": [],
      "document_count": 148,
      "last_updated": "2025-01-15T10:30:00Z"
    },
    "production": {
      "created_at": "2025-01-10T00:00:00Z",
      "description": "Production KG with CWOW data",
      "tags": ["production", "cwow"],
      "document_count": 200,
      "last_updated": "2025-01-15T12:00:00Z"
    },
    "evaluation-v1": {
      "created_at": "2025-01-12T00:00:00Z",
      "description": "Evaluation dataset v1 - baseline",
      "tags": ["evaluation", "baseline"],
      "document_count": 50,
      "last_updated": "2025-01-12T15:00:00Z",
      "parent_workspace": "production",
      "snapshot_of": "production@2025-01-12"
    }
  },
  "active_workspace": "production"
}
```

### Advantages
- ✅ Complete isolation between versions
- ✅ Easy to switch between versions
- ✅ No query-time filtering overhead
- ✅ Simple backup/restore per workspace
- ✅ Can run parallel evaluations

### Disadvantages
- ❌ Duplicated data across workspaces
- ❌ More disk space required
- ❌ Need to manage multiple directories

---

## Option 2: Metadata-Based Segmentation (Recommended for Neo4j)

### Concept
Use metadata labels/properties to segment data within a single graph.

### Implementation

#### 2.1 Enhanced Metadata Schema
```python
# Add to all nodes/documents
metadata = {
    "workspace": "production",
    "version": "v1.0.0",
    "segment": "cwow-census",
    "environment": "production|evaluation|development",
    "created_at": "2025-01-15T10:00:00Z",
    "ingestion_id": "ing_abc123",
    "tags": ["patient", "facility", "census"],
    "persona": "business",
    "source": "cwow-docs"
}
```

#### 2.2 Neo4j Label Strategy
```cypher
// Add version/segment labels to nodes
CREATE (p:Patient:V1:Production {name: "John Doe", ...})
CREATE (f:Facility:V1:Production {name: "Facility A", ...})

// Query specific version
MATCH (p:Patient:V1) RETURN p

// Query across versions
MATCH (p:Patient) WHERE p.version IN ['v1', 'v2'] RETURN p
```

#### 2.3 Filtered Query Interface
```bash
# Query with filters
`agent kg query "patient status" --workspace production --version v1
`agent kg query "patient status" --segment cwow-census
`agent kg query "patient status" --tags patient,facility

# Search with filters
`agent kg search "active patient" --workspace evaluation-v1
```

#### 2.4 Segment Management
```bash
# Create segment
`agent kg segment create cwow-census --description "CWOW Census List data"

# Ingest into segment
`agent kg ingest --source cwow-docs --segment cwow-census --version v1

# List segments
`agent kg segment list

# Clear segment
`agent kg segment clear cwow-census --version v1
```

### Advantages
- ✅ Single graph with flexible querying
- ✅ Less disk space (no duplication)
- ✅ Can query across versions
- ✅ Easy to add new metadata dimensions

### Disadvantages
- ❌ Query-time filtering overhead
- ❌ More complex query logic
- ❌ Risk of data mixing if filters not applied correctly

---

## Option 3: Hybrid Approach (Best of Both Worlds)

### Concept
Combine workspaces for major versions with metadata for fine-grained segmentation.

### Implementation

#### 3.1 Structure
```
Workspaces (major versions):
├── production/
│   ├── Segments: cwow-census, cwow-facility, cwow-patient
│   └── Versions: v1.0, v1.1, v1.2
├── evaluation-baseline/
│   ├── Segments: cwow-census
│   └── Versions: v1.0
└── evaluation-experiment-1/
    ├── Segments: cwow-census
    └── Versions: v1.0
```

#### 3.2 Usage
```bash
# Create workspace for evaluation
`agent kg workspace create evaluation-baseline

# Ingest with segment and version
`agent kg ingest --source cwow-docs \
  --workspace evaluation-baseline \
  --segment cwow-census \
  --version v1.0 \
  --tags baseline,census

# Query specific combination
`agent kg query "patient status" \
  --workspace evaluation-baseline \
  --segment cwow-census \
  --version v1.0
```

---

## Option 4: Time-Based Versioning

### Concept
Automatic versioning based on ingestion timestamps.

### Implementation

#### 4.1 Temporal Metadata
```python
metadata = {
    "ingested_at": "2025-01-15T10:00:00Z",
    "valid_from": "2025-01-15T10:00:00Z",
    "valid_until": None,  # null = current
    "snapshot_id": "snap_20250115_100000",
    "parent_snapshot": "snap_20250114_100000"
}
```

#### 4.2 Temporal Queries
```bash
# Query as of specific time
`agent kg query "patient status" --as-of "2025-01-15T10:00:00Z"

# Query between time range
`agent kg query "patient status" --from "2025-01-01" --to "2025-01-15"

# Create snapshot
`agent kg snapshot create baseline-2025-01-15

# Restore from snapshot
`agent kg snapshot restore baseline-2025-01-15
```

---

## Evaluation-Specific Features

### 5.1 Evaluation Dataset Management

```bash
# Create evaluation dataset from production
`agent kg eval create-dataset \
  --name baseline-v1 \
  --source-workspace production \
  --segment cwow-census \
  --sample-size 100 \
  --stratify-by patient_type

# List evaluation datasets
`agent kg eval list-datasets

# Compare agent performance across datasets
`agent kg eval compare \
  --agent agent-v1 \
  --datasets baseline-v1,baseline-v2,experiment-1
```

### 5.2 A/B Testing Support

```python
# Evaluation configuration
evaluation_config = {
    "name": "census-list-evaluation",
    "datasets": [
        {
            "name": "baseline",
            "workspace": "evaluation-baseline",
            "segment": "cwow-census",
            "version": "v1.0"
        },
        {
            "name": "enhanced",
            "workspace": "evaluation-enhanced",
            "segment": "cwow-census",
            "version": "v1.1"
        }
    ],
    "metrics": ["accuracy", "recall", "response_time"],
    "queries": [
        "How to identify active patients?",
        "What are patient status categories?",
        "Explain census list filters"
    ]
}
```

### 5.3 Dataset Versioning

```bash
# Tag dataset version
`agent kg eval tag-dataset baseline-v1 --version 1.0.0

# Create dataset from query results
`agent kg eval create-dataset-from-query \
  --name patient-status-subset \
  --query "MATCH (p:Patient)-[:HAS_STATUS]->(s:Status) RETURN p, s" \
  --workspace production

# Export dataset for external evaluation
`agent kg eval export-dataset baseline-v1 --format json --output baseline-v1.json
```

---

## Implementation Roadmap

### Phase 1: Basic Workspace Support (Week 1-2)
- [ ] Add workspace field to KGConfig
- [ ] Implement workspace directory management
- [ ] Add workspace commands (create, list, switch, delete)
- [ ] Update ingestion to use workspace directories
- [ ] Update query/search to use active workspace

### Phase 2: Metadata Enhancement (Week 3-4)
- [ ] Extend metadata schema with version, segment, environment
- [ ] Add metadata filtering to queries
- [ ] Implement segment management commands
- [ ] Add workspace metadata tracking

### Phase 3: Evaluation Features (Week 5-6)
- [ ] Implement evaluation dataset creation
- [ ] Add dataset comparison tools
- [ ] Create evaluation metrics tracking
- [ ] Build A/B testing framework

### Phase 4: Advanced Features (Week 7-8)
- [ ] Time-based versioning
- [ ] Snapshot/restore functionality
- [ ] Cross-workspace queries
- [ ] Performance optimization

---

## Recommended Approach

### For Immediate Implementation: **Option 1 (Multi-Workspace) + Enhanced Metadata**

**Why:**
1. **Simplest to implement** - minimal changes to existing code
2. **Complete isolation** - no risk of data mixing during evaluation
3. **Flexible** - can add metadata filtering later
4. **Performant** - no query-time filtering overhead

**Implementation Priority:**
1. ✅ Workspace management (create, switch, list, delete)
2. ✅ Workspace-aware ingestion
3. ✅ Workspace-aware queries
4. ✅ Enhanced metadata (version, segment, tags)
5. ✅ Evaluation dataset creation from workspaces

### Example Usage Flow

```bash
# Setup
`agent kg workspace create production
`agent kg workspace create eval-baseline
`agent kg workspace create eval-experiment-1

# Ingest production data
`agent kg workspace switch production
`agent kg ingest --source cwow-docs --segment census --version v1.0

# Create evaluation datasets
`agent kg workspace switch eval-baseline
`agent kg ingest --source cwow-docs --segment census --version v1.0 --sample 100

`agent kg workspace switch eval-experiment-1
`agent kg ingest --source cwow-docs-enhanced --segment census --version v1.1 --sample 100

# Evaluate agents
`agent kg eval run \
  --agent agent-v1 \
  --workspaces eval-baseline,eval-experiment-1 \
  --queries queries.json \
  --output results.json

# Compare results
`agent kg eval compare results.json --metric accuracy
```

---

## Technical Considerations

### Storage Requirements
- **Workspace approach**: ~1GB per workspace (for 148 documents)
- **Metadata approach**: ~1GB total + query overhead
- **Recommendation**: Use workspaces for major versions, metadata for fine-grained filtering

### Performance Impact
- **Workspace switching**: Minimal (just change directory path)
- **Metadata filtering**: 10-20% query overhead for complex filters
- **Cross-workspace queries**: Not supported initially (can add later)

### Backup Strategy
```bash
# Backup specific workspace
`agent kg backup --workspace production --output production-backup.tar.gz

# Restore workspace
`agent kg restore --workspace production --input production-backup.tar.gz

# Clone workspace
`agent kg workspace clone production evaluation-v2
```

---

## Questions to Consider

1. **How many evaluation datasets do you anticipate?**
   - Few (< 5): Multi-workspace is perfect
   - Many (> 10): Consider metadata-based segmentation

2. **Do you need to query across versions?**
   - Yes: Use metadata-based or hybrid approach
   - No: Multi-workspace is simpler

3. **What's your evaluation frequency?**
   - Continuous: Automate workspace creation
   - Periodic: Manual workspace management is fine

4. **Storage constraints?**
   - Limited: Use metadata-based segmentation
   - Ample: Multi-workspace for simplicity

5. **Do you need time-travel queries?**
   - Yes: Implement temporal versioning
   - No: Simple version tags are sufficient

---

## Next Steps

1. **Review this design** with the team
2. **Choose the approach** based on your requirements
3. **Prioritize features** for implementation
4. **Create detailed implementation tickets**
5. **Start with Phase 1** (Basic Workspace Support)

Let me know which approach resonates with your use case, and I can help implement it!
