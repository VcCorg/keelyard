"""Extended project management commands for running and managing agents."""

import ast
import subprocess
import sys
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import List, Dict, Any, Optional
from typing_extensions import Annotated

from dva_agentic_cli.config import CLI_NAME

console = Console()


def discover_agents(project_path: Path) -> List[Dict[str, Any]]:
    """
    Discover agents in a project by scanning the agents directory.
    
    Returns:
        List of agent info dictionaries
    """
    agents = []
    agents_dir = project_path / "src" / "agents"
    
    if not agents_dir.exists():
        return agents
    
    for agent_file in agents_dir.glob("*.py"):
        if agent_file.name.startswith("_") or agent_file.name == "base.py":
            continue
        
        try:
            # Parse the file to extract agent classes
            content = agent_file.read_text()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's an agent class (inherits from BaseAgent or has Agent in name)
                    is_agent = any(
                        base.id in ["BaseAgent", "Agent"] if isinstance(base, ast.Name) else False
                        for base in node.bases
                    ) or "Agent" in node.name
                    
                    if is_agent:
                        # Extract docstring
                        docstring = ast.get_docstring(node) or "No description available"
                        
                        agents.append({
                            "name": node.name,
                            "file": agent_file.name,
                            "module": f"src.agents.{agent_file.stem}",
                            "description": docstring.split("\n")[0],  # First line only
                            "full_description": docstring,
                        })
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not parse {agent_file.name}: {e}")
    
    return agents


def run_interactive_agent(
    path: Path,
    agent_name: str,
    venv_path: Path,
) -> None:
    """
    Run an agent in interactive mode.
    
    Args:
        path: Project directory path
        agent_name: Name of the agent class to run
        venv_path: Path to virtual environment
    """
    import tempfile
    
    # Discover agents to validate the name
    agents = discover_agents(path)
    agent_info = None
    for agent in agents:
        if agent["name"] == agent_name:
            agent_info = agent
            break
    
    if not agent_info:
        console.print(f"[red]✗ Error:[/red] Agent '{agent_name}' not found.")
        console.print("\n[yellow]Available agents:[/yellow]")
        for agent in agents:
            console.print(f"  • {agent['name']}")
        raise typer.Exit(1)
    
    # Create a temporary runner script
    runner_script = f"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from src.agents.{agent_info['file'].replace('.py', '')} import {agent_name}

async def main():
    # Initialize agent with configuration from environment
    try:
        # Try to instantiate with common configuration patterns
        if "{agent_name}" == "VertexAIAgent":
            # VertexAIAgent requires project_id
            project_id = os.getenv("GOOGLE_PROJECT_ID")
            location = os.getenv("GOOGLE_LOCATION", "us-central1")
            model = os.getenv("VERTEX_AI_MODEL", "gemini-pro")
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if not project_id:
                print("Error: GOOGLE_PROJECT_ID not set in .env file")
                print("Please configure Vertex AI with: dva init vertex-ai")
                sys.exit(1)
            
            agent = {agent_name}(
                project_id=project_id,
                location=location,
                model=model,
                credentials_path=credentials_path if credentials_path else None
            )
        else:
            # Try to instantiate without arguments first
            agent = {agent_name}()
    except TypeError as e:
        print(f"Error: Could not instantiate {{agent.__class__.__name__ if 'agent' in locals() else '{agent_name}'}}")
        print(f"Details: {{e}}")
        print("\\nThis agent may require configuration. Check the agent's __init__ method.")
        sys.exit(1)
    
    # Check if agent has run_interactive method
    if hasattr(agent, 'run_interactive'):
        await agent.run_interactive()
    else:
        print(f"Error: {{agent.__class__.__name__}} does not support interactive mode.")
        print("Interactive agents must implement the 'run_interactive()' method.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n\\nInterrupted by user.")
    except Exception as e:
        print(f"Error: {{e}}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
"""
    
    # Write temporary script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=path) as f:
        f.write(runner_script)
        temp_script = Path(f.name)
    
    try:
        # Determine Python executable
        if venv_path.exists():
            python_exe = venv_path / "bin" / "python"
            if not python_exe.exists():
                python_exe = venv_path / "Scripts" / "python.exe"  # Windows
        else:
            python_exe = sys.executable
        
        # Run the agent with PYTHONPATH set
        import os
        env = os.environ.copy()
        env['PYTHONPATH'] = str(path)
        
        console.print()  # Add spacing
        
        result = subprocess.run(
            [str(python_exe), str(temp_script)],
            cwd=path,
            env=env,
            check=False
        )
        
        if result.returncode != 0 and result.returncode != 130:  # 130 is KeyboardInterrupt
            console.print(f"\n[red]✗ Process exited with code {result.returncode}[/red]")
            raise typer.Exit(result.returncode)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
    finally:
        # Clean up temporary file
        if temp_script.exists():
            temp_script.unlink()


def run_project_command(
    path: Path = Path("."),
    agent: Optional[str] = None,
    script: Optional[str] = None,
) -> None:
    """
    Run agents in a project.
    
    Examples:
        dva project run                          # Run main.py
        dva project run --agent KnowledgeGraphAgent  # Run specific agent
        dva project run --script examples/kg_agent_demo.py  # Run custom script
    """
    path = path.resolve()
    
    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)
    
    # Check for virtual environment
    venv_path = path / ".venv"
    if not venv_path.exists():
        console.print("[yellow]⚠ Warning:[/yellow] No virtual environment found.")
        console.print("[dim]Run: python -m venv .venv && source .venv/bin/activate && pip install -e '.'[/dim]")
    
    # Determine what to run
    if script:
        script_path = path / script
        if not script_path.exists():
            console.print(f"[red]✗ Error:[/red] Script {script} not found.")
            raise typer.Exit(1)
        run_file = script_path
        console.print(f"[cyan]🚀 Running script:[/cyan] {script}")
    elif agent:
        # Run interactive agent
        console.print(f"[cyan]🤖 Starting interactive agent:[/cyan] {agent}")
        return run_interactive_agent(path, agent, venv_path)
    else:
        run_file = path / "src" / "main.py"
        console.print("[cyan]🚀 Running:[/cyan] main.py")
    
    if not run_file.exists():
        console.print(f"[red]✗ Error:[/red] {run_file} not found.")
        raise typer.Exit(1)
    
    # Determine Python executable
    if venv_path.exists():
        python_exe = venv_path / "bin" / "python"
        if not python_exe.exists():
            python_exe = venv_path / "Scripts" / "python.exe"  # Windows
    else:
        python_exe = sys.executable
    
    # Run the script with PYTHONPATH set to project root
    import os
    env = os.environ.copy()
    env['PYTHONPATH'] = str(path)
    
    try:
        result = subprocess.run(
            [str(python_exe), str(run_file)],
            cwd=path,
            env=env,
            check=False
        )
        
        if result.returncode != 0:
            console.print(f"\n[red]✗ Process exited with code {result.returncode}[/red]")
            raise typer.Exit(result.returncode)
        else:
            console.print("\n[green]✓ Process completed successfully[/green]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]✗ Error running project:[/red] {e}")
        raise typer.Exit(1)


def list_agents_command(path: Path = Path(".")) -> None:
    """List all agents in a project."""
    path = path.resolve()
    
    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)
    
    agents_dir = path / "src" / "agents"
    if not agents_dir.exists():
        console.print(f"[red]✗ Error:[/red] No agents directory found at {agents_dir}")
        raise typer.Exit(1)
    
    console.print(Panel.fit(
        f"[bold cyan]Agents in Project[/bold cyan]\n"
        f"Location: {path.name}",
        border_style="cyan"
    ))
    
    agents = discover_agents(path)
    
    if not agents:
        console.print("\n[yellow]No agents found in this project.[/yellow]")
        console.print("[dim]Agents should be in src/agents/ and inherit from BaseAgent.[/dim]")
        return
    
    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("File", style="green")
    table.add_column("Description", style="white")
    
    for agent in agents:
        table.add_row(
            agent["name"],
            agent["file"],
            agent["description"][:60] + "..." if len(agent["description"]) > 60 else agent["description"]
        )
    
    console.print(table)
    console.print(f"\n[dim]Total agents: {len(agents)}[/dim]")
    console.print(f"[dim]Use '{CLI_NAME} project agent info <agent_name>' for more details[/dim]")


def agent_info_command(agent_name: str, path: Path = Path(".")) -> None:
    """Show detailed information about a specific agent."""
    path = path.resolve()
    
    if not path.exists():
        console.print(f"[red]✗ Error:[/red] Directory {path} does not exist.")
        raise typer.Exit(1)
    
    agents = discover_agents(path)
    
    # Find the agent
    agent = next((a for a in agents if a["name"] == agent_name), None)
    
    if not agent:
        console.print(f"[red]✗ Error:[/red] Agent '{agent_name}' not found.")
        console.print(f"\n[dim]Available agents:[/dim]")
        for a in agents:
            console.print(f"  • {a['name']}")
        raise typer.Exit(1)
    
    # Display agent info
    console.print(Panel.fit(
        f"[bold cyan]{agent['name']}[/bold cyan]\n\n"
        f"[bold]File:[/bold] {agent['file']}\n"
        f"[bold]Module:[/bold] {agent['module']}\n\n"
        f"[bold]Description:[/bold]\n{agent['full_description']}",
        title="Agent Information",
        border_style="cyan"
    ))
    
    # Show usage example
    console.print("\n[bold]Usage Example:[/bold]")
    console.print(f"[dim]from {agent['module']} import {agent['name']}[/dim]")
    console.print(f"[dim]agent = {agent['name']}()[/dim]")
    console.print(f"[dim]result = await agent.process({{...}})[/dim]")
