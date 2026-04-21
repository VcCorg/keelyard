# Basic Agent Template

A simple agent template using Google ADK framework with essential tools for getting started.

## Features

- **Framework**: Google ADK (Agent Development Kit)
- **Tools**: Calculator, Text Analyzer, File Reader
- **Use Case**: Basic agent functionality
- **Dependencies**: Google ADK, Typer, Rich, Pydantic

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Google Cloud credentials
   ```

3. **Run the agent**:
   ```bash
   python src/main.py
   ```

## Project Structure

```
basic-agent/
|-- src/
|   |-- basic_agent/
|   |   |-- __init__.py
|   |   |-- main.py
|   |   |-- agents/
|   |   |   |-- __init__.py
|   |   |   |-- basic_agent.py
|   |   |-- tools/
|   |   |   |-- __init__.py
|   |   |   |-- calculator.py
|   |   |   |-- text_analyzer.py
|   |   |   |-- file_reader.py
|   |   |-- config.py
|   |-- tests/
|   |   |-- test_basic_agent.py
|-- .env.example
|-- README.md
|-- pyproject.toml
```

## Configuration

The agent uses the following environment variables:

- `GOOGLE_PROJECT_ID`: Your Google Cloud project ID
- `GOOGLE_LOCATION`: Google Cloud region (default: us-central1)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account credentials
- `VERTEX_AI_MODEL`: Vertex AI model to use (default: gemini-2.0-flash-001)

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
ruff check .
ruff format .
```

### Type Checking

```bash
mypy src/
```

## Usage Examples

```python
from basic_agent.agents.basic_agent import BasicAgent

# Create and run agent
agent = BasicAgent()
response = agent.run("What is 15 * 23?")
print(response)
```

## License

MIT License - see LICENSE file for details.
