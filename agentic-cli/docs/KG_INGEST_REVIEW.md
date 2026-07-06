# Knowledge Graph Ingest Processing Logic Review

## Overview

The KG ingest system processes various data sources (PDFs, text files, Git repos, Confluence, directories) and ingests them into either Neo4j or LightRAG knowledge graphs. The system supports entity extraction, relationship building, and persona-based tagging.

## Architecture

### Entry Point: `keel kg ingest` Command
**Location**: `src/agentic_cli/commands/kg.py:374-620`

```
`agent kg ingest [--source NAME | --path PATH] [OPTIONS]
```

### Processing Flow

```
1. Command Entry (kg.py)
   ├─ Validate Neo4j/LightRAG connection
   ├─ Resolve data source (from name or direct path)
   └─ Route to provider-specific ingestion

2. Provider Routing
   ├─ Neo4j Path (ingest.py)
   │  ├─ Parse documents (parsers.py)
   │  ├─ Extract entities (entity_extraction.py)
   │  ├─ Build relationships
   │  └─ Store in Neo4j (neo4j_client.py)
   │
   └─ LightRAG Path (lightrag_client.py)
      ├─ Parse documents (parsers.py)
      └─ Insert via LightRAG API

3. Document Parsing (parsers.py)
   ├─ Format detection (auto or explicit)
   ├─ Parser selection (PDF, text, CSV, JSON, Git, Confluence, directory)
   └─ Document list generation

4. Entity Extraction (Neo4j only)
   ├─ Vertex AI Gemini model
   ├─ Entity identification (Person, Organization, Location, Concept, etc.)
   └─ Relationship extraction

5. Storage
   ├─ Neo4j: Nodes + Relationships with persona tags
   └─ LightRAG: Documents with metadata
```

## Key Components

### 1. Command Handler (`kg.py:374-620`)

**Responsibilities:**
- Parameter validation
- Data source resolution
- Provider routing
- Progress feedback
- Error handling

**Key Features:**
- **Dual Source Support**: `--source` (configured) or `--path` (direct)
- **Format Auto-Detection**: Infers format from extension/URL
- **Provider Routing**: Neo4j vs LightRAG
- **Git Support**: Extended timeout (600s) for large repos
- **Batch Processing**: 50 docs at a time with progress updates

**Parameters:**
```python
--source NAME              # Data source from 'agent data create'
--path PATH                # Direct file/directory/URL path
--format FORMAT            # pdf, text, csv, json, confluence, git, directory
--extract-entities         # Use LLM for entity extraction (default: True)
--no-extract-entities      # Skip entity extraction
--build-relationships      # Build entity relationships (default: True)
--no-build-relationships   # Skip relationship building
--recursive                # Process subdirectories (default: True)
--no-recursive             # Don't recurse directories
--skip-validation          # Skip connection check (hidden)
```

### 2. Data Source Resolution (`kg.py:32-88`)

**Function**: `resolve_data_source(source_name: str)`

**Purpose**: Convert data source name to location, type, and metadata

**Returns**: `(location, source_type, metadata)`

**Metadata Extraction:**
- **All sources**: name, description, tags
- **Git sources**: domain, purpose, branch, tag

**Example:**
```python
# Input: --source my-backend-repo
# Output: 
#   location = "https://github.com/org/backend.git"
#   source_type = "git"
#   metadata = {
#       "name": "my-backend-repo",
#       "domain": "backend, api",
#       "purpose": "Core API services",
#       "branch": "main",
#       "tag": None
#   }
```

### 3. Core Ingest Logic (`ingest.py:56-192`)

**Function**: `ingest_data(source, format, persona, metadata, extract_entities, build_relationships, recursive)`

**Processing Steps:**

1. **Format Detection** (if not specified)
   - Directory check
   - Git URL patterns (github.com, gitlab.com, .git)
   - File extensions (.pdf, .txt, .csv, .json)
   - URL patterns (confluence, wiki)
   - Default: text

2. **Persona Auto-Detection**
   - Git repos → "developer"
   - Other sources → "business"

3. **Document Parsing**
   - Calls appropriate parser based on format
   - Returns list of document dicts

4. **Entity Extraction** (if enabled)
   - Uses Vertex AI Gemini 2.5 Flash Lite
   - Extracts entities and relationships
   - Adds persona tags

5. **Neo4j Storage**
   - Creates nodes with persona metadata
   - Adds "Code::" namespace for developer persona
   - Creates relationships
   - Returns statistics

### 4. Document Parsers (`parsers.py`)

#### PDF Parser (`parse_pdf`)
- Uses PyPDF2
- One document per page
- Metadata: source, page, total_pages, format

#### Text Parser (`parse_text`)
- Reads .txt and .md files
- Single document
- Metadata: source, format, size

#### CSV Parser (`parse_csv`)
- One document per row
- Converts row to JSON string
- Metadata: source, row_number, format, columns

#### JSON Parser (`parse_json`)
- Reads JSON array or object
- One document per array item or single doc for object
- Metadata: source, format, item_index

#### Confluence Parser (`parse_confluence`)
- Requires configuration (URL, username, token)
- Supports page URLs and space URLs
- Extracts HTML content
- Metadata: source, title, space, page_id, version

#### Directory Parser (`parse_directory`)
- Recursively scans for supported files
- Supported: .pdf, .txt, .md, .csv, .json
- Calls appropriate parser for each file
- Continues on errors (logs and skips)

#### Git Parser (`parse_git_repository`)
**Most Complex Parser**

**Steps:**
1. Clone repo to temp directory
2. Checkout branch/tag if specified
3. Generate repository digest using gitingest
4. Analyze source files (.py, .java, .sql, .ddl, .dml)
5. Extract code structure (functions, classes, imports)
6. Create documents with developer persona
7. Clean up temp directory

**Documents Created:**
- Repository overview (from gitingest)
- File-level documents (one per source file)
- Function/class documents (code chunks)

**Metadata:**
- source_type, persona, repo_url, repo_name
- domain, purpose, branch, tag
- commit_hash, commit_date
- file_path, language, doc_type
- function/class names, line numbers

### 5. Entity Extraction (`entity_extraction.py`)

**Model**: Vertex AI Gemini 2.5 Flash Lite

**Entity Types:**
- Person
- Organization
- Location
- Concept
- Product
- Event
- Technology
- Process

**Relationship Types:**
- WORKS_FOR
- LOCATED_IN
- RELATED_TO
- PART_OF
- USES
- CREATES
- MANAGES

**Process:**
1. Initialize Vertex AI with project/location
2. For each document:
   - Extract entities with LLM
   - Parse JSON response
   - Generate unique IDs
   - Extract relationships (if enabled)
3. Return entities and relationships

**Prompt Structure:**
```
Extract entities from this text:
[CONTENT]

Return JSON array with:
- type: entity type
- name: entity name
- description: brief description
```

### 6. Neo4j Storage (`neo4j_client.py`)

**Node Creation:**
- Label: Entity type (with "Code::" prefix for developer persona)
- Properties: id, name, content, persona, metadata (JSON)

**Relationship Creation:**
- From/to node IDs
- Relationship type
- Properties (optional)

**Persona Tagging:**
- Added to node properties
- Used for filtering queries
- "developer" for code, "business" for docs

### 7. LightRAG Integration (`lightrag_client.py`)

**Simpler Flow:**
- No entity extraction
- Direct document insertion
- Metadata preserved
- Batch processing for Git repos

**Git Handling:**
- 50 docs per batch
- Progress feedback every batch
- Persona added to metadata
- Extended timeout (600s)

## Data Flow Examples

### Example 1: PDF Ingestion (Neo4j)

```bash
`agent kg ingest --path document.pdf
```

**Flow:**
1. Validate Neo4j connection
2. Detect format: "pdf"
3. Parse PDF → 10 pages → 10 documents
4. Extract entities → 25 entities, 15 relationships
5. Store in Neo4j with persona="business"
6. Return stats: 25 entities, 15 relationships

### Example 2: Git Repository (LightRAG)

```bash
`agent kg ingest --source backend-repo
```

**Flow:**
1. Validate LightRAG connection
2. Resolve source → git URL, branch=main
3. Clone repository
4. Generate digest with gitingest
5. Analyze 150 Python files
6. Create 450 documents (overview + files + functions)
7. Insert in batches of 50 with progress
8. Return stats: 450 documents, 125,000 chars

### Example 3: Directory Ingestion (Neo4j)

```bash
`agent kg ingest --path /docs --recursive
```

**Flow:**
1. Validate Neo4j connection
2. Detect format: "directory"
3. Scan recursively → find 30 files (.pdf, .txt, .md)
4. Parse each file → 45 documents total
5. Extract entities → 80 entities, 50 relationships
6. Store in Neo4j with persona="business"
7. Return stats: 80 entities, 50 relationships

## Issues & Observations

### 1. **Error Handling**
- ✅ Good: Connection validation before processing
- ✅ Good: Graceful file-level errors in directory parsing
- ⚠️ Issue: Git parsing failures abort entire ingestion
- ⚠️ Issue: Entity extraction failures not caught per-document

### 2. **Performance**
- ✅ Good: Batch processing for Git repos
- ✅ Good: Progress feedback for long operations
- ⚠️ Issue: No parallel processing for multiple files
- ⚠️ Issue: Entity extraction is sequential (slow for large datasets)
- ⚠️ Issue: No caching of parsed documents

### 3. **Memory Management**
- ⚠️ Issue: All documents loaded into memory before processing
- ⚠️ Issue: Large Git repos can cause OOM
- ⚠️ Issue: No streaming for large files

### 4. **Entity Extraction**
- ✅ Good: Uses latest Gemini model
- ✅ Good: Structured JSON output
- ⚠️ Issue: No retry logic for LLM failures
- ⚠️ Issue: No rate limiting (could hit quotas)
- ⚠️ Issue: Fixed prompt (not customizable)
- ⚠️ Issue: No entity deduplication across documents

### 5. **Git Repository Handling**
- ✅ Good: Supports branch/tag checkout
- ✅ Good: Uses gitingest for overview
- ✅ Good: Code structure analysis
- ⚠️ Issue: Clones entire repo (no shallow clone)
- ⚠️ Issue: No cleanup on failure
- ⚠️ Issue: Limited to Python, Java, SQL (hardcoded)
- ⚠️ Issue: No support for binary files

### 6. **Metadata Handling**
- ✅ Good: Rich metadata for Git sources
- ✅ Good: Persona tagging
- ⚠️ Issue: Metadata structure inconsistent across formats
- ⚠️ Issue: No validation of metadata schema

### 7. **Format Detection**
- ✅ Good: Auto-detection from extensions
- ⚠️ Issue: Limited URL pattern matching
- ⚠️ Issue: No MIME type checking
- ⚠️ Issue: Ambiguous formats (e.g., .txt could be code)

### 8. **Relationship Building**
- ⚠️ Issue: Only within-document relationships
- ⚠️ Issue: No cross-document entity linking
- ⚠️ Issue: No entity resolution/deduplication

## Recommendations

### High Priority

1. **Add Streaming Support**
   - Process documents one at a time
   - Reduce memory footprint
   - Enable progress tracking

2. **Improve Error Handling**
   - Catch per-document errors
   - Continue processing on failures
   - Collect error summary

3. **Add Parallel Processing**
   - Process multiple files concurrently
   - Use thread pool for I/O operations
   - Configurable concurrency level

4. **Entity Deduplication**
   - Hash-based entity matching
   - Merge duplicate entities
   - Link across documents

5. **Add Retry Logic**
   - Exponential backoff for LLM calls
   - Rate limiting
   - Circuit breaker pattern

### Medium Priority

6. **Optimize Git Ingestion**
   - Shallow clone option
   - Configurable file extensions
   - Better cleanup on errors

7. **Improve Progress Feedback**
   - Real-time progress bars
   - ETA calculations
   - Detailed statistics

8. **Add Validation**
   - Schema validation for metadata
   - Content validation
   - Size limits

9. **Caching Layer**
   - Cache parsed documents
   - Cache entity extractions
   - Invalidation strategy

### Low Priority

10. **Customizable Prompts**
    - User-defined entity types
    - Custom relationship types
    - Prompt templates

11. **Binary File Support**
    - Images (OCR)
    - Office documents
    - Archives

12. **Advanced Format Detection**
    - MIME type checking
    - Content-based detection
    - Language detection for code

## Code Quality

### Strengths
- ✅ Clear separation of concerns
- ✅ Type hints throughout
- ✅ Good documentation
- ✅ Modular parser design
- ✅ Rich console output

### Weaknesses
- ⚠️ Limited test coverage
- ⚠️ No logging (uses print statements)
- ⚠️ Hardcoded values (batch sizes, timeouts)
- ⚠️ No configuration for extraction parameters
- ⚠️ Mixed sync/async patterns

## Summary

The KG ingest system is **well-structured** with clear separation between parsing, extraction, and storage. The **dual provider support** (Neo4j/LightRAG) is elegant, and the **Git repository handling** is sophisticated.

**Main strengths:**
- Comprehensive format support
- Rich metadata tracking
- Persona-based tagging
- Good user feedback

**Main weaknesses:**
- Performance bottlenecks (sequential processing, no streaming)
- Error handling gaps
- Memory management issues
- Limited customization

**Recommended focus areas:**
1. Streaming and parallel processing
2. Better error handling and recovery
3. Entity deduplication
4. Performance optimization for large datasets
