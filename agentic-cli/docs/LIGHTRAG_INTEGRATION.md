# LightRAG Integration

This document describes the integration between Agentic CLI and LightRAG infrastructure.

## Overview

The Agentic CLI now supports both Neo4j and LightRAG as knowledge graph providers. LightRAG is a lightweight, high-performance graph-based retrieval-augmented generation system.

## Prerequisites

1. **LightRAG Infrastructure Running**
   ```bash
   cd /path/to/lightrag-infrastructure
   ./setup.sh
   # or
   make start
   ```

2. **Install Agentic CLI with KG Support**
   ```bash
   cd /path/to/agentic-cli
   uv pip install -e ".[kg]"
   ```

## Configuration

### Initialize LightRAG Provider

```bash
# Configure DVA to use LightRAG
`agent kg init --provider lightrag --lightrag-url http://localhost:8001

# With custom timeout
`agent kg init --provider lightrag --lightrag-url http://localhost:8001 --lightrag-timeout 60.0
```

### View Configuration

```bash
`agent kg config --show
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting             ┃ Value                  ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Provider            │ lightrag               │
│ LightRAG URL        │ http://localhost:8001  │
│ LightRAG Timeout    │ 30.0s                  │
│ Embeddings Provider │ vertex-ai              │
└─────────────────────┴────────────────────────┘
```

## Usage

### Ingest Data

#### Ingest a Single File

```bash
# PDF file
`agent kg ingest --path /path/to/document.pdf

# Text file
`agent kg ingest --path /path/to/document.txt

# Markdown file
`agent kg ingest --path /path/to/document.md
```

#### Ingest a Directory

```bash
# Recursively ingest all supported files
`agent kg ingest --path /path/to/documents/

# Non-recursive (only files in the directory)
`agent kg ingest --path /path/to/documents/ --no-recursive
```

#### Using Data Sources

```bash
# First, configure a data source
`agent data create --name my-docs --source-type doc --source-location /path/to/docs

# Then ingest using the source name
`agent kg ingest --source my-docs
```

### Get Statistics

```bash
`agent kg stats
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value                  ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Documents           │ 42                     │
│ Entities            │ 1,234                  │
│ Relationships       │ 3,456                  │
│ Total Characters    │ 125,678                │
└─────────────────────┴────────────────────────┘
```

## Supported File Types

When ingesting directories, the following file types are automatically processed:

- `.txt` - Plain text files
- `.md` - Markdown files
- `.pdf` - PDF documents
- `.json` - JSON files
- `.csv` - CSV files

## Architecture

### Components

1. **LightRAG Client** (`src/dva_agentic_cli/kg/lightrag_client.py`)
   - HTTP client wrapper for LightRAG API
   - Methods: `insert()`, `insert_file()`, `query()`, `search()`, `get_stats()`
   - Health checking and connection validation

2. **Configuration** (`src/dva_agentic_cli/kg/config.py`)
   - Extended `KGConfig` with LightRAG settings
   - Fields: `lightrag_url`, `lightrag_timeout`
   - Method: `is_lightrag_configured()`

3. **CLI Commands** (`src/dva_agentic_cli/commands/kg.py`)
   - Provider-aware routing (Neo4j vs LightRAG)
   - Automatic validation and error handling
   - Unified interface for both providers

### Data Flow

```
User Command
    ↓
`agent kg ingest --path /docs
    ↓
Load KGConfig (provider=lightrag)
    ↓
Validate LightRAG connection
    ↓
LightRAGClient.insert_file()
    ↓
HTTP POST → LightRAG API
    ↓
Display results
```

## Switching Between Providers

You can easily switch between Neo4j and LightRAG:

```bash
# Switch to LightRAG
`agent kg init --provider lightrag --lightrag-url http://localhost:8001

# Switch to Neo4j
`agent kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password

# Check current provider
`agent kg config --show
```

## Error Handling

The CLI provides clear error messages:

```bash
# If LightRAG is not running
$ agent kg ingest --path /docs
✗ LightRAG is not available: Cannot connect to LightRAG at http://localhost:8001
Make sure LightRAG infrastructure is running.

# If httpx is not installed
$ agent kg ingest --path /docs
✗ Error: httpx is required for LightRAG support. Install it with: pip install httpx
```

## Advanced Usage

### Custom Metadata

When ingesting files, metadata is automatically added:

```python
{
    "filename": "document.pdf",
    "filepath": "/absolute/path/to/document.pdf",
    "file_type": ".pdf"
}
```

### Batch Processing

For large directories, files are processed one at a time with progress updates:

```bash
$ agent kg ingest --path /large-docs/
  Ingested: file1.txt
  Ingested: file2.pdf
  Ingested: file3.md
  ⚠ Skipped file4.bin: Unsupported format
✓ Successfully ingested directory
  Files: 3
  Total characters: 45,678
```

## Comparison: Neo4j vs LightRAG

| Feature | Neo4j | LightRAG |
|---------|-------|----------|
| Entity Extraction | ✅ LLM-based | ✅ Built-in |
| Relationship Building | ✅ Explicit | ✅ Automatic |
| Semantic Search | ✅ Vector embeddings | ✅ Built-in |
| Query Language | Cypher | Natural language |
| Setup Complexity | Medium (Docker) | Low (Docker) |
| Performance | High | Very High |
| Scalability | Excellent | Good |

## Troubleshooting

### LightRAG Not Available

```bash
# Check if LightRAG is running
curl http://localhost:8001/health

# Start LightRAG infrastructure
cd /path/to/lightrag-infrastructure
make start

# Check logs
make logs
```

### Connection Timeout

```bash
# Increase timeout
`agent kg init --provider lightrag --lightrag-url http://localhost:8001 --lightrag-timeout 60.0
```

### Missing Dependencies

```bash
# Reinstall with KG dependencies
uv pip install -e ".[kg]"

# Verify httpx is installed
python -c "import httpx; print(httpx.__version__)"
```

## API Reference

### LightRAGClient Methods

- `health_check()` - Check service health
- `insert(text, metadata)` - Insert raw text
- `insert_file(file_path, metadata)` - Insert file contents
- `query(query, mode, top_k)` - Query with mode (naive, local, global, hybrid)
- `search(query, top_k)` - Semantic search
- `get_stats()` - Get statistics
- `clear()` - Clear all data

### Configuration Fields

- `provider` - "neo4j" or "lightrag"
- `lightrag_url` - LightRAG API base URL (default: http://localhost:8001)
- `lightrag_timeout` - Request timeout in seconds (default: 30.0)

## Examples

### Complete Workflow

```bash
# 1. Start LightRAG infrastructure
cd lightrag-infrastructure
make start

# 2. Configure Agentic CLI
`agent kg init --provider lightrag

# 3. Configure data source
`agent data create --name research-papers \
  --source-type doc \
  --source-location /path/to/papers \
  --description "Research papers collection" \
  --tags "research,papers,ml"

# 4. Ingest data
`agent kg ingest --source research-papers

# 5. View statistics
`agent kg stats

# 6. Query (future feature)
# agent kg query "What are the main findings?"
```

## Future Enhancements

- [ ] Query support for LightRAG
- [ ] Search command integration
- [ ] Visualization support
- [ ] Batch ingestion API
- [ ] Progress bars for large ingestions
- [ ] Async ingestion support
- [ ] Custom metadata schemas

## References

- [LightRAG Infrastructure](../lightrag-infrastructure/README.md)
- [DVA Data Commands](../README.md#data-source-management)
- [Knowledge Graph Commands](../README.md#knowledge-graph-commands)
