# Knowledge Graph Module

This module provides knowledge graph functionality for the Agentic CLI, combining Neo4j graph database with Vertex AI for intelligent data processing.

## Architecture

```
kg/
├── __init__.py              # Module initialization
├── config.py                # Configuration management
├── neo4j_client.py          # Neo4j database client
├── ingest.py                # Data ingestion orchestration
├── parsers.py               # File format parsers
├── entity_extraction.py     # Vertex AI entity extraction
├── query.py                 # Query execution
├── search.py                # Search functionality
├── stats.py                 # Statistics
├── tool_generator.py        # ADK tool generation
└── visualize.py             # Graph visualization
```

## Components

### Configuration (`config.py`)

Manages knowledge graph configuration including:
- Neo4j connection settings
- Vertex AI credentials
- Embeddings configuration

Configuration is stored in `~/.dva-agentic/kg-config.json` and can be loaded/saved using the `KGConfig` class.

### Neo4j Client (`neo4j_client.py`)

Provides a high-level interface to Neo4j:
- Node creation and querying
- Relationship management
- Cypher query execution
- Vector similarity search
- Statistics gathering

### Data Ingestion (`ingest.py`)

Orchestrates the data ingestion pipeline:
1. Parse source files using appropriate parser
2. Extract entities and relationships using Vertex AI
3. Store in Neo4j graph database

### Parsers (`parsers.py`)

Support for multiple file formats:
- **PDF**: Extract text from PDF documents
- **Text**: Plain text and Markdown files
- **CSV**: Tabular data
- **JSON**: Structured data
- **Confluence**: Wiki pages (requires authentication)

### Entity Extraction (`entity_extraction.py`)

Uses Vertex AI Gemini model to:
- Extract entities (Person, Organization, Location, etc.)
- Identify relationships between entities
- Generate embeddings for semantic search

### Query (`query.py`)

Execute queries against the graph:
- Natural language queries (converted to Cypher)
- Direct Cypher queries
- Result formatting

### Search (`search.py`)

Search functionality:
- Semantic search using embeddings
- Exact text matching
- Relevance scoring

### Tool Generator (`tool_generator.py`)

Generate ADK tool classes with customizable operations:
- Search
- Query
- Traverse
- Custom operations

### Visualization (`visualize.py`)

Create interactive HTML visualizations using PyVis:
- Node and relationship rendering
- Color-coded by entity type
- Interactive exploration

## Usage Examples

### Basic Setup

```python
from dva_agentic_cli.kg.config import KGConfig
from dva_agentic_cli.kg.neo4j_client import Neo4jClient

# Load configuration
config = KGConfig.load()

# Connect to Neo4j
with Neo4jClient(config) as client:
    stats = client.get_stats()
    print(f"Nodes: {stats['nodes']}")
```

### Data Ingestion

```python
from dva_agentic_cli.kg.ingest import ingest_data

# Ingest a PDF
result = ingest_data(
    source="document.pdf",
    format="pdf",
    extract_entities=True,
    build_relationships=True,
)

print(f"Entities: {result['entities_count']}")
print(f"Relationships: {result['relationships_count']}")
```

### Entity Extraction

```python
from dva_agentic_cli.kg.entity_extraction import extract_entities_from_documents

documents = [
    {
        "title": "Example",
        "content": "John works at Google.",
        "metadata": {"source": "example.txt"},
    }
]

entities, relationships = extract_entities_from_documents(
    documents,
    build_relationships=True,
)
```

### Querying

```python
from dva_agentic_cli.kg.query import execute_query

# Natural language query
results = execute_query(
    "Find all people who work at Google",
    format="natural",
    limit=10,
)

# Cypher query
results = execute_query(
    "MATCH (n:Person) RETURN n LIMIT 10",
    format="cypher",
)
```

### Searching

```python
from dva_agentic_cli.kg.search import search_graph

# Semantic search
results = search_graph(
    "artificial intelligence",
    semantic=True,
    limit=10,
)

# Exact search
results = search_graph(
    "Google",
    semantic=False,
    limit=10,
)
```

### Tool Generation

```python
from dva_agentic_cli.kg.tool_generator import generate_tool

# Generate tool code
tool_code = generate_tool(
    name="knowledge_graph",
    operations=["search", "query", "traverse"],
)

# Save to file
with open("kg_tool.py", "w") as f:
    f.write(tool_code)
```

## Dependencies

Required packages (install with `pip install -e ".[kg]"`):
- `neo4j>=5.14.0` - Neo4j Python driver
- `pydantic>=2.0.0` - Configuration management
- `google-cloud-aiplatform>=1.38.0` - Vertex AI
- `PyPDF2>=3.0.0` - PDF parsing
- `pyvis>=0.3.2` - Graph visualization
- `atlassian-python-api>=3.41.0` - Confluence integration

## Configuration

The module uses two configuration files:

1. **Main config** (`~/.dva-agentic/config.json`): Vertex AI settings
2. **KG config** (`~/.dva-agentic/kg-config.json`): Neo4j and KG-specific settings

### Example KG Config

```json
{
  "provider": "neo4j",
  "neo4j_uri": "bolt://localhost:7687",
  "neo4j_username": "neo4j",
  "neo4j_password": "password",
  "embeddings_provider": "vertex-ai",
  "google_project_id": "my-project",
  "google_location": "us-central1",
  "vertex_ai_model": "text-embedding-004"
}
```

## Error Handling

All modules include proper error handling:
- Configuration validation
- Connection error handling
- Graceful fallbacks for missing dependencies
- Informative error messages

## Testing

To test the module:

```bash
# Install test dependencies
pip install -e ".[dev,kg]"

# Run tests
pytest tests/test_kg.py -v
```

## Extension Points

The module is designed to be extensible:

1. **Custom Parsers**: Add new file format parsers in `parsers.py`
2. **Custom Entity Types**: Modify entity extraction prompts
3. **Custom Relationships**: Define new relationship types
4. **Custom Tools**: Generate custom ADK tools with specific operations

## Performance Considerations

- **Batch Processing**: Process multiple documents in batches
- **Connection Pooling**: Neo4j client uses connection pooling
- **Embedding Caching**: Consider caching embeddings for frequently accessed content
- **Query Optimization**: Use appropriate indexes and query limits

## Security

- Credentials stored in user home directory (`~/.dva-agentic/`)
- File permissions set to user-only (600)
- No credentials in code or logs
- Support for environment variables

## Future Enhancements

Planned features:
- Support for more graph databases (ArangoDB, TigerGraph)
- Additional embedding providers (OpenAI, Cohere)
- Real-time data streaming
- Advanced graph algorithms
- Multi-language support
- Incremental updates
