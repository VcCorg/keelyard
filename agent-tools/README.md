# DVA Agent Tools

A comprehensive collection of reusable tools for DVA agents, supporting integrations, data processing, AI utilities, and mathematical calculations.

## Overview

This repository contains agent tools that can be used with the DVA Agentic CLI to extend agent capabilities. Tools are organized by category and designed to be easily integrated into any agent project.

## Available Tools

### Integration Tools

#### Jira Integration (`jira-integration`)
- **Category**: Integrations
- **Description**: Tool for integrating with Jira for issue tracking, project management, and workflow automation
- **Features**: Issue creation, search, comments, transitions, project management
- **Dependencies**: jira>=3.1.0, requests>=2.31.0, pydantic>=2.0.0
- **Author**: DVA Team
- **Version**: 1.1.0

#### Slack Integration (`slack-integration`)
- **Category**: Integrations
- **Description**: Tool for integrating with Slack for team communication, notifications, and bot interactions
- **Features**: Message sending, channel management, user interactions, webhooks
- **Dependencies**: slack-sdk>=3.21.0, requests>=2.31.0, pydantic>=2.0.0
- **Author**: DVA Team
- **Version**: 1.0.0

#### Confluence Integration (`confluence-integration`)
- **Category**: Integrations
- **Description**: Tool for integrating with Confluence for documentation management and wiki operations
- **Features**: Page creation, updates, search, space management, content conversion
- **Dependencies**: atlassian-python-api>=3.41.0, requests>=2.31.0, pydantic>=2.0.0
- **Author**: DVA Team
- **Version**: 1.0.0

### Data Processing Tools

#### PDF Document Processor (`pdf-processor`)
- **Category**: Data Processors
- **Description**: Tool for processing and extracting content from PDF files with text, images, and metadata extraction
- **Features**: Text extraction, image extraction, metadata parsing, OCR support
- **Dependencies**: PyPDF2>=3.0.0, pymupdf>=1.23.0, pillow>=10.0.0
- **Author**: DVA Team
- **Version**: 2.0.0

#### CSV Data Processor (`csv-processor`)
- **Category**: Data Processors
- **Description**: Tool for processing CSV files with data validation, transformation, and analysis capabilities
- **Features**: Data validation, transformation, analysis, Excel export
- **Dependencies**: pandas>=2.0.0, numpy>=1.24.0, openpyxl>=3.1.0
- **Author**: DVA Team
- **Version**: 1.2.0

#### JSON Data Processor (`json-processor`)
- **Category**: Data Processors
- **Description**: Tool for processing JSON files with schema validation, transformation, and querying capabilities
- **Features**: Schema validation, transformation, JMESPath querying, pretty printing
- **Dependencies**: jsonschema>=4.17.0, pydantic>=2.0.0, jmespath>=1.0.0
- **Author**: DVA Team
- **Version**: 1.1.0

### AI Utility Tools

#### Text Analyzer (`text-analyzer`)
- **Category**: AI Utilities
- **Description**: AI-powered text analysis tool for sentiment analysis, entity extraction, and language processing
- **Features**: Sentiment analysis, entity extraction, language detection, text classification
- **Dependencies**: transformers>=4.30.0, torch>=2.0.0, spacy>=3.7.0
- **Author**: DVA Team
- **Version**: 1.3.0

#### Text Summarizer (`summarizer`)
- **Category**: AI Utilities
- **Description**: AI-powered text summarization tool for extractive and abstractive summarization
- **Features**: Extractive summarization, abstractive summarization, length control
- **Dependencies**: transformers>=4.30.0, torch>=2.0.0, sentence-transformers>=2.2.0
- **Author**: DVA Team
- **Version**: 1.2.0

#### Text Translator (`translator`)
- **Category**: AI Utilities
- **Description**: AI-powered text translation tool supporting multiple languages and translation models
- **Features**: Multi-language support, model selection, batch translation
- **Dependencies**: transformers>=4.30.0, torch>=2.0.0, sentencepiece>=0.1.0
- **Author**: DVA Team
- **Version**: 1.1.0

### Calculator Tools

#### Basic Calculator (`basic-calculator`)
- **Category**: Calculators
- **Description**: Basic calculator tool for arithmetic operations and mathematical functions
- **Features**: Arithmetic operations, basic functions, unit conversion
- **Dependencies**: numpy>=1.24.0, sympy>=1.12.0
- **Author**: DVA Team
- **Version**: 1.0.0

#### Scientific Calculator (`scientific-calculator`)
- **Category**: Calculators
- **Description**: Advanced scientific calculator with complex mathematical operations and scientific functions
- **Features**: Advanced functions, symbolic computation, statistical analysis
- **Dependencies**: numpy>=1.24.0, sympy>=1.12.0, scipy>=1.10.0
- **Author**: DVA Team
- **Version**: 1.1.0

## Usage

### Prerequisites

1. Install the DVA Agentic CLI:
   ```bash
   pip install dva-agentic-cli
   ```

2. Configure the registry:
   ```bash
   dva agent-tool registry add https://bitbucket.example.com/scm/~your-user/dva-agent-tools.git
   ```

### Using Tools

#### List Available Tools
```bash
dva agent-tool list
dva agent-tool list --category integrations
dva agent-tool list --tag jira
```

#### Show Tool Details
```bash
dva agent-tool show jira-integration
```

#### Install Tools in Project
```bash
# Install single tool
dva agent-tool install jira-integration --target ./my-agent/src/tools

# Install multiple tools
dva agent-tool install jira-integration --target ./my-agent/src/tools
dva agent-tool install slack-integration --target ./my-agent/src/tools

# Install tools during project creation
dva project create my-agent --agent-tools jira-integration,slack-integration
```

#### Show Tool Dependencies
```bash
dva agent-tool dependencies jira-integration
```

### Tool Categories

- **Integrations**: External service integrations (Jira, Slack, Confluence, etc.)
- **Data Processors**: Data processing and transformation tools (PDF, CSV, JSON, etc.)
- **AI Utilities**: AI-powered utility tools and helpers (text analysis, summarization, etc.)
- **Calculators**: Mathematical calculation tools (basic, scientific, statistical)

## Tool Structure

Each tool follows a consistent structure:

```
tool-name/
|-- src/
|   |-- main.py (or tool-specific entry point)
|   |-- __init__.py
|   |-- config.py
|   |-- utils.py
|-- tests/
|-- README.md
|-- pyproject.toml
```

### Tool Interface

Tools should implement a consistent interface:

```python
class ToolName:
    """Tool description."""
    
    def __init__(self, **kwargs):
        """Initialize the tool."""
        pass
    
    def execute(self, **args):
        """Execute the tool functionality."""
        pass
    
    def get_info(self):
        """Get tool information."""
        return {
            "name": "Tool Name",
            "version": "1.0.0",
            "description": "Tool description",
            "capabilities": ["capability1", "capability2"],
            "dependencies": ["dep1", "dep2"]
        }
```

## Integration Examples

### Using Jira Integration Tool

```python
from tools.integrations.jira.src.main import JiraIntegrationTool

# Initialize tool
jira_tool = JiraIntegrationTool(
    base_url="https://your-domain.atlassian.net",
    username="your-email@example.com",
    api_token="your-api-token"
)

# Test connection
result = jira_tool.test_connection()

# Get projects
projects = jira_tool.get_projects()

# Search issues
issues = jira_tool.search_issues("project = PROJ AND status = 'In Progress'")
```

### Using PDF Processor Tool

```python
from tools.data_processors.pdf.src.processor import PDFProcessor

# Initialize tool
pdf_tool = PDFProcessor()

# Extract text from PDF
text = pdf_tool.extract_text("document.pdf")

# Extract metadata
metadata = pdf_tool.extract_metadata("document.pdf")

# Extract images
images = pdf_tool.extract_images("document.pdf", output_dir="./images")
```

### Using Text Analyzer Tool

```python
from tools.ai_utilities.text_analyzer.src.analyzer import TextAnalyzer

# Initialize tool
analyzer = TextAnalyzer()

# Analyze sentiment
sentiment = analyzer.analyze_sentiment("This is a great product!")

# Extract entities
entities = analyzer.extract_entities("John works at Google in California.")

# Classify text
category = analyzer.classify_text("This is a technical document about software development.")
```

## Configuration

Tools use environment variables for configuration. Each tool includes configuration documentation:

### Jira Integration
```bash
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

### Slack Integration
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
```

### Text Analyzer
```bash
HUGGINGFACE_MODEL=bert-base-uncased
OPENAI_API_KEY=your-openai-key
```

## Contributing

### Adding New Tools

1. Create a new directory under the appropriate category:
   ```bash
   mkdir tools/integrations/my-new-tool
   ```

2. Follow the standard tool structure
3. Add the tool to `registry.json`:
   ```json
   {
     "name": "My New Tool",
     "description": "Description of the tool",
     "category": "integrations",
     "tags": ["tag1", "tag2"],
     "path": "tools/integrations/my-new-tool",
     "entry_point": "src/main.py",
     "class_name": "MyNewTool",
     "dependencies": ["dependency1", "dependency2"],
     "author": "Your Name",
     "version": "1.0.0",
     "created_at": "2024-04-15T10:00:00Z",
     "updated_at": "2024-04-15T10:00:00Z"
   }
   ```

4. Submit a pull request

### Tool Guidelines

- **Consistency**: Follow the established tool structure and interface
- **Documentation**: Include comprehensive README and inline documentation
- **Testing**: Include unit tests for all major functionality
- **Dependencies**: Specify exact versions for all dependencies
- **Error Handling**: Implement proper error handling and logging
- **Configuration**: Use environment variables for configuration

## Development

### Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://bitbucket.example.com/scm/~your-user/dva-agent-tools.git
   cd dva-agent-tools
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest
   ```

4. Run linting:
   ```bash
   ruff check .
   ruff format .
   ```

### Testing Tools

Each tool should include comprehensive tests:

```python
import pytest
from tools.integrations.jira.src.main import JiraIntegrationTool

class TestJiraIntegrationTool:
    def test_init(self):
        tool = JiraIntegrationTool("url", "user", "token")
        assert tool.base_url == "url"
        assert tool.username == "user"
    
    @pytest.mark.asyncio
    async def test_connection(self):
        # Mock the HTTP requests
        tool = JiraIntegrationTool("url", "user", "token")
        result = tool.test_connection()
        # Assert expected behavior
```

## Support

- **Documentation**: [DVA Agentic CLI Documentation](https://docs.dva.com)
- **Issues**: [GitHub Issues](https://github.com/dva/dva-agent-tools/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dva/dva-agent-tools/discussions)

## License

MIT License - see LICENSE file for details.

## Version History

- **1.0.0**: Initial release with integration and data processing tools
- **1.1.0**: Added AI utility tools and enhanced calculator tools
- **1.2.0**: Improved error handling and configuration management
- **1.3.0**: Added advanced features and performance optimizations
