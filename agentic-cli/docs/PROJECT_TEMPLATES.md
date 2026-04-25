# Project Templates

The DVA Agentic CLI provides an embedded template system for creating agent projects with different frameworks and use cases.

## Quick Start

```bash
# Create a basic agent project
dva project create my-agent

# Create a RAG agent
dva project create my-rag --use-case rag

# Create a Knowledge Graph agent
dva project create my-kg --use-case knowledge-graph

# Create with additional tools
dva project create my-bot --use-case chatbot --tools web_search,api_caller
```

## Frameworks

| Framework | Description | Status |
|-----------|-------------|--------|
| `adk` | Google ADK (Agent Development Kit) | ✓ Available |
| `langgraph` | LangGraph | ✓ Available |

## Use Cases

| Use Case | Description | Default Tools |
|----------|-------------|---------------|
| `basic` | Simple agent with basic tools | calculator, text_analyzer, file_reader |
| `rag` | RAG with document retrieval | document_loader, embeddings, vector_search |
| `knowledge-graph` | Neo4j knowledge graph integration | kg_query, kg_ingest, entity_extractor |
| `multi-agent` | Orchestrated multi-agent system | agent_router, memory, text_analyzer |
| `chatbot` | Conversational agent with memory | memory, text_analyzer, web_search |
| `data-pipeline` | ETL and data processing | csv_processor, json_processor, database_tool |
| `code-assistant` | Code generation and review | code_executor, code_analyzer, git_tool |

## Available Tools

### Basic Tools
- `calculator` - Mathematical calculations
- `text_analyzer` - Text statistics and analysis
- `file_reader` - Read file contents
- `file_writer` - Write to files

### Web Tools
- `web_search` - Search the web
- `web_scraper` - Scrape web pages
- `api_caller` - Make API calls

### RAG Tools
- `vector_search` - Semantic vector search
- `document_loader` - Load and parse documents
- `embeddings` - Generate text embeddings

### Knowledge Graph Tools
- `kg_query` - Query Neo4j knowledge graph
- `kg_ingest` - Ingest data into knowledge graph
- `entity_extractor` - Extract entities from text

### Code Tools
- `code_executor` - Execute code safely
- `code_analyzer` - Analyze code structure
- `git_tool` - Git operations

### Data Tools
- `csv_processor` - Process CSV files
- `json_processor` - Process JSON files
- `database_tool` - Database operations

### Communication Tools
- `memory` - Conversation memory management
- `agent_router` - Route between multiple agents

## Command Options

```bash
dva project create <name> [OPTIONS]

Arguments:
  name                    Project name (required)

Options:
  --path PATH             Directory to create project in (default: current)
  --framework, -f TEXT    Agent framework: adk, langgraph (default: adk)
  --use-case, -u TEXT     Use case (default: basic)
  --tools, -t TEXT        Additional tools (comma-separated)
  --tests/--no-tests      Include test suite (default: --tests)
  --examples/--no-examples Include examples (default: --examples)
  --docker/--no-docker    Include Docker files (default: --no-docker)
  --force                 Overwrite existing project
```

## Examples

### Basic Agent
```bash
dva project create my-agent
```

Creates a simple agent with calculator, text analyzer, and file reader tools.

### RAG Agent
```bash
dva project create my-rag --use-case rag
```

Creates an agent with document loading, embeddings, and vector search capabilities.

### Knowledge Graph Agent
```bash
dva project create my-kg --use-case knowledge-graph
```

Creates an agent integrated with Neo4j for knowledge graph operations.

### Multi-Agent System
```bash
dva project create my-system --use-case multi-agent
```

Creates an orchestrator agent that can route to specialized sub-agents.

### Chatbot with Extra Tools
```bash
dva project create my-bot --use-case chatbot --tools api_caller,file_reader
```

Creates a chatbot with memory, web search, and additional API and file tools.

### Production-Ready with Docker
```bash
dva project create my-prod --use-case rag --docker
```

Creates a RAG agent with Docker and docker-compose files included.

## Generated Project Structure

```
my-project/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── config.py         # Pydantic settings
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py       # BaseAgent class
│   │   └── <agent>.py    # Use case specific agent
│   ├── tools/
│   │   ├── __init__.py
│   │   └── <tool>.py     # Tool implementations
│   └── workflows/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_agent.py
├── examples/
│   └── basic_example.py
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
└── README.md
```

## Configuration

Projects are configured via environment variables. Copy `.env.example` to `.env` and update:

```bash
# Agent Configuration
AGENT_PROVIDER=vertex_ai

# Google Cloud
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Vertex AI Model
VERTEX_AI_MODEL=gemini-2.0-flash-001

# Neo4j (for knowledge-graph use case)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## Pre-configured Google Cloud

If you've run `dva init vertex-ai`, your Google Cloud settings will automatically be applied to new projects:

```bash
# Configure once
dva init vertex-ai --project-id my-gcp-project

# All new projects get the config
dva project create my-agent  # .env auto-populated
```

## Listing Available Options

```bash
# Show all frameworks, use cases, and tools
dva project list-templates
```

## Extending Tools

To add custom tools to a generated project:

1. Create a new file in `src/tools/`
2. Implement your tool function or class
3. Import and use in your agent

Example custom tool:
```python
# src/tools/my_custom_tool.py
def my_tool(input: str) -> str:
    """My custom tool."""
    return f"Processed: {input}"
```
