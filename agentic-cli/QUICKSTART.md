# Quick Start Guide

Get up and running with DVA Agentic CLI in 2 minutes!

## 🚀 Fast Setup

```bash
# Navigate to the project
cd dva-agentic-cli

# Run the setup script
./setup.sh

# Activate the virtual environment
source .venv/bin/activate

# Test the CLI
dva --version
```

## ✅ Verify Installation

```bash
# Check version
dva --version
# Output: dva-agentic-cli version 0.1.0

# View help
dva --help

# Try the hello command
dva hello
dva hello "Your Name"
```

## 🧪 Run Tests

```bash
# Run all tests
make test

# Run integration tests
make integration

# Run with coverage
make test-cov
```

## 📝 Next Steps

1. **Explore the codebase**: Check out `src/dva_agentic_cli/main.py`
2. **Add new commands**: Create modules in `src/dva_agentic_cli/commands/`
3. **Integrate ADK**: Start wrapping ADK agent commands
4. **Write tests**: Add tests in `tests/` directory

## 🛠️ Development Workflow

```bash
# Make code changes
# ...

# Format code
make format

# Run linting
make lint

# Run tests
make test

# Test the CLI
dva <your-command>
```

## 📚 Project Structure

```
dva-agentic-cli/
├── src/dva_agentic_cli/    # Main package
│   ├── main.py             # CLI entry point
│   └── commands/           # Command modules
├── tests/                  # Test files
├── Makefile               # Development commands
└── pyproject.toml         # Project config
```

## 🎯 Common Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make install` | Install package |
| `make test` | Run tests |
| `make lint` | Check code quality |
| `make format` | Format code |
| `make integration` | Run integration tests |
| `dva --version` | Show CLI version |
| `dva --help` | Show CLI help |

## 🐛 Troubleshooting

### uv not found
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Virtual environment not activated
```bash
source .venv/bin/activate
```

### Command not found: dva
```bash
# Reinstall the package
make install-dev
```

## 💡 Tips

- Use `dva --help` to see all available commands
- Each command has its own `--help` option
- The CLI uses rich formatting for beautiful output
- All commands are modular and extensible

Ready to build something awesome! 🎉
