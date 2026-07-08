# test-agent

Simple agent with basic tools for getting started

## Framework

**Google ADK (Agent Development Kit)**

## Use Case

**Basic Agent**

## Included Tools

- Web Search

## Quick Start

```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the agent
python src/main.py
```

## Project Structure

```
test-agent/
├── src/
│   ├── agents/      # Agent implementations
│   ├── tools/       # Tool definitions
│   ├── workflows/   # Workflow orchestration
│   ├── config.py    # Configuration
│   └── main.py      # Entry point
├── tests/           # Test suite
├── examples/        # Usage examples
├── .env.example     # Environment template
├── pyproject.toml   # Project configuration
└── README.md
```

## Development

```bash
# Run tests
make test

# Format code
make format

# Lint
make lint
```

## License

MIT
