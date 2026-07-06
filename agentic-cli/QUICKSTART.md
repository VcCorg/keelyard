# Quick Start Guide

Get up and running with Agentic CLI in 2 minutes!

## 🚀 Fast Setup

```bash
# Navigate to the project
cd agentic-cli

# Run the setup script
./setup.sh

# Activate the virtual environment
source .venv/bin/activate

# Test the CLI
`agent --version
```

## ✅ Verify Installation

```bash
# Check version
`agent --version
# Output: agentic-cli version 0.1.0

# View help
`agent --help

# Try the hello command
`agent hello
`agent hello "Your Name"
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

1. **Explore the codebase**: Check out `src/agentic_cli/main.py`
2. **Add new commands**: Create modules in `src/agentic_cli/commands/`
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
`agent <your-command>
```

## 📚 Project Structure

```
agentic-cli/
├── src/agentic_cli/    # Main package
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
| `keel --version` | Show CLI version |
| `keel --help` | Show CLI help |

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

### Command not found: keel
```bash
# Reinstall the package
make install-dev
```

## 💡 Tips

- Use `keel --help` to see all available commands
- Each command has its own `--help` option
- The CLI uses rich formatting for beautiful output
- All commands are modular and extensible

Ready to build something awesome! 🎉
