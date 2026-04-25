# Knowledge Graph Integration

The DVA Agentic CLI includes a powerful knowledge graph system that combines Neo4j graph database with Vertex AI for intelligent entity extraction and semantic search.

## Features

- **Multi-format Data Ingestion**: PDF, text, CSV, JSON, and Confluence
- **AI-Powered Entity Extraction**: Uses Vertex AI to automatically extract entities and relationships
- **Semantic Search**: Vector embeddings for intelligent search
- **Graph Queries**: Natural language and Cypher query support
- **Interactive Visualization**: HTML-based graph visualization
- **ADK Tool Generation**: Auto-generate tools for agent integration

## Quick Start

### 1. Install Dependencies

```bash
# Install with knowledge graph support
pip install -e ".[kg]"
```

### 2. Configure Neo4j

First, ensure you have Neo4j running. You can use Docker:

```bash
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:latest
```

Then configure the CLI:

```bash
dva kg init \
    --provider neo4j \
    --uri bolt://localhost:7687 \
    --username neo4j \
    --password password \
    --embeddings vertex-ai
```

### 3. Configure Vertex AI (if not already done)

```bash
# Automatically runs gcloud auth application-default login
dva init vertex-ai \
    --project-id YOUR_PROJECT_ID \
    --location us-central1
```

### 4. Ingest Data

```bash
# Ingest a PDF document (direct path)
dva kg ingest --path document.pdf

# Ingest using a configured data source
dva kg ingest --source my-dataset

# Ingest a directory of files
dva kg ingest --path ./data --format text

# Ingest CSV data
dva kg ingest --path data.csv --extract-entities --build-relationships

# Ingest JSON
dva kg ingest --path config.json
```

## Commands

### Configuration

#### `dva kg init`

Initialize knowledge graph configuration.

```bash
dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password
```

Options:
- `--provider`: Graph database provider (neo4j, networkx)
- `--uri`: Neo4j connection URI
- `--username`: Neo4j username
- `--password`: Neo4j password
- `--embeddings`: Embeddings provider (vertex-ai, openai, none)

#### `dva kg config`

Manage configuration.

```bash
# Show current configuration
dva kg config --show

# Reset configuration
dva kg config --reset
```

### Data Ingestion

#### `dva kg ingest`

Ingest data from various sources. You can specify sources in two ways:

1. **Direct path/URL**: Use `--path` to specify a direct file or directory path
2. **Data source name**: Use `--source` to reference a configured data source (created with `dva data create`)

```bash
# Direct path ingestion
dva kg ingest --path document.pdf

# Data source ingestion (requires dva data create first)
dva kg ingest --source my-dataset

# Specify format explicitly
dva kg ingest --path data.txt --format text

# Disable entity extraction
dva kg ingest --path data.csv --no-extract-entities

# Disable relationship building
dva kg ingest --path data.json --no-build-relationships
```

**Data Source Integration**: Before using `--source`, configure data sources with:

```bash
# Configure a local document source
dva data create --name my-docs --source-type doc --source-location /path/to/docs

# Configure a GCS source
dva data create --name gcs-data --source-type doc --source-location gs://bucket/path

# Configure a Confluence source
dva data create --name wiki --source-type confluence --source-location https://company.atlassian.net

# Then ingest using the configured source
dva kg ingest --source my-docs
```

Supported formats:
- **PDF**: `.pdf` files
- **Text**: `.txt`, `.md` files
- **CSV**: `.csv` files
- **JSON**: `.json` files
- **Confluence**: Confluence URLs (requires authentication)

### Querying

#### `dva kg query`

Query the knowledge graph.

```bash
# Natural language query
dva kg query "Find all people who work at Google"

# Cypher query
dva kg query "MATCH (n:Person) RETURN n LIMIT 10" --format cypher

# Limit results
dva kg query "Show all organizations" --limit 5
```

#### `dva kg search`

Search the knowledge graph.

```bash
# Semantic search (uses embeddings)
dva kg search "artificial intelligence" --semantic

# Exact text search
dva kg search "Google" --exact

# Limit results
dva kg search "machine learning" --limit 20
```

### Statistics

#### `dva kg stats`

Display knowledge graph statistics.

```bash
dva kg stats
```

Shows:
- Total nodes
- Total relationships
- Node types count
- Relationship types count
- Top connected entities

### Visualization

#### `dva kg visualize`

Generate interactive HTML visualization.

```bash
# Basic visualization
dva kg visualize

# Custom output file
dva kg visualize --output my-graph.html

# Filter by node type
dva kg visualize --filter Person

# Control traversal depth
dva kg visualize --depth 3
```

### Tool Generation

#### `dva kg tool`

Generate ADK tool class for knowledge graph operations.

```bash
# Generate tool with default operations
dva kg tool --name company_knowledge

# Specify operations
dva kg tool --name custom_kg --operations search,query,traverse

# Save to file
dva kg tool --name my_tool --output tools/kg_tool.py
```

Available operations:
- `search`: Semantic and exact search
- `query`: Natural language and Cypher queries
- `traverse`: Graph traversal from a node

## Entity Extraction

The system uses Vertex AI's Gemini model to automatically extract:

### Entity Types
- **Person**: People mentioned in documents
- **Organization**: Companies, institutions
- **Location**: Places, addresses
- **Concept**: Ideas, technologies, methodologies
- **Product**: Products, services
- **Event**: Events, meetings, conferences
- **Document**: Source documents

### Relationship Types
- **WORKS_FOR**: Person works for Organization
- **LOCATED_IN**: Entity located in Location
- **RELATED_TO**: General relationship
- **PART_OF**: Component relationship
- **MENTIONS**: Document mentions Entity

## Semantic Search

The system supports semantic search using Vertex AI embeddings:

1. **Text Embedding**: Documents and entities are embedded using `text-embedding-004`
2. **Vector Index**: Neo4j vector index for similarity search
3. **Cosine Similarity**: Find semantically similar content

### Setup Vector Index

The vector index is created automatically, but you can verify:

```cypher
SHOW INDEXES
```

## Integration with ADK Agents

### Generate a Tool

```bash
dva kg tool --name knowledge_graph --output tools/kg_tool.py
```

### Use in Agent

```python
from tools.kg_tool import KnowledgeGraphTool

class MyAgent:
    def __init__(self):
        self.kg_tool = KnowledgeGraphTool()
    
    def search_knowledge(self, query: str):
        results = self.kg_tool.search(query, semantic=True, limit=5)
        return results
    
    def query_graph(self, query: str):
        results = self.kg_tool.query(query, format="natural")
        return results
```

## Advanced Usage

### Custom Cypher Queries

```bash
# Find all relationships
dva kg query "MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name LIMIT 10" --format cypher

# Find nodes by property
dva kg query "MATCH (n:Person) WHERE n.name CONTAINS 'John' RETURN n" --format cypher

# Complex traversal
dva kg query "MATCH path = (start:Person)-[*1..3]-(end:Organization) RETURN path" --format cypher
```

### Batch Ingestion

```python
from pathlib import Path
from dva_agentic_cli.kg.ingest import ingest_data

# Ingest all PDFs in a directory
for pdf_file in Path("./documents").glob("*.pdf"):
    result = ingest_data(
        source=str(pdf_file),
        format="pdf",
        extract_entities=True,
        build_relationships=True,
    )
    print(f"Ingested {pdf_file.name}: {result['entities_count']} entities")
```

### Custom Entity Extraction

```python
from dva_agentic_cli.kg.entity_extraction import extract_entities_from_documents

documents = [
    {
        "title": "My Document",
        "content": "John works at Google in Mountain View.",
        "metadata": {"source": "example.txt"},
    }
]

entities, relationships = extract_entities_from_documents(
    documents,
    build_relationships=True,
)
```

## Configuration File

Configuration is stored in `~/.dva-agentic/kg-config.json`:

```json
{
  "provider": "neo4j",
  "neo4j_uri": "bolt://localhost:7687",
  "neo4j_username": "neo4j",
  "neo4j_password": "password",
  "embeddings_provider": "vertex-ai",
  "google_project_id": "your-project-id",
  "google_location": "us-central1",
  "vertex_ai_model": "text-embedding-004"
}
```

## Troubleshooting

### Neo4j Connection Issues

```bash
# Test connection
dva kg stats

# Check Neo4j is running
docker ps | grep neo4j

# View Neo4j logs
docker logs neo4j
```

### Vertex AI Authentication

```bash
# Authenticate with gcloud
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Verify configuration
dva init show
```

### Missing Dependencies

```bash
# Install all KG dependencies
pip install -e ".[kg]"

# Install specific packages
pip install neo4j PyPDF2 pyvis google-cloud-aiplatform
```

### Empty Search Results

1. Check if data is ingested: `dva kg stats`
2. Verify Neo4j connection: `dva kg config --show`
3. Try exact search instead of semantic: `dva kg search "query" --exact`

## Performance Tips

1. **Batch Ingestion**: Ingest multiple files at once for better performance
2. **Vector Index**: Ensure vector index is created for semantic search
3. **Query Limits**: Use appropriate limits to avoid overwhelming results
4. **Depth Control**: Limit traversal depth in visualizations

## Best Practices

1. **Consistent Entity Types**: Use consistent entity type names
2. **Meaningful Relationships**: Create descriptive relationship types
3. **Metadata**: Include rich metadata in documents
4. **Regular Backups**: Backup Neo4j database regularly
5. **Index Management**: Monitor and maintain indexes

## Examples

### Example 1: Company Knowledge Base

```bash
# Ingest company documents
dva kg ingest ./company-docs --format text --extract-entities

# Search for information
dva kg search "product roadmap" --semantic

# Query organizational structure
dva kg query "Find all people and their departments"

# Visualize
dva kg visualize --output company-graph.html
```

### Example 2: Research Papers

```bash
# Ingest research papers
dva kg ingest ./papers/*.pdf

# Find related concepts
dva kg search "neural networks" --semantic --limit 10

# Explore citations
dva kg query "MATCH (p:Paper)-[:CITES]->(cited:Paper) RETURN p.name, cited.name"
```

### Example 3: Customer Data

```bash
# Ingest customer data
dva kg ingest customers.csv --extract-entities --build-relationships

# Find customer segments
dva kg query "Find all customers in California"

# Generate tool for CRM integration
dva kg tool --name customer_knowledge --output tools/customer_kg.py
```

## Next Steps

- Explore [Neo4j Cypher documentation](https://neo4j.com/docs/cypher-manual/)
- Learn about [Vertex AI embeddings](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)
- Check out [ADK agent integration](./ADK_INTEGRATION.md)
