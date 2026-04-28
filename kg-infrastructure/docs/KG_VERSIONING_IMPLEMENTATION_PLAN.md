# KG Versioning Implementation Plan

## Quick Reference: Recommended Solution

**Multi-Workspace Approach with Enhanced Metadata**

This provides the best balance of:
- Simple implementation
- Complete data isolation for evaluations
- Flexible metadata for filtering
- No query performance overhead

---

## Implementation Details

### 1. Configuration Changes

#### File: `src/dva_agentic_cli/kg/config.py`

```python
class KGConfig(BaseModel):
    """Knowledge graph configuration."""
    
    # ... existing fields ...
    
    # New workspace fields
    workspace: str = Field(
        default="default", 
        description="Active workspace name"
    )
    workspace_base_dir: str = Field(
        default="/data/lightrag",
        description="Base directory for all workspaces"
    )
    
    def get_workspace_dir(self) -> str:
        """Get the full path to the current workspace directory."""
        return f"{self.workspace_base_dir}/{self.workspace}"
    
    def list_workspaces(self) -> List[str]:
        """List all available workspaces."""
        base_path = Path(self.workspace_base_dir)
        if not base_path.exists():
            return ["default"]
        return [d.name for d in base_path.iterdir() if d.is_dir()]
```

### 2. Workspace Metadata Management

#### File: `src/dva_agentic_cli/kg/workspace.py` (NEW)

```python
"""Workspace management for knowledge graph."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel


class WorkspaceMetadata(BaseModel):
    """Metadata for a workspace."""
    name: str
    created_at: str
    description: Optional[str] = None
    tags: List[str] = []
    document_count: int = 0
    entity_count: int = 0
    relation_count: int = 0
    last_updated: Optional[str] = None
    parent_workspace: Optional[str] = None
    snapshot_of: Optional[str] = None
    environment: str = "development"  # development, evaluation, production


class WorkspaceManager:
    """Manage KG workspaces."""
    
    def __init__(self, base_dir: str = "/data/lightrag"):
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / "workspaces.json"
        self._ensure_base_dir()
    
    def _ensure_base_dir(self):
        """Ensure base directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self) -> Dict[str, WorkspaceMetadata]:
        """Load workspace metadata from file."""
        if not self.metadata_file.exists():
            return {}
        
        with open(self.metadata_file, 'r') as f:
            data = json.load(f)
        
        return {
            name: WorkspaceMetadata(**meta)
            for name, meta in data.get("workspaces", {}).items()
        }
    
    def _save_metadata(self, metadata: Dict[str, WorkspaceMetadata]):
        """Save workspace metadata to file."""
        data = {
            "workspaces": {
                name: meta.model_dump()
                for name, meta in metadata.items()
            }
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_workspace(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        environment: str = "development",
        parent_workspace: Optional[str] = None
    ) -> WorkspaceMetadata:
        """Create a new workspace."""
        workspace_dir = self.base_dir / name
        
        if workspace_dir.exists():
            raise ValueError(f"Workspace '{name}' already exists")
        
        # Create workspace directory
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata
        metadata = WorkspaceMetadata(
            name=name,
            created_at=datetime.utcnow().isoformat() + "Z",
            description=description,
            tags=tags or [],
            environment=environment,
            parent_workspace=parent_workspace
        )
        
        # Save metadata
        all_metadata = self._load_metadata()
        all_metadata[name] = metadata
        self._save_metadata(all_metadata)
        
        return metadata
    
    def delete_workspace(self, name: str, force: bool = False):
        """Delete a workspace."""
        if name == "default" and not force:
            raise ValueError("Cannot delete default workspace without force=True")
        
        workspace_dir = self.base_dir / name
        
        if not workspace_dir.exists():
            raise ValueError(f"Workspace '{name}' does not exist")
        
        # Remove directory
        import shutil
        shutil.rmtree(workspace_dir)
        
        # Remove metadata
        all_metadata = self._load_metadata()
        if name in all_metadata:
            del all_metadata[name]
            self._save_metadata(all_metadata)
    
    def list_workspaces(self) -> List[WorkspaceMetadata]:
        """List all workspaces."""
        metadata = self._load_metadata()
        
        # Also check for directories without metadata
        for dir_path in self.base_dir.iterdir():
            if dir_path.is_dir() and dir_path.name not in metadata:
                # Create metadata for orphaned workspace
                metadata[dir_path.name] = WorkspaceMetadata(
                    name=dir_path.name,
                    created_at=datetime.fromtimestamp(
                        dir_path.stat().st_ctime
                    ).isoformat() + "Z"
                )
        
        return list(metadata.values())
    
    def get_workspace(self, name: str) -> WorkspaceMetadata:
        """Get workspace metadata."""
        metadata = self._load_metadata()
        
        if name not in metadata:
            raise ValueError(f"Workspace '{name}' does not exist")
        
        return metadata[name]
    
    def update_workspace_stats(
        self,
        name: str,
        document_count: Optional[int] = None,
        entity_count: Optional[int] = None,
        relation_count: Optional[int] = None
    ):
        """Update workspace statistics."""
        metadata = self._load_metadata()
        
        if name not in metadata:
            raise ValueError(f"Workspace '{name}' does not exist")
        
        workspace = metadata[name]
        
        if document_count is not None:
            workspace.document_count = document_count
        if entity_count is not None:
            workspace.entity_count = entity_count
        if relation_count is not None:
            workspace.relation_count = relation_count
        
        workspace.last_updated = datetime.utcnow().isoformat() + "Z"
        
        self._save_metadata(metadata)
    
    def clone_workspace(
        self,
        source: str,
        target: str,
        description: Optional[str] = None
    ) -> WorkspaceMetadata:
        """Clone a workspace."""
        source_dir = self.base_dir / source
        target_dir = self.base_dir / target
        
        if not source_dir.exists():
            raise ValueError(f"Source workspace '{source}' does not exist")
        
        if target_dir.exists():
            raise ValueError(f"Target workspace '{target}' already exists")
        
        # Copy directory
        import shutil
        shutil.copytree(source_dir, target_dir)
        
        # Create metadata
        source_meta = self.get_workspace(source)
        target_meta = WorkspaceMetadata(
            name=target,
            created_at=datetime.utcnow().isoformat() + "Z",
            description=description or f"Clone of {source}",
            tags=source_meta.tags.copy(),
            document_count=source_meta.document_count,
            entity_count=source_meta.entity_count,
            relation_count=source_meta.relation_count,
            environment=source_meta.environment,
            parent_workspace=source,
            snapshot_of=f"{source}@{datetime.utcnow().isoformat()}"
        )
        
        all_metadata = self._load_metadata()
        all_metadata[target] = target_meta
        self._save_metadata(all_metadata)
        
        return target_meta
```

### 3. CLI Commands

#### File: `src/dva_agentic_cli/commands/kg_workspace.py` (NEW)

```python
"""Workspace management commands for agent kg."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from dva_agentic_cli.kg.config import KGConfig
from dva_agentic_cli.kg.workspace import WorkspaceManager

workspace_app = typer.Typer(
    help="Workspace management commands",
    rich_markup_mode=None
)
console = Console()


@workspace_app.command()
def create(
    name: str = typer.Argument(..., help="Workspace name"),
    description: str = typer.Option(None, "--description", "-d", help="Workspace description"),
    tags: str = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    environment: str = typer.Option("development", "--env", "-e", help="Environment (development, evaluation, production)"),
    parent: str = typer.Option(None, "--parent", "-p", help="Parent workspace to clone from"),
):
    """Create a new workspace."""
    config = KGConfig.load()
    manager = WorkspaceManager(config.workspace_base_dir)
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    
    try:
        if parent:
            # Clone from parent
            metadata = manager.clone_workspace(parent, name, description)
            console.print(f"[green]✓[/green] Workspace '{name}' created as clone of '{parent}'")
        else:
            # Create new workspace
            metadata = manager.create_workspace(
                name=name,
                description=description,
                tags=tag_list,
                environment=environment
            )
            console.print(f"[green]✓[/green] Workspace '{name}' created")
        
        # Show metadata
        panel = Panel(
            f"[cyan]Name:[/cyan] {metadata.name}\n"
            f"[cyan]Environment:[/cyan] {metadata.environment}\n"
            f"[cyan]Created:[/cyan] {metadata.created_at}\n"
            f"[cyan]Tags:[/cyan] {', '.join(metadata.tags) if metadata.tags else 'None'}",
            title="Workspace Details"
        )
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def list():
    """List all workspaces."""
    config = KGConfig.load()
    manager = WorkspaceManager(config.workspace_base_dir)
    
    try:
        workspaces = manager.list_workspaces()
        
        if not workspaces:
            console.print("[yellow]No workspaces found[/yellow]")
            return
        
        table = Table(title="Knowledge Graph Workspaces")
        table.add_column("Name", style="cyan")
        table.add_column("Environment", style="green")
        table.add_column("Documents", justify="right")
        table.add_column("Entities", justify="right")
        table.add_column("Created", style="dim")
        table.add_column("Active", justify="center")
        
        for ws in sorted(workspaces, key=lambda x: x.name):
            is_active = "✓" if ws.name == config.workspace else ""
            table.add_row(
                ws.name,
                ws.environment,
                str(ws.document_count),
                str(ws.entity_count),
                ws.created_at[:10],  # Just date
                is_active
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def switch(
    name: str = typer.Argument(..., help="Workspace name to switch to"),
):
    """Switch to a different workspace."""
    config = KGConfig.load()
    manager = WorkspaceManager(config.workspace_base_dir)
    
    try:
        # Verify workspace exists
        workspace = manager.get_workspace(name)
        
        # Update config
        config.workspace = name
        config.save()
        
        console.print(f"[green]✓[/green] Switched to workspace '{name}'")
        console.print(f"[dim]Environment: {workspace.environment}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def current():
    """Show current active workspace."""
    config = KGConfig.load()
    manager = WorkspaceManager(config.workspace_base_dir)
    
    try:
        workspace = manager.get_workspace(config.workspace)
        
        panel = Panel(
            f"[cyan]Name:[/cyan] {workspace.name}\n"
            f"[cyan]Environment:[/cyan] {workspace.environment}\n"
            f"[cyan]Description:[/cyan] {workspace.description or 'None'}\n"
            f"[cyan]Documents:[/cyan] {workspace.document_count}\n"
            f"[cyan]Entities:[/cyan] {workspace.entity_count}\n"
            f"[cyan]Relations:[/cyan] {workspace.relation_count}\n"
            f"[cyan]Created:[/cyan] {workspace.created_at}\n"
            f"[cyan]Last Updated:[/cyan] {workspace.last_updated or 'Never'}",
            title="Current Workspace"
        )
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)


@workspace_app.command()
def delete(
    name: str = typer.Argument(..., help="Workspace name to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a workspace."""
    config = KGConfig.load()
    manager = WorkspaceManager(config.workspace_base_dir)
    
    if name == config.workspace:
        console.print("[red]✗[/red] Cannot delete active workspace. Switch to another workspace first.")
        raise typer.Exit(1)
    
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete workspace '{name}'?")
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)
    
    try:
        manager.delete_workspace(name)
        console.print(f"[green]✓[/green] Workspace '{name}' deleted")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise typer.Exit(1)
```

### 4. Update Main KG Commands

#### File: `src/dva_agentic_cli/commands/kg.py`

```python
# Add workspace subcommand
from dva_agentic_cli.commands.kg_workspace import workspace_app
kg_app.add_typer(workspace_app, name="workspace", help="Workspace management")

# Update ingest command to use workspace
@kg_app.command()
def ingest(
    # ... existing parameters ...
    workspace: str = typer.Option(
        None,
        "--workspace", "-w",
        help="Target workspace (uses active workspace if not specified)"
    ),
):
    """Ingest data into knowledge graph."""
    config = KGConfig.load()
    
    # Use specified workspace or active workspace
    if workspace:
        # Temporarily switch workspace for this operation
        original_workspace = config.workspace
        config.workspace = workspace
        workspace_dir = config.get_workspace_dir()
        # ... ingestion logic ...
        config.workspace = original_workspace
    else:
        workspace_dir = config.get_workspace_dir()
        # ... ingestion logic ...
```

### 5. Update LightRAG Client

#### File: `src/dva_agentic_cli/kg/lightrag_client.py`

```python
class LightRAGClient:
    """Client for LightRAG API operations."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 30.0,
        working_dir: Optional[str] = None  # NEW: workspace-specific directory
    ):
        # ... existing code ...
        self.working_dir = working_dir
    
    def insert(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Insert with workspace-aware metadata."""
        if metadata is None:
            metadata = {}
        
        # Add workspace info to metadata if working_dir is set
        if self.working_dir:
            metadata["workspace"] = Path(self.working_dir).name
        
        # ... rest of insert logic ...
```

---

## Usage Examples

### Basic Workflow

```bash
# 1. Create workspaces
`agent kg workspace create production --env production --description "Production KG"
`agent kg workspace create eval-baseline --env evaluation --description "Baseline evaluation dataset"
`agent kg workspace create eval-experiment-1 --env evaluation --description "Experiment 1 dataset"

# 2. Ingest data into production
`agent kg workspace switch production
`agent kg ingest --source cwow-docs --segment census --version v1.0

# 3. Create evaluation datasets
`agent kg workspace switch eval-baseline
`agent kg ingest --source cwow-docs --segment census --version v1.0 --tags baseline

`agent kg workspace switch eval-experiment-1
`agent kg ingest --source cwow-docs-enhanced --segment census --version v1.1 --tags experiment

# 4. Query different workspaces
`agent kg query "How to identify active patients?" --workspace production
`agent kg query "How to identify active patients?" --workspace eval-baseline
`agent kg query "How to identify active patients?" --workspace eval-experiment-1

# 5. Compare results
`agent kg workspace list
`agent kg workspace current
```

### Evaluation Workflow

```bash
# Clone production for evaluation
`agent kg workspace create eval-test-1 --parent production --description "Test dataset 1"

# Run evaluation queries
for workspace in eval-baseline eval-experiment-1 eval-test-1; do
  echo "Testing workspace: $workspace"
  agent kg query "patient status query" --workspace $workspace --output results-$workspace.json
done

# Compare results
`agent kg eval compare results-*.json
```

---

## Migration Path

### For Existing Data

```bash
# 1. Current data is in /data/lightrag
# 2. Move to default workspace
mkdir -p /data/lightrag-new/default
mv /data/lightrag/* /data/lightrag-new/default/
mv /data/lightrag-new /data/lightrag

# 3. Update config
`agent kg workspace list  # Should show 'default'
```

---

## Testing Plan

1. **Unit Tests**: Test WorkspaceManager methods
2. **Integration Tests**: Test workspace switching during ingestion
3. **E2E Tests**: Full evaluation workflow
4. **Performance Tests**: Query performance across workspaces

---

## Next Steps

1. Review this implementation plan
2. Create GitHub issues for each component
3. Start with workspace management (WorkspaceManager class)
4. Add CLI commands
5. Update ingestion to use workspaces
6. Add evaluation features

Would you like me to start implementing any of these components?
