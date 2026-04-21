# My ADK Agent Project

A production-ready ADK agent project template for building agentic workflows.

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install -e ".[dev]"
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Agent Configuration
AGENT_MODEL=gpt-4
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=2000

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 📁 Project Structure

```
my-adk-agent-project/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py         # Base agent class
│   │   └── example.py      # Example agent
│   ├── tools/              # Agent tools
│   │   ├── __init__.py
│   │   └── example_tools.py
│   ├── workflows/          # Workflow definitions
│   │   ├── __init__.py
│   │   └── example_workflow.py
│   ├── config.py           # Configuration management
│   └── main.py             # Main entry point
├── tests/                  # Test suite
│   ├── test_agents.py
│   └── test_workflows.py
├── notebooks/              # Jupyter notebooks for experimentation
│   └── agent_playground.ipynb
├── .env.example            # Example environment variables
├── pyproject.toml          # Project configuration
├── Makefile               # Development commands
└── README.md              # This file
```

## 🤖 Usage

### Running the Example Agent

```bash
# Run the main script
python src/main.py

# Or use make
make run
```

### Interactive Development

```bash
# Start IPython with project context
make shell

# Or start Jupyter
make notebook
```

### Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test
pytest tests/test_agents.py -v
```

## 🛠️ Development

### Available Make Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make install-dev   # Install with dev dependencies
make test          # Run tests
make test-cov      # Run tests with coverage
make lint          # Run linting
make format        # Format code
make clean         # Clean build artifacts
make run           # Run the main application
make shell         # Start IPython shell
make notebook      # Start Jupyter notebook
```

### Code Quality

```bash
# Check code style
make lint

# Auto-format code
make format
```

## 📚 Creating Your Own Agent

### 1. Define Your Agent

Create a new agent in `src/agents/`:

```python
# src/agents/my_agent.py
from agents.base import BaseAgent
from typing import Dict, Any

class MyAgent(BaseAgent):
    """Your custom agent implementation."""
    
    def __init__(self, model: str = "gpt-4", **kwargs):
        super().__init__(model=model, **kwargs)
        # Initialize your agent
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return results."""
        # Your agent logic here
        return {"result": "processed"}
```

### 2. Create Tools

Add tools in `src/tools/`:

```python
# src/tools/my_tools.py
from typing import Any

def my_tool(input: str) -> str:
    """Tool description for the agent."""
    # Tool implementation
    return f"Processed: {input}"
```

### 3. Build Workflows

Define workflows in `src/workflows/`:

```python
# src/workflows/my_workflow.py
from agents.my_agent import MyAgent

async def run_workflow(input_data: dict) -> dict:
    """Execute your workflow."""
    agent = MyAgent()
    result = await agent.process(input_data)
    return result
```

## 🔧 Configuration

The project uses Pydantic Settings for configuration management. See `src/config.py` for available settings.

### Environment Variables

- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `AGENT_MODEL`: Default model to use
- `AGENT_TEMPERATURE`: Temperature for generation
- `AGENT_MAX_TOKENS`: Maximum tokens for responses
- `ENVIRONMENT`: Environment (development/staging/production)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

## 📊 Monitoring and Logging

The project includes structured logging. Logs are written to:
- Console (formatted with Rich)
- `logs/agent.log` (rotating file handler)

## 🚢 Deployment

### Docker (Coming Soon)

```bash
# Build Docker image
docker build -t my-adk-agent .

# Run container
docker run -p 8000:8000 my-adk-agent
```

## 🤝 Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests: `make test`
4. Run linting: `make lint`
5. Submit a pull request

## 📝 License

[Add your license here]

## 🔗 Resources

- [ADK Documentation](https://docs.adk.dev)
- [Python Best Practices](https://docs.python-guide.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## 🆘 Support

For issues and questions:
- Create an issue in the repository
- Check the documentation
- Contact the team

---

**Happy Building! 🚀**
