# Weaviate KG Infrastructure

Weaviate-based knowledge graph infrastructure for DVA - single database solution for vector search and graph relationships.

## Architecture

```
weaviate/
├── docker-compose.yml          # Docker Compose configuration
├── .env                        # Environment configuration
├── .env.example               # Environment template
├── scripts/                   # Setup and test scripts
│   ├── setup_schema.py       # Schema creation
│   ├── ingest_test_data.py   # Test data ingestion
│   └── test_queries.py       # Query validation tests
└── README.md                  # This file
```

## Quick Start

### 1. Start Weaviate

```bash
cd /Users/your-user/agentic-project/myAgentPG/kg-infrastructure/weaviate
docker-compose up -d
```

### 2. Verify Health

```bash
curl http://localhost:8080/v1/.well-known/ready
```

Expected response: `{"status":"ready"}`

### 3. Install Dependencies

```bash
pip install weaviate-client python-dotenv
```

### 4. Setup Schema

```bash
cd scripts
python setup_schema.py
```

### 5. Ingest Test Data

```bash
python ingest_test_data.py
```

### 6. Run Test Queries

```bash
python test_queries.py
```

## Schema

### CodeEntity
Code entities (functions, classes, modules) from code repositories.

**Properties:**
- `name` (string): Name of the code entity
- `content` (text): Code content or documentation
- `entityType` (string): Type of entity (function, class, module, etc.)
- `filePath` (string): File path in the repository
- `language` (string): Programming language
- `domain` (string): Domain the code belongs to
- `repo` (string): Repository name
- `lineNumber` (int): Line number in the file

### Document
Business requirement documents and specifications.

**Properties:**
- `name` (string): Document name or title
- `content` (text): Document content
- `documentType` (string): Type of document (requirement, spec, etc.)
- `domain` (string): Domain the document belongs to
- `source` (string): Source of the document (Confluence, Jira, etc.)
- `url` (string): URL to the original document
- `author` (string): Document author
- `lastModified` (date): Last modification date

### Relationship
Relationships between code entities and documents.

**Properties:**
- `relationshipType` (string): Type of relationship (implements, references, related_to, etc.)
- `confidence` (number): Confidence score for the relationship
- `source` (string): Source of the relationship (LLM, vector_search, etc.)
- `metadata` (object): Additional metadata about the relationship

## Configuration

Environment variables in `.env`:

- `WEAVIATE_HOST`: Weaviate host (default: localhost)
- `WEAVIATE_PORT`: Weaviate port (default: 8080)
- `WEAVIATE_SCHEME`: HTTP scheme (default: http)
- `DEFAULT_VECTORIZER`: Default vectorizer (text2vec-transformers)
- `TRANSFORMERS_MODEL`: Transformer model name
- `QUERY_DEFAULTS_LIMIT`: Default query limit (default: 25)
- `AUTHENTICATION_ENABLED`: Enable authentication (default: false)

## Ports

- `8080`: Weaviate HTTP API
- `8081`: Weaviate gRPC API

## Volumes

- `weaviate_data`: Persistent data storage for Weaviate

## Management Commands

### Start Weaviate

```bash
docker-compose up -d
```

### Stop Weaviate

```bash
docker-compose down
```

### View Logs

```bash
docker-compose logs -f weaviate
```

### Restart Weaviate

```bash
docker-compose restart
```

### Reset Data

```bash
docker-compose down -v
docker-compose up -d
```

## Test Data

The test data includes:
- 5 code entities (functions and classes)
- 4 business documents
- Sample relationships

## Next Steps

1. **Phase 1 (Current):** Infrastructure validation
   - ✅ Set up Weaviate infrastructure
   - ✅ Create schema
   - ✅ Ingest test data
   - ✅ Run test queries

2. **Phase 2:** Integration with agentic-cli
   - Update KG config to support Weaviate provider
   - Create Weaviate client in agentic-cli
   - Update KG ingest to use Weaviate
   - Update KG linker to use Weaviate

3. **Phase 3:** Migration
   - Migrate existing Neo4j data to Weaviate
   - Update all KG commands to use Weaviate
   - Deprecate Neo4j + LightRAG infrastructure

## Comparison with Current Infrastructure

| Aspect | Current (Neo4j + LightRAG) | New (Weaviate) |
|--------|---------------------------|----------------|
| **Services** | 2 (Neo4j + LightRAG) | 1 (Weaviate) |
| **Data Storage** | Separate (graph + vector) | Unified (graph + vector) |
| **Query Language** | Cypher + HTTP API | GraphQL |
| **Complexity** | Higher (2 services) | Lower (1 service) |
| **Local Deployment** | ✅ Yes | ✅ Yes |
| **Stability** | LightRAG unstable | Stable |

## Troubleshooting

### Weaviate not starting

Check logs:
```bash
docker-compose logs weaviate
```

### Schema creation fails

Verify Weaviate is ready:
```bash
curl http://localhost:8080/v1/.well-known/ready
```

### Test queries return no results

Verify data was ingested:
```bash
python -c "import weaviate; c = weaviate.Client('http://localhost:8080'); print(c.data_object.get(class_name='CodeEntity')['totalResults'])"
```

## References

- [Weaviate Documentation](https://weaviate.io/developers/weaviate/current/)
- [Weaviate Python Client](https://weaviate.io/developers/weaviate/client-libraries/python/)
- [GraphQL API](https://weaviate.io/developers/weaviate/api/graphql/)
