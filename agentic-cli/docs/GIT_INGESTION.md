# Git Repository Ingestion for Knowledge Graph

## Overview

This document describes the Git repository ingestion feature for the DVA KG system, which enables ingesting source code from Git repositories with developer persona support.

## Implementation Summary

### ✅ Completed Components

#### 1. Dependencies (`pyproject.toml`)
- Added `gitpython>=3.1.40` for Git repository cloning
- Added `gitingest>=0.1.0` for parsing Git repositories

#### 2. Code Analyzer (`kg/code_analyzer.py`)
**Purpose:** Extract code structure from Python and Java files

**Features:**
- **PythonAnalyzer**: Uses AST to extract:
  - Imports and dependencies
  - Classes with methods
  - Top-level functions
  - Docstrings and signatures
  - Line numbers for code chunks

- **JavaAnalyzer**: Uses regex patterns to extract:
  - Package declarations
  - Imports
  - Classes with methods
  - Interfaces
  - Visibility modifiers

**Quick Summary Generation:**
- Each file gets a one-line summary: `"Python module: auth.py | Imports: 5 modules | Classes: UserAuth, TokenManager | Functions: validate_token"`

#### 3. Git Parser (`kg/parsers.py::parse_git_repository`)
**Purpose:** Clone Git repos and create smart-chunked documents

**Implementation Flow:**
1. Clone repository to temp directory
2. Checkout specific branch/tag if specified
3. Generate repository digest using gitingest
4. Scan for Python (.py) and Java (.java) files
5. Analyze each file with code_analyzer
6. Create documents for:
   - Repository overview
   - Each source file (with summary)
   - Each class (with code chunk)
   - Each function (with code chunk)
7. Clean up temp directory

**Metadata Captured:**
- `source_type`: "git"
- `persona`: "developer"
- `repo_url`: Full Git URL
- `repo_name`: Repository name
- `domain`: Business domain (from user input)
- `purpose`: Repository purpose (from user input)
- `branch`: Branch name
- `tag`: Tag name
- `commit_hash`: Short commit hash (8 chars)
- `commit_date`: ISO 8601 timestamp
- `language`: "python" or "java"
- `file_path`: Relative path in repo
- `doc_type`: "repository_overview", "source_file", "class", or "function"

#### 4. Ingest Pipeline (`kg/ingest.py`)
**Purpose:** Orchestrate ingestion with persona support

**New Parameters:**
- `persona`: Optional persona tag ("developer", "business", or auto-detect)
- `metadata`: Additional metadata dict (for Git: name, domain, purpose, branch, tag)

**Persona Auto-Detection:**
- `format == "git"` → `persona = "developer"`
- Other formats → `persona = "business"`

**Hybrid Namespace Approach (Option D):**
- Developer persona + Git format → Add `Code::` namespace to entity types
- Example: `"Function"` becomes `"Code::Function"`
- All entities get `persona` property for flexible querying

**Neo4j Node Structure:**
```python
{
    "label": "Code::Function",  # Namespace for code entities
    "properties": {
        "id": "repo/path/file.py::function_name",
        "name": "function_name",
        "content": "def function_name(args):\n    ...",
        "persona": "developer",  # Persona property
        "metadata": {
            "repo_name": "backend-api",
            "domain": "authentication",
            "purpose": "User authentication service",
            "language": "python",
            "file_path": "src/auth/validators.py",
            "doc_type": "function",
            "args": ["token", "user_id"]
        }
    }
}
```

---

## Usage Examples

### 1. Register Git Repository as Data Source

```bash
# Register with metadata
`agent data create \
  --name backend-api \
  --source-type git \
  --source-location https://github.com/org/backend-api.git \
  --git-branch main \
  --description "Backend API for patient management" \
  --tags "api,python,backend,authentication"
```

### 2. Ingest Git Repository

```bash
# Ingest using data source name
`agent kg ingest --source backend-api

# Or ingest directly with URL
`agent kg ingest --path https://github.com/org/backend-api.git --format git
```

### 3. Query with Persona Filter (Coming Soon)

```bash
# Query only code (developer persona)
`agent kg query "authentication middleware" --persona developer

# Query only docs (business persona)
`agent kg query "patient data requirements" --persona business

# Query both (no filter)
`agent kg query "how is patient authentication implemented"
```

---

## Persona Separation Strategy

### Option D: Hybrid Namespace + Metadata

**Why This Approach?**
1. **Namespaces** (`Code::`, `Doc::`) provide clear visual separation
2. **Metadata** (`persona` property) enables flexible filtering
3. **Best of both worlds** for querying and visualization

**Entity Type Examples:**

| Source Type | Persona | Original Type | Final Label | Persona Property |
|-------------|---------|---------------|-------------|------------------|
| Git | developer | Function | `Code::Function` | `developer` |
| Git | developer | Class | `Code::Class` | `developer` |
| Git | developer | Module | `Code::Module` | `developer` |
| PDF | business | Requirement | `Requirement` | `business` |
| Confluence | business | Document | `Document` | `business` |

**Query Patterns:**

```cypher
// Find all code entities
MATCH (n) WHERE n.persona = 'developer' RETURN n

// Find all code functions
MATCH (n:Code:Function) RETURN n

// Find developer entities in specific domain
MATCH (n) 
WHERE n.persona = 'developer' 
  AND n.metadata CONTAINS 'authentication'
RETURN n

// Find relationships between code and docs
MATCH (code)-[r]-(doc)
WHERE code.persona = 'developer' 
  AND doc.persona = 'business'
RETURN code, r, doc
```

---

## Code Entity Types

### Repository Level
- `Code::Repository`: The repository itself with overview

### File Level
- `Code::Module`: Python modules or Java packages
- `Code::SourceFile`: Individual source files with summary

### Code Structure
- `Code::Class`: Class definitions with methods list
- `Code::Function`: Functions/methods with signatures
- `Code::Interface`: Java interfaces (Java only)

### Data Model (SQL/DDL/DML)
- `Code::Table`: Database table definitions with columns
- `Code::View`: Database views with queries
- `Code::Procedure`: Stored procedures
- `Code::Function`: SQL functions (database functions)
- `Code::Index`: Database indexes
- `Code::Constraint`: Foreign keys, unique constraints, etc.

### Dependencies
- `Code::Import`: Import statements and dependencies
- `Code::Package`: Package declarations (Java)

---

## Smart Chunking Strategy

### Why Smart Chunking?
- **Context Preservation**: Each function/class is a self-contained chunk
- **Precise Retrieval**: Query for specific functions, not entire files
- **Better Embeddings**: Smaller, focused chunks create better semantic matches
- **Scalability**: Works with repos of any size

### Document Hierarchy

```
Repository: backend-api
├── Overview Document (gitingest summary)
├── src/auth/validators.py (file summary)
│   ├── Class: TokenValidator (with code)
│   │   └── Methods: validate, refresh, revoke
│   ├── Function: validate_token (with code)
│   └── Function: check_expiry (with code)
└── src/auth/middleware.py (file summary)
    ├── Class: AuthMiddleware (with code)
    └── Function: authenticate_request (with code)
```

### Chunk Sizes
- **Repository overview**: Full gitingest digest (~2-5KB)
- **File summary**: First 1000 chars + metadata
- **Class chunk**: Full class definition (extracted by line numbers)
- **Function chunk**: Full function definition (extracted by line numbers)

---

## Git Metadata Tracking

### Repository Metadata
```json
{
  "repo_url": "https://github.com/org/backend-api.git",
  "repo_name": "backend-api",
  "domain": "authentication",
  "purpose": "User authentication and authorization service",
  "branch": "main",
  "tag": null,
  "commit_hash": "a1b2c3d4",
  "commit_date": "2025-11-22T22:05:00-06:00"
}
```

### File Metadata
```json
{
  "language": "python",
  "file_path": "src/auth/validators.py",
  "doc_type": "source_file",
  "imports": ["jwt", "datetime", "typing"],
  "classes": ["TokenValidator", "RefreshTokenValidator"],
  "functions": ["validate_token", "check_expiry"]
}
```

### Code Entity Metadata
```json
{
  "doc_type": "function",
  "function_name": "validate_token",
  "args": ["token", "secret_key", "algorithms"],
  "line_start": 45,
  "line_end": 62
}
```

---

## Next Steps (Pending Implementation)

### 1. Update KG Ingest Command
- [ ] Detect Git source type from data sources
- [ ] Extract Git metadata (branch, tag, name, domain, purpose)
- [ ] Pass metadata to ingest_data() function
- [ ] Handle Git-specific errors (auth, network, invalid repos)

### 2. LightRAG Integration
- [ ] Add persona to LightRAG document metadata
- [ ] Update LightRAG insert to include persona tags
- [ ] Test persona-based retrieval in LightRAG

### 3. Query Enhancements
- [ ] Add `--persona` flag to `dva kg query` command
- [ ] Update Neo4j queries to filter by persona
- [ ] Update LightRAG queries to filter by persona
- [ ] Add persona context to LLM prompts

### 4. Code-Specific Entity Extraction
- [ ] Create code-specific extraction prompts
- [ ] Extract function call relationships
- [ ] Extract class inheritance relationships
- [ ] Extract import dependency relationships
- [ ] Build code relationship graph

### 5. Testing
- [ ] Test with public GitHub repos
- [ ] Test with private repos (SSH keys)
- [ ] Test with large repos (>1000 files)
- [ ] Test persona filtering in queries
- [ ] Performance benchmarks

### 6. Documentation
- [ ] Update README with Git ingestion examples
- [ ] Create developer guide for code queries
- [ ] Add troubleshooting section
- [ ] Document best practices

---

## Installation

```bash
# Install with KG dependencies (includes Git support)
cd agentic-cli
uv pip install -e ".[kg]"

# Or with pip
pip install -e ".[kg]"
```

---

## Troubleshooting

### Git Clone Fails
- **Issue**: Authentication error
- **Solution**: Use HTTPS with personal access token or SSH with keys

### gitingest Not Found
- **Issue**: `ModuleNotFoundError: No module named 'gitingest'`
- **Solution**: `pip install gitingest`

### Large Repository Timeout
- **Issue**: Cloning takes too long
- **Solution**: Use shallow clone or specific branch/tag

### Parse Errors
- **Issue**: Syntax errors in Python/Java files
- **Solution**: Files with syntax errors are skipped with warnings

---

## Architecture Diagram

```
User Command
    ↓
`agent kg ingest --source backend-api
    ↓
Resolve Data Source (commands/kg.py)
    ├── Load from ~/.dva-agentic/config.json
    ├── Extract: URL, branch, tag, name, domain, purpose
    └── Detect source_type = "git"
    ↓
Ingest Pipeline (kg/ingest.py)
    ├── Auto-detect persona = "developer"
    ├── Call parse_git_repository()
    └── Pass metadata
    ↓
Git Parser (kg/parsers.py)
    ├── Clone repo to temp dir
    ├── Checkout branch/tag
    ├── Run gitingest for overview
    ├── Scan for .py and .java files
    └── For each file:
        ↓
    Code Analyzer (kg/code_analyzer.py)
        ├── Parse with AST (Python) or Regex (Java)
        ├── Extract: classes, functions, imports
        ├── Generate quick summary
        └── Return analysis
        ↓
    Create Documents
        ├── Repository overview
        ├── File summaries
        ├── Class chunks
        └── Function chunks
    ↓
Entity Extraction (optional)
    ├── Extract entities from documents
    └── Build relationships
    ↓
Store in Neo4j
    ├── Add Code:: namespace
    ├── Add persona property
    ├── Create nodes with metadata
    └── Create relationships
    ↓
Clean Up
    └── Remove temp directory
```

---

## Summary

The Git ingestion feature provides:
- ✅ **Smart Chunking**: Functions and classes as individual documents
- ✅ **Persona Support**: Hybrid namespace + metadata approach
- ✅ **Multi-Language Support**
- **Python**: AST-based parsing (classes, functions, imports)
- **Java**: Regex-based parsing (classes, methods, interfaces)
- **SQL/DDL/DML**: Data model parsing (tables, views, procedures, constraints)
- **Extensible**: Easy to add more languages
- ✅ **Scalable**: No size limits, handles large repos
- ✅ **Clean Integration**: Works with existing KG infrastructure

This enables powerful code-aware queries like:
- "Find all authentication functions in the backend"
- "Show me classes that handle patient data"
- "What are the dependencies of the auth module?"
- "How is the login flow implemented?"
