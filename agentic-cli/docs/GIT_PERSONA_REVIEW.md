# Git Ingestion Persona Review

## Summary

✅ **CONFIRMED**: All Git repository ingestion paths (both sync and async) properly tag documents with `persona="developer"`.

---

## Persona Assignment Flow

### 1. Parser Level (Primary Assignment)

**File:** `src/dva_agentic_cli/kg/parsers.py`

The `parse_git_repository()` function **always** sets `persona="developer"` in the metadata for ALL documents:

```python
# Line 421-432
git_metadata = {
    "source_type": "git",
    "persona": "developer",  # ✅ HARDCODED for all Git repos
    "repo_url": repo_url,
    "repo_name": metadata.get("name", repo_name),
    "domain": metadata.get("domain", ""),
    "purpose": metadata.get("purpose", ""),
    "branch": branch or repo.active_branch.name,
    "tag": tag,
    "commit_hash": commit_hash,
    "commit_date": commit_date,
}
```

This metadata is then attached to **every document** parsed from the repository:

```python
# Line 455-463 (Repository overview document)
documents.append({
    "title": f"Repository: {repo_name}",
    "content": repo_summary,
    "metadata": {
        **git_metadata,  # ✅ Includes persona="developer"
        "doc_type": "repository_overview",
        "format": "git"
    }
})

# Line 495-503 (Source file documents)
doc = {
    "title": f"{relative_path}",
    "content": content,
    "metadata": {
        **git_metadata,  # ✅ Includes persona="developer"
        "doc_type": "source_file",
        "language": language,
        "file_path": str(relative_path),
        "format": "git"
    }
}
```

**Result:** Every document from a Git repository has `persona="developer"` in its metadata.

---

### 2. Ingest Level (Secondary Assignment - Neo4j Only)

**File:** `src/dva_agentic_cli/kg/ingest.py`

For Neo4j ingestion, the `ingest_data()` function also auto-detects persona:

```python
# Line 84-89
# Auto-detect persona from format if not specified
if persona is None:
    if format == "git":
        persona = "developer"  # ✅ Auto-detected for Git
    else:
        persona = "business"  # Default for documents
```

This persona is then used for:
1. **Entity namespacing**: Code entities get `Code::` prefix
2. **Node properties**: Persona stored as node property in Neo4j

```python
# Line 161-164
# Use namespace for code entities (Option D: Hybrid approach)
entity_type = entity.get("type", "Entity")
if persona == "developer" and format == "git":
    # Add Code:: namespace for developer persona
    if not entity_type.startswith("Code::"):
        entity_type = f"Code::{entity_type}"
```

**Note:** This only applies to Neo4j ingestion. LightRAG uses the metadata from documents directly.

---

## Ingestion Paths

### Path 1: Sync Neo4j Ingestion

**Command:** `dva kg ingest --source <git-source> --provider neo4j`

**Flow:**
1. **Command:** `src/dva_agentic_cli/commands/kg.py` (line 493-516)
   - Resolves data source
   - Detects `format="git"` (line 472-473)
   - Calls `ingest_data()` with `persona=None` (line 501)

2. **Ingest:** `src/dva_agentic_cli/kg/ingest.py` (line 84-112)
   - Auto-detects `persona="developer"` from format (line 86-87)
   - Calls `parse_git_repository()` (line 107-112)

3. **Parser:** `src/dva_agentic_cli/kg/parsers.py` (line 421-432)
   - Sets `persona="developer"` in metadata
   - Returns documents with persona metadata

4. **Entity Extraction:** `src/dva_agentic_cli/kg/ingest.py` (line 161-164)
   - Adds `Code::` namespace to entities
   - Stores persona in Neo4j node properties

**Result:** ✅ Git repos tagged as `persona="developer"` with `Code::` entity namespaces

---

### Path 2: Sync LightRAG Ingestion

**Command:** `dva kg ingest --source <git-source> --provider lightrag`

**Flow:**
1. **Command:** `src/dva_agentic_cli/commands/kg.py` (line 518-570)
   - Resolves data source
   - Detects `format="git"` (line 529)
   - Calls `parse_git_repository()` directly (line 530-545)

2. **Parser:** `src/dva_agentic_cli/kg/parsers.py` (line 421-432)
   - Sets `persona="developer"` in metadata
   - Returns documents with persona metadata

3. **Insert:** `src/dva_agentic_cli/commands/kg.py` (line 549-565)
   - Inserts documents into LightRAG
   - Metadata (including persona) passed to LightRAG

**Result:** ✅ Git repos tagged as `persona="developer"` in LightRAG metadata

---

### Path 3: Async Neo4j Ingestion

**Command:** `dva kg async submit --source <git-source> --provider neo4j`

**Flow:**
1. **Submit:** `src/dva_agentic_cli/commands/kg_async.py` (line 93-126)
   - Resolves data source
   - Detects `format="git"` (line 101-102)
   - Submits job with format and metadata

2. **Worker:** `src/dva_agentic_cli/kg/async_worker.py` (line 60-90)
   - Loads job
   - Calls `ingest_data()` with job parameters

3. **Ingest:** `src/dva_agentic_cli/kg/ingest.py` (line 84-112)
   - Auto-detects `persona="developer"` from format
   - Calls `parse_git_repository()`

4. **Parser:** `src/dva_agentic_cli/kg/parsers.py` (line 421-432)
   - Sets `persona="developer"` in metadata
   - Returns documents with persona metadata

**Result:** ✅ Git repos tagged as `persona="developer"` with `Code::` entity namespaces

---

### Path 4: Async LightRAG Ingestion

**Command:** `dva kg async submit --source <git-source> --provider lightrag`

**Flow:**
1. **Submit:** `src/dva_agentic_cli/commands/kg_async.py` (line 93-126)
   - Resolves data source
   - Detects `format="git"` (line 101-102)
   - Submits job with format and metadata

2. **Worker:** `src/dva_agentic_cli/kg/async_worker.py` (line 115-148)
   - Loads job
   - Detects `format="git"` (line 120)
   - Calls `parse_git_repository()` directly (line 125-136)

3. **Parser:** `src/dva_agentic_cli/kg/parsers.py` (line 421-432)
   - Sets `persona="developer"` in metadata
   - Returns documents with persona metadata

4. **Insert:** `src/dva_agentic_cli/kg/async_worker.py` (line 158-178)
   - Inserts documents into LightRAG
   - Metadata (including persona) passed to LightRAG

**Result:** ✅ Git repos tagged as `persona="developer"` in LightRAG metadata

---

## Verification Points

### 1. Parser Metadata

Every document from `parse_git_repository()` includes:

```python
{
    "title": "...",
    "content": "...",
    "metadata": {
        "source_type": "git",
        "persona": "developer",  # ✅ ALWAYS SET
        "repo_url": "...",
        "repo_name": "...",
        "domain": "...",
        "purpose": "...",
        "branch": "...",
        "tag": "...",
        "commit_hash": "...",
        "commit_date": "...",
        "doc_type": "source_file" | "repository_overview",
        "format": "git",
        "language": "...",  # for source files
        "file_path": "..."  # for source files
    }
}
```

### 2. Neo4j Entity Namespacing

For Neo4j, entities from Git repos get `Code::` prefix:

```python
# Original entity type: "Function"
# After namespacing: "Code::Function"

# Original entity type: "Class"
# After namespacing: "Code::Class"
```

This allows filtering by entity type:
```cypher
// Find all code entities
MATCH (n) WHERE n.type STARTS WITH "Code::" RETURN n

// Find all code functions
MATCH (n:Code::Function) RETURN n
```

### 3. LightRAG Metadata

For LightRAG, the persona is stored in document metadata and used for query enhancement:

```python
# Query with developer persona
enhanced_query = f"From the code/developer perspective: {query_text}"

# Search with developer persona
enhanced_text = f"From the code/developer perspective: {search_text}"
```

---

## Query/Search Behavior

### With Persona Filter

**Query:**
```bash
`agent kg query "patient authentication" --persona developer
```

**Neo4j:**
- Filters to nodes with `persona="developer"`
- Focuses on `Code::*` labeled nodes
- Returns code-related entities (functions, classes, modules)

**LightRAG:**
- Enhances query: `"From the code/developer perspective: patient authentication"`
- LightRAG uses metadata to focus on developer context
- Returns code-related documents

### Without Persona Filter

**Query:**
```bash
`agent kg query "patient authentication"
```

**Neo4j:**
- Returns all nodes (both developer and business)
- Includes both `Code::*` and regular entities

**LightRAG:**
- No query enhancement
- Returns all documents (both code and docs)

---

## Code Locations

### Primary Persona Assignment

1. **`src/dva_agentic_cli/kg/parsers.py`** (line 423)
   - `"persona": "developer"` hardcoded in `git_metadata`
   - Applied to ALL documents from Git repos

### Secondary Persona Assignment (Neo4j only)

2. **`src/dva_agentic_cli/kg/ingest.py`** (line 86-87)
   - Auto-detects `persona="developer"` for `format="git"`
   - Used for entity namespacing

### Format Detection

3. **`src/dva_agentic_cli/commands/kg.py`** (line 472-473)
   - Sync ingestion: Sets `resolved_format="git"` for Git sources

4. **`src/dva_agentic_cli/commands/kg_async.py`** (line 101-102)
   - Async ingestion: Sets `format="git"` for Git sources

### Entity Namespacing (Neo4j only)

5. **`src/dva_agentic_cli/kg/ingest.py`** (line 161-164)
   - Adds `Code::` prefix to entities when `persona="developer"` and `format="git"`

### Query Enhancement (LightRAG)

6. **`src/dva_agentic_cli/commands/kg.py`** (line 726-729, 849-852)
   - Query: Enhances with "From the code/developer perspective:"
   - Search: Enhances with "From the code/developer perspective:"

---

## Testing Verification

### Check Metadata in Documents

After ingestion, check a document's metadata:

```python
# For LightRAG
`agent kg search "patient" --persona developer

# Should return documents with persona="developer" in metadata
```

### Check Neo4j Nodes

Query Neo4j directly:

```cypher
// Find all developer persona nodes
MATCH (n) WHERE n.persona = "developer" RETURN n LIMIT 10

// Find all code entities
MATCH (n) WHERE n.type STARTS WITH "Code::" RETURN n LIMIT 10

// Count by persona
MATCH (n) RETURN n.persona, count(*) as count
```

### Check LightRAG Stats

```bash
`agent kg stats

# Should show entities with developer persona
```

---

## Conclusion

✅ **All Git ingestion paths properly assign `persona="developer"`:**

1. **Sync Neo4j**: ✅ Persona set at parser level + ingest level
2. **Sync LightRAG**: ✅ Persona set at parser level
3. **Async Neo4j**: ✅ Persona set at parser level + ingest level
4. **Async LightRAG**: ✅ Persona set at parser level

**Key Points:**
- Persona is **hardcoded** as `"developer"` in `parse_git_repository()` (line 423)
- This ensures **100% consistency** across all ingestion paths
- Neo4j additionally uses persona for **entity namespacing** (`Code::*`)
- LightRAG uses persona for **query enhancement** and **filtering**

**No changes needed** - the implementation is correct and consistent!
