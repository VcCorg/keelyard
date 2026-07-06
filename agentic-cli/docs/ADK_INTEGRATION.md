# ADK Agent Integration Guide

This guide explains how to integrate ADK agent functionality into the Agentic CLI.

## Option 1: Using Local Python Modules

If you're developing ADK modules locally in the parent project, you can reference them directly.

### Step 1: Create Your ADK Module

In the parent project directory (`/Users/your-user/agentic-project/`), create your ADK modules:

```bash
# Example structure
agentic-project/
├── agentic-cli/          # This CLI project
└── adk_modules/              # Your ADK modules
    ├── __init__.py
    ├── agent.py
    └── workflows.py
```

### Step 2: Add Local Dependency to pyproject.toml

Update `pyproject.toml` to include your local modules:

```toml
[project.optional-dependencies]
adk = [
    # Reference local modules using relative path
]

# Or add to main dependencies if always needed
dependencies = [
    "typer>=0.12.0",
    "rich>=13.7.0",
    # Add your local module path here when ready
]
```

### Step 3: Install in Editable Mode

```bash
# Install with local ADK modules
uv pip install -e ".[dev,adk]"
```

## Option 2: Using PyPI Package

When ADK agent is available on PyPI:

```toml
[project.optional-dependencies]
adk = [
    "adk-agent>=0.1.0",
]
```

## Option 3: Using Git Repository

If ADK agent is in a Git repository:

```toml
[project.optional-dependencies]
adk = [
    "adk-agent @ git+https://github.com/your-org/adk-agent.git@main",
]
```

## Creating ADK Command Wrappers

### Example: Agent Management Command

Create a new command module:

```python
# src/agentic_cli/commands/agent.py
import typer
from rich.console import Console
from typing_extensions import Annotated

# Import your ADK modules
# from adk_modules import agent

console = Console()
agent_app = typer.Typer(help="Manage ADK agents")


@agent_app.command("create")
def create_agent(
    name: Annotated[str, typer.Argument(help="Agent name")],
    model: Annotated[str, typer.Option("--model", "-m", help="Model to use")] = "gpt-4",
) -> None:
    """Create a new ADK agent."""
    console.print(f"[green]Creating agent:[/green] {name}")
    console.print(f"[dim]Model: {model}[/dim]")
    
    # Your ADK integration code here
    # result = agent.create(name=name, model=model)
    
    console.print("[green]✓[/green] Agent created successfully!")


@agent_app.command("list")
def list_agents() -> None:
    """List all available agents."""
    console.print("[cyan]Available agents:[/cyan]")
    
    # Your ADK integration code here
    # agents = agent.list_all()
    
    console.print("  • agent-1")
    console.print("  • agent-2")


@agent_app.command("run")
def run_agent(
    name: Annotated[str, typer.Argument(help="Agent name")],
    prompt: Annotated[str, typer.Option("--prompt", "-p", help="Prompt to execute")],
) -> None:
    """Run an agent with a prompt."""
    console.print(f"[green]Running agent:[/green] {name}")
    console.print(f"[dim]Prompt: {prompt}[/dim]")
    
    # Your ADK integration code here
    # result = agent.run(name=name, prompt=prompt)
    
    console.print("[green]✓[/green] Agent execution completed!")
```

### Register the Command in main.py

```python
# src/agentic_cli/main.py
from agentic_cli.commands.agent import agent_app

# Add to your main app
app.add_typer(agent_app, name="agent")
```

### Usage

```bash
# Create an agent
`agent agent create my-agent --model gpt-4

# List agents
`agent agent list

# Run an agent
`agent agent run my-agent --prompt "Analyze this data"
```

## Example Command Structure

Here's a complete example of a well-structured ADK command:

```python
# src/agentic_cli/commands/workflow.py
import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated
from pathlib import Path

console = Console()
workflow_app = typer.Typer(help="Manage ADK workflows")


@workflow_app.command("create")
def create_workflow(
    name: Annotated[str, typer.Argument(help="Workflow name")],
    config: Annotated[Path, typer.Option("--config", "-c", help="Config file path")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False,
) -> None:
    """Create a new workflow from configuration."""
    if verbose:
        console.print(f"[dim]Loading config from: {config}[/dim]")
    
    console.print(f"[green]Creating workflow:[/green] {name}")
    
    # Your ADK workflow creation logic
    
    console.print("[green]✓[/green] Workflow created!")


@workflow_app.command("status")
def workflow_status(
    name: Annotated[str, typer.Argument(help="Workflow name")],
) -> None:
    """Check workflow status."""
    table = Table(title=f"Workflow: {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    # Your ADK status check logic
    table.add_row("Status", "Running")
    table.add_row("Progress", "75%")
    table.add_row("Started", "2025-10-28 09:00:00")
    
    console.print(table)
```

## Testing ADK Commands

Create tests for your ADK commands:

```python
# tests/test_agent_commands.py
from typer.testing import CliRunner
from agentic_cli.main import app

runner = CliRunner()


def test_agent_create():
    """Test agent creation command."""
    result = runner.invoke(app, ["agent", "create", "test-agent"])
    assert result.exit_code == 0
    assert "Creating agent" in result.stdout


def test_agent_list():
    """Test agent list command."""
    result = runner.invoke(app, ["agent", "list"])
    assert result.exit_code == 0
```

## Best Practices

1. **Modular Commands**: Keep each command group in its own module
2. **Rich Output**: Use Rich for beautiful terminal output
3. **Error Handling**: Add proper error handling and user-friendly messages
4. **Type Hints**: Use Annotated types for better CLI documentation
5. **Testing**: Write tests for all commands
6. **Documentation**: Add docstrings and help text
7. **Configuration**: Support config files for complex operations
8. **Async Support**: Use async/await if ADK operations are async

## Next Steps

1. Create your ADK modules in the parent project
2. Add command modules in `src/agentic_cli/commands/`
3. Register commands in `main.py`
4. Write tests for new commands
5. Update documentation

## Resources

- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [uv Documentation](https://github.com/astral-sh/uv)
