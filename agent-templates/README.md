# Agentic Agent Templates

A comprehensive collection of agent templates for the Agentic CLI, supporting multiple frameworks and use cases.

## Overview

This repository contains agent templates that can be used with the Agentic CLI to quickly scaffold new agent projects. Templates are organized by framework and use case, making it easy to find the right starting point for your project.

## Available Templates

### ADK Framework Templates

#### Basic Agent (`adk-basic-agent`)
- **Use Case**: Basic agent functionality
- **Tools**: Calculator, Text Analyzer, File Reader
- **Description**: Simple agent template using Google ADK framework with essential tools for getting started
- **Dependencies**: Google ADK, Typer, Rich, Pydantic

#### PR Reviewer (`adk-pr-reviewer`)
- **Use Case**: Code review automation
- **Tools**: Bitbucket MCP, Memory, Jira MCP (optional)
- **Description**: Automated pull request reviewer using ADK framework with Bitbucket and Jira integration
- **Dependencies**: Google ADK, MCP, HTTPX, Google Generative AI

#### RAG Agent (`adk-rag-agent`)
- **Use Case**: Knowledge management
- **Tools**: Vector Search, Document Loader, Embeddings
- **Description**: Retrieval-augmented generation agent with document processing and vector search capabilities
- **Dependencies**: Google ADK, ChromaDB, Sentence Transformers

#### Scrum Master (`adk-scrum-master`)
- **Use Case**: Project management
- **Tools**: Jira MCP, Confluence MCP, Bitbucket MCP, Memory
- **Description**: Domain-scoped Scrum Master agent with Jira, Confluence, and Bitbucket MCP integration
- **Dependencies**: Google ADK, MCP, HTTPX, Google Generative AI

### LangGraph Framework Templates

#### Multi-Agent System (`langgraph-multi-agent`)
- **Use Case**: Multi-agent orchestration
- **Tools**: Agent Router, Memory, Text Analyzer, File Reader/Writer
- **Description**: Multi-agent collaboration system using LangGraph with agent routing and orchestration
- **Dependencies**: LangGraph, LangChain, LangChain Google GenAI

#### Conversational Agent (`langgraph-chatbot`)
- **Use Case**: Conversational AI
- **Tools**: Memory, Text Analyzer, Web Search, API Caller
- **Description**: Conversational chatbot with memory and context management using LangGraph
- **Dependencies**: LangGraph, LangChain, LangChain Google GenAI

## Template Structure

Each template follows a consistent structure:

```
template-name/
|-- src/
|   |-- template_name/
|   |   |-- __init__.py
|   |   |-- main.py
|   |   |-- agents/
|   |   |-- tools/
|   |   |-- config.py
|   |-- tests/
|-- .env.example
|-- README.md
|-- pyproject.toml
```

## Usage

### Prerequisites

1. Install the Agentic CLI:
   ```bash
   pip install agentic-cli
   ```

2. Configure the registry:
   ```bash
   agent agent-template registry add https://bitbucket.example.com/scm/~your-user/agent-templates.git
   ```

### Using Templates

#### List Available Templates
```bash
`agent agent-template list
`agent agent-template list --framework adk
`agent agent-template list --use-case pr-reviewer
`agent agent-template list --category code-review
```

#### Show Template Details
```bash
`agent agent-template show adk-pr-reviewer
```

#### Create Project from Template
```bash
# Basic usage
`agent project create my-agent --agent-template adk-basic-agent

# With additional tools
`agent project create my-pr-agent --agent-template adk-pr-reviewer --agent-tools jira-integration,slack-integration

# With domain context
`agent project create my-scrum-agent --agent-template adk-scrum-master --domain cwow-facility
```

#### Install Template Directly
```bash
`agent agent-template install adk-basic-agent --target ./my-agent
```

### Template Categories

- **Foundational**: Basic agent templates for getting started
- **Code Review**: Code reviewing and quality assurance agents
- **Knowledge**: Knowledge management and RAG agents
- **Project Management**: Project management and agile agents
- **Orchestration**: Multi-agent orchestration and coordination
- **Conversational**: Conversational and chatbot agents

## Framework Support

### Google ADK (Agent Development Kit)
- **Description**: Google's official framework for building AI agents
- **Strengths**: Deep integration with Google Cloud, Vertex AI, and Google services
- **Use Cases**: Enterprise applications, Google Cloud integration, production deployments

### LangGraph
- **Description**: Framework for building complex multi-agent systems
- **Strengths**: Agent orchestration, state management, complex workflows
- **Use Cases**: Multi-agent systems, workflow automation, complex business processes

## Contributing

### Adding New Templates

1. Create a new directory under the appropriate framework folder:
   ```bash
   mkdir templates/adk/my-new-template
   ```

2. Follow the standard template structure
3. Add the template to `registry.json`:
   ```json
   {
     "name": "My New Template",
     "description": "Description of the template",
     "framework": "adk",
     "use_case": "my-use-case",
     "category": "my-category",
     "tags": ["tag1", "tag2"],
     "path": "templates/adk/my-new-template",
     "dependencies": ["dependency1", "dependency2"],
     "author": "Your Name",
     "version": "1.0.0",
     "created_at": "2024-04-15T10:00:00Z",
     "updated_at": "2024-04-15T10:00:00Z"
   }
   ```

4. Submit a pull request

### Template Guidelines

- **Consistency**: Follow the established template structure
- **Documentation**: Include comprehensive README and inline documentation
- **Testing**: Include unit tests for all major functionality
- **Dependencies**: Specify exact versions for all dependencies
- **Examples**: Include usage examples and sample configurations

## Configuration

Templates use environment variables for configuration. Each template includes an `.env.example` file with the required variables:

```bash
# Google Cloud Configuration
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
VERTEX_AI_MODEL=gemini-2.0-flash-001

# Agent Configuration
AGENT_NAME=my-agent
AGENT_DESCRIPTION=My agent description
LOG_LEVEL=INFO
```

## Support

- **Documentation**: [Agentic CLI Documentation](https://docs.keel.com)
- **Issues**: [GitHub Issues](https://github.com/keel/agent-templates/issues)
- **Discussions**: [GitHub Discussions](https://github.com/keel/agent-templates/discussions)

## License

MIT License - see LICENSE file for details.

## Version History

- **1.0.0**: Initial release with ADK and LangGraph templates
- **1.1.0**: Added PR Reviewer and Scrum Master templates
- **1.2.0**: Enhanced RAG template with improved vector search
- **1.3.0**: Added LangGraph conversational agent template
