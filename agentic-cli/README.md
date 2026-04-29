# Agentic CLI

A command-line interface for agentic workflows using the ADK agent platform.

## Features

- 🚀 Built with [Typer](https://typer.tiangolo.com/) for intuitive CLI interactions
- 🤖 Integrates with ADK agent platform for agentic capabilities
- 🧠 **Knowledge Graph**: Neo4j + LightRAG + Vertex AI for intelligent data retrieval
- 📦 Uses [uv](https://github.com/astral-sh/uv) for fast Python package management
- 🎨 Rich terminal output with colors and formatting
- 🧩 Modular architecture supporting multiple sub-commands
- ✅ Comprehensive testing with pytest

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

## Installation

### Configurable CLI Name

The CLI name is configurable via the `AGENT_CLI_NAME` environment variable. By default it's `dva`, but you can customize it during installation:

```bash
# Install with default name (dva)
pip install ./agentic-cli

# Install with custom name
AGENT_CLI_NAME=raj pip install ./agentic-cli
AGENT_CLI_NAME=alice pip install ./agentic-cli
```

All commands, help text, and version output will automatically reflect your chosen name.

### Development Installation

```bash
# Clone or navigate to the project
cd agentic-cli

# Create a virtual environment with uv
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install the package in development mode
make install-dev

# Or with custom CLI name
AGENT_CLI_NAME=myagent make install-dev
```

### Quick Installation

```bash
# Run the automated setup script
./setup.sh

# Or use make
make install

# Or with custom CLI name
AGENT_CLI_NAME=myagent ./setup.sh
```

### Installing with Optional Features

Optional dependencies are available for different features:

```bash
# Install with ADK dependencies
uv pip install -e ".[dev,adk]"

# Install with Knowledge Graph support (Neo4j + Vertex AI)
uv pip install -e ".[dev,kg]"

# Install with all features
uv pip install -e ".[dev,adk,kg]"

# Or with custom CLI name
AGENT_CLI_NAME=custom uv pip install -e ".[dev,kg]"
```

## Usage

### Help Documentation & Dynamic Naming

The CLI automatically adapts all help text and output to match your configured CLI name:

```bash
# Get help (shows your configured CLI name)
`agent --help

# Get command-specific help
`agent project --help
`agent kg --help
`agent data --help

# Show version (displays your configured CLI name)
`agent --version

# All help output is dynamic - no hardcoded command names
# If installed as 'raj', all examples show 'raj' instead of 'agent'
raj --help
raj project --help
```

### Basic Commands

```bash
# Show version
`agent --version

# Show help
`agent --help

# Example hello command
`agent hello
`agent hello "Your Name"
```

### Available Commands

#### Global Options
- `--version, -v`: Display version information
- `--help`: Show help message

All commands below use `dva` as the CLI name. If you installed with a custom name (e.g., `AGENT_CLI_NAME=raj`), replace `dva` with your chosen name in all examples.

#### Initialization & Authentication
- `dva init vertex-ai`: Configure Vertex AI settings
- `dva init show`: Show current configuration
- `dva init reset`: Reset configuration to defaults

#### Project Management
- `dva project create <name>`: Create a new agentic project from template
- `dva project list-templates`: List available project templates
- `dva project info [PATH]`: Show information about a project
- `dva project list`: List all registered projects
- `dva project validate [PATH]`: Validate project configuration

#### Knowledge Graph
- `dva kg check`: Check prerequisites and Neo4j availability
- `dva kg init`: Initialize knowledge graph configuration (supports Neo4j and LightRAG)
- `dva kg config`: Manage knowledge graph settings
- `dva kg ingest`: Ingest data from PDF, text, CSV, JSON, Confluence (✅ both providers)
- `dva kg query <query>`: Query the knowledge graph (✅ both providers)
- `dva kg search <text>`: Search with semantic or exact matching (✅ both providers)
- `dva kg stats`: Display graph statistics (✅ both providers)
- `dva kg tool`: Generate ADK tool for knowledge graph operations (Neo4j only)
- `dva kg visualize`: Create interactive graph visualization (Neo4j only)
- `dva kg workspace`: Manage workspaces (LightRAG only)

**Note:** See [Provider Support Guide](docs/PROVIDER_SUPPORT.md) for detailed provider compatibility.

#### Data Source Configuration
- `dva data init`: Configure global GCS and Confluence settings
- `dva data create`: Register a new data source (local, GCS, Confluence, or Git)
- `dva data list`: List all configured data sources
- `dva data show <name>`: Show detailed information about a data source
- `dva data update <name>`: Update an existing data source
- `dva data delete <name>`: Delete a data source configuration

#### MCP Server Management
- `dva mcp list`: List available MCP servers
- `dva mcp test`: Test MCP server connections
- `dva mcp status`: Show MCP server status

#### Agent Management & Evaluation
- `dva agent create <name>`: Create a new agent
- `dva agent list`: List all agents
- `dva agent info <name>`: Show agent details
- `dva agent deploy <name>`: Deploy an agent
- `dva agent test <name>`: Test an agent
- `dva eval validate-skill <path>`: Validate a skill file for quality and structure
- `dva eval validate-skill <path> --output json`: Validate skill and output as JSON
- `dva eval validate-skill <path> --check structure`: Run specific validation checks

#### Code & Repository Management
- `dva code onboard`: Onboard a code repository
- `dva code list`: List onboarded repositories
- `dva code skills`: Show available skills for a repository
- `dva code analyze`: Analyze code structure

#### Skill Management
- `dva skill create <name>`: Create a new skill
- `dva skill list`: List available skills
- `dva skill install <source>`: Install a skill from GitHub
- `dva skill show <name>`: Show skill details

#### Skill Validation & Evaluation
- `dva eval validate-skill <path>`: Validate a skill file for quality and structure
- `dva eval validate-skill <path> --output json`: Validate skill with JSON output

**Note:** The skill validation system checks:
- ✅ YAML frontmatter structure (name, description fields)
- ✅ Required markdown sections (Instructions, Available Tools, Workflow)
- ✅ Markdown syntax and formatting
- ✅ Tool reference documentation
- ✅ Overall skill completeness and clarity

Example:
```bash
# Validate a skill file
`agent eval validate-skill .skills/pr-reviewer/SKILL.md

# Get detailed JSON report
`agent eval validate-skill .skills/pr-reviewer/SKILL.md --output json

# Quality Score: 92/100 = Excellent
# Includes: Full documentation, examples, clear workflow
```

For more information on skill evaluation, see [Skill Evaluation Integration](docs/SKILL_EVALUATION_INTEGRATION.md).

#### Domain Management
- `dva domain list`: List available domains
- `dva domain info <name>`: Show domain details
- `dva domain create <name>`: Create a new domain

#### Product Management
- `dva product list`: List available products
- `dva product info <name>`: Show product details
- `dva product create <name>`: Create a new product

#### History & Execution Tracking
- `dva history list`: List execution history
- `dva history show <id>`: Show details of a past execution
- `dva history clear`: Clear execution history

#### Agent Templates
- `dva agent-template list`: List available agent templates
- `dva agent-template info <name>`: Show template details
- `dva agent-template create`: Create from template

#### Agent Tools
- `dva agent-tool list`: List available agent tools
- `dva agent-tool info <name>`: Show tool details
- `dva agent-tool generate`: Generate tool code

#### Example Commands
- `dva hello [NAME]`: Simple greeting command (placeholder)

### Google Vertex AI Setup

Configure Vertex AI for your projects:

```bash
# First time: prompts for project ID and runs gcloud auth
`agent init vertex-ai

# Subsequent runs: reuses existing config, only refreshes auth
`agent init vertex-ai

# Update specific settings
`agent init vertex-ai --location us-east1

# Skip authentication if already authenticated
`agent init vertex-ai --skip-auth

# View saved configuration
`agent init show

# The configuration will be automatically applied to new projects
```

See [Vertex AI Setup Guide](docs/VERTEX_AI_SETUP.md) for detailed instructions.

### Creating a New Agentic Project

The CLI provides an embedded template system with multiple frameworks and use cases:

```bash
# Create a basic agent
`agent project create my-agent

# Create with specific use case
`agent project create my-rag --use-case rag
`agent project create my-kg --use-case knowledge-graph
`agent project create my-bot --use-case chatbot

# Create with specific framework
`agent project create my-agent --framework langgraph

# Add extra tools
`agent project create my-bot --use-case chatbot --tools web_search,api_caller

# Include Docker support
`agent project create my-prod --use-case rag --docker

# List all available frameworks, use cases, and tools
`agent project list-templates
```

#### Available Use Cases

| Use Case | Description |
|----------|-------------|
| `basic` | Simple agent with calculator, text analyzer, file reader |
| `rag` | Document retrieval with embeddings and vector search |
| `knowledge-graph` | Neo4j knowledge graph integration |
| `multi-agent` | Orchestrated multi-agent system |
| `chatbot` | Conversational agent with memory |
| `data-pipeline` | ETL and data processing workflows |
| `code-assistant` | Code generation, review, and refactoring |

See [Project Templates Guide](docs/PROJECT_TEMPLATES.md) for full documentation.

If you've configured Vertex AI with `dva init vertex-ai`, the project will automatically include Vertex AI settings.

After creating a project:

```bash
cd my-agent-project

# Edit .env file with your API keys
nano .env

# Install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run the example agent
python src/main.py

# Or use make commands
make install-dev
make run
make test
```

### Using Knowledge Graph

Build intelligent data retrieval systems with Neo4j or LightRAG + Vertex AI:

```bash
# Install knowledge graph dependencies
pip install -e ".[kg]"

# Option 1: Use LightRAG (recommended for simplicity)
cd ../lightrag-infrastructure
./setup.sh

`agent kg init --provider lightrag --lightrag-url http://localhost:8001
`agent kg ingest --path /path/to/documents
`agent kg stats

# Option 2: Use Neo4j (for advanced graph operations)
cd ../neo4j-infrastructure
./setup.sh

`agent kg init --provider neo4j \
  --uri bolt://localhost:7687 \
  --username neo4j \
  --password password

# Ingest data (works with both providers)
`agent kg ingest --path document.pdf
`agent kg ingest --path data.csv
`agent kg ingest --path ./documents

# Or ingest using configured data sources
`agent data create --name my-docs --source-type doc --source-location /path/to/docs
`agent kg ingest --source my-docs

# Query and search (Neo4j only)
`agent kg query "Find all people who work at Google"
`agent kg search "artificial intelligence" --semantic

# View statistics (both providers)
`agent kg stats

# Generate tool for ADK agents (Neo4j only)
`agent kg tool --name knowledge_graph --output tools/kg_tool.py

# Visualize the graph (Neo4j only)
`agent kg visualize --output graph.html
```

**Prerequisites**: 
- Neo4j: See [neo4j-infrastructure](../neo4j-infrastructure/README.md)
- LightRAG: See [lightrag-infrastructure](../lightrag-infrastructure/README.md)

See the [Knowledge Graph Guide](docs/KNOWLEDGE_GRAPH.md) and [LightRAG Integration](docs/LIGHTRAG_INTEGRATION.md) for detailed documentation.

### Managing Data Sources

Configure and manage data sources for ingestion into knowledge graphs or other pipelines:

```bash
# Configure global GCS settings
`agent data init \
  --gcs-project-id your-project-id \
  --gcs-bucket your-bucket \
  --gcs-prefix data/

# Configure Confluence settings
`agent data init \
  --confluence-url https://your-domain.atlassian.net/wiki \
  --confluence-username user@example.com \
  --confluence-api-token-env CONFLUENCE_API_TOKEN

# Create a local documentation source
`agent data create \
  --name local-docs \
  --source-type doc \
  --source-location /path/to/docs \
  --description "Local documentation folder" \
  --tags "local,documentation"

# Create a GCS data source
`agent data create \
  --name gcs-data \
  --source-type doc \
  --source-location gs://my-bucket/data/docs \
  --description "GCS documentation bucket" \
  --tags "gcs,production"

# Create a Confluence source
`agent data create \
  --name team-wiki \
  --source-type confluence \
  --source-location https://your-domain.atlassian.net/wiki/spaces/TEAM \
  --description "Team Confluence space" \
  --tags "confluence,wiki"

# Create a Git repository source with branch
`agent data create \
  --name backend-repo \
  --source-type git \
  --source-location https://github.com/company/backend.git \
  --git-branch main \
  --description "Backend codebase" \
  --tags "git,backend,production"

# Create a Git repository source with tag (SSH URL)
`agent data create \
  --name frontend-release \
  --source-type git \
  --source-location git@github.com:company/frontend.git \
  --git-tag v2.1.0 \
  --description "Frontend release v2.1.0" \
  --tags "git,frontend,release"

# List all data sources
`agent data list

# Show details of a specific source
`agent data show team-wiki

# Update a data source
`agent data update local-docs \
  --description "Updated documentation" \
  --tags "local,docs,updated"

# Delete a data source
`agent data delete old-source --yes
```

**Configuration Storage**: Data source configurations are stored in `~/.dva-agentic/config.json` alongside other CLI settings.

**Supported Source Types**:
- **doc**: Local file paths or GCS paths (`gs://bucket/path`)
- **confluence**: Confluence space URLs
- **git**: Git repository URLs (HTTPS, SSH, git:// protocols) with optional branch or tag

**Git-Specific Features**:
- Specify `--git-branch` to track a specific branch (e.g., `main`, `develop`)
- Specify `--git-tag` to track a specific release tag (e.g., `v1.0.0`)
- Cannot specify both branch and tag simultaneously
- If neither is specified, the default branch will be used

**Data Source Integration**: Data sources are now integrated with `dva kg ingest`:
```bash
# Configure data sources
`agent data create --name team-wiki --source-type confluence --source-location https://company.atlassian.net
`agent data create --name local-docs --source-type doc --source-location /path/to/docs

# Ingest from configured data sources
`agent kg ingest --source team-wiki
`agent kg ingest --source local-docs

# Note: Git repositories are not yet supported for direct ingestion
# Clone locally first, then use --path option
```

## Development

### Project Structure

```
agentic-cli/
├── src/
│   └── agentic_cli/
│       ├── __init__.py          # Package version
│       ├── main.py              # Main CLI entry point
│       ├── commands/            # Command modules
│       │   ├── init.py          # Initialization commands
│       │   ├── project.py       # Project management
│       │   ├── data.py          # Data source configuration
│       │   └── kg.py            # Knowledge graph commands
│       └── kg/                  # Knowledge graph module
│           ├── config.py        # Configuration
│           ├── neo4j_client.py  # Neo4j client
│           ├── ingest.py        # Data ingestion
│           ├── parsers.py       # File parsers
│           ├── entity_extraction.py  # Vertex AI extraction
│           ├── query.py         # Query execution
│           ├── search.py        # Search functionality
│           └── tool_generator.py     # ADK tool generation
├── tests/                       # Test directory
│   ├── test_data_commands.py   # Data command tests
│   ├── test_kg.py              # KG tests
│   └── ...                     # Other tests
├── docs/                        # Documentation
│   ├── KNOWLEDGE_GRAPH.md      # KG guide
│   └── VERTEX_AI_SETUP.md      # Vertex AI setup
├── pyproject.toml              # Project configuration
├── Makefile                    # Development commands
└── README.md                   # This file
```

### Development Commands

```bash
# Install with dev dependencies
make install-dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Lint code
make lint

# Format code
make format

# Clean build artifacts
make clean

# Run integration tests
make integration

# Run CLI with arguments
make run ARGS="--version"
make run ARGS="hello World"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agentic_cli --cov-report=html

# Or use make commands
make test
make test-cov
```

### Code Quality

The project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check code style
make lint

# Auto-format code
make format
```

## Adding New Commands

To add new commands, create a new module in `src/agentic_cli/commands/`:

```python
# src/agentic_cli/commands/my_command.py
import typer
from rich.console import Console

console = Console()

def my_command():
    """Your command description."""
    console.print("[green]Command executed![/green]")
```

Then register it in `main.py`:

```python
from agentic_cli.commands import my_command

app.command()(my_command.my_command)
```

## Integration Testing

Run comprehensive integration tests to verify all commands work correctly:

```bash
make integration
```

This will test:
- Version display
- Help output
- All registered commands
- Command arguments and options

## Roadmap

- [x] Knowledge graph integration with Neo4j + Vertex AI
- [x] Multi-format data ingestion (PDF, CSV, JSON, text)
- [x] AI-powered entity extraction and relationship building
- [x] Semantic search with embeddings
- [x] ADK tool generation for knowledge graph
- [ ] Implement additional ADK agent command wrappers
- [ ] Add agent creation and management commands
- [ ] Implement workflow orchestration commands
- [ ] Support for multiple agent backends
- [ ] Interactive mode for complex workflows
- [ ] Additional graph databases (ArangoDB, TigerGraph)
- [ ] Real-time data streaming to knowledge graph

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests and linting: `make test && make lint`
4. Submit a pull request

## License

[Add your license here]

## Version

Current version: 0.1.0
