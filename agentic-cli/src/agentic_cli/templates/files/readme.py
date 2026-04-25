"""Generate README.md content."""

from agentic_cli.templates.config import TemplateConfig


def get_readme_content(config: TemplateConfig) -> str:
    """Generate README.md content based on configuration."""
    tools_list = "\n".join(f"- {t.display_name}" for t in config.tools)
    
    return f'''# {config.name}

{config.use_case.description}

## Framework

**{config.framework.display_name}**

## Use Case

**{config.use_case.display_name}**

## Included Tools

{tools_list}

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
{config.name}/
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
'''
