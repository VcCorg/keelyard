"""Agent tool registry implementation."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from dva_agentic_cli.registry.base import BaseRegistry, RegistryConfig, RegistryMetadata

console = Console()


class AgentToolMetadata(RegistryMetadata):
    """Metadata for agent tools."""
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str,
        author: str,
        created_at: str,
        updated_at: str,
        entry_point: str,
        class_name: str,
        tags: List[str] = None,
        category: Optional[str] = None,
        dependencies: List[str] = None,
        path: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            description=description,
            version=version,
            author=author,
            created_at=created_at,
            updated_at=updated_at,
            tags=tags or [],
            category=category,
            dependencies=dependencies or [],
            path=path
        )
        self.entry_point = entry_point
        self.class_name = class_name


class AgentToolRegistry(BaseRegistry):
    """Registry for agent tools."""
    
    def list_items(self, category: Optional[str] = None, tag: Optional[str] = None) -> List[AgentToolMetadata]:
        """List agent tools with optional filters."""
        try:
            metadata = self._load_registry_metadata()
            tools = []
            
            for name, tool_data in metadata.get("tools", {}).items():
                # Apply filters
                if category and tool_data.get("category") != category:
                    continue
                if tag and tag not in tool_data.get("tags", []):
                    continue
                
                tool_meta = AgentToolMetadata(
                    name=name,
                    description=tool_data.get("description", ""),
                    version=tool_data.get("version", "1.0.0"),
                    author=tool_data.get("author", "Unknown"),
                    created_at=tool_data.get("created_at", ""),
                    updated_at=tool_data.get("updated_at", ""),
                    entry_point=tool_data.get("entry_point", "main.py"),
                    class_name=tool_data.get("class_name", "Tool"),
                    tags=tool_data.get("tags", []),
                    category=tool_data.get("category"),
                    dependencies=tool_data.get("dependencies", []),
                    path=tool_data.get("path"),
                )
                tools.append(tool_meta)
            
            return tools
        except Exception as e:
            console.print(f"[red]Error listing tools: {e}[/red]")
            return []
    
    def get_item(self, name: str) -> Optional[AgentToolMetadata]:
        """Get a specific agent tool by name."""
        try:
            metadata = self._load_registry_metadata()
            tools = metadata.get("tools", {})
            
            if name not in tools:
                return None
            
            tool_data = tools[name]
            return AgentToolMetadata(
                name=name,
                description=tool_data.get("description", ""),
                version=tool_data.get("version", "1.0.0"),
                author=tool_data.get("author", "Unknown"),
                created_at=tool_data.get("created_at", ""),
                updated_at=tool_data.get("updated_at", ""),
                entry_point=tool_data.get("entry_point", "main.py"),
                class_name=tool_data.get("class_name", "Tool"),
                tags=tool_data.get("tags", []),
                category=tool_data.get("category"),
                dependencies=tool_data.get("dependencies", []),
                path=tool_data.get("path"),
            )
        except Exception as e:
            console.print(f"[red]Error getting tool '{name}': {e}[/red]")
            return None
    
    def install_item(self, name: str, target_path: Path, version: Optional[str] = None) -> bool:
        """Install an agent tool to the target path."""
        try:
            tool_meta = self.get_item(name)
            if not tool_meta:
                console.print(f"[red]Tool '{name}' not found[/red]")
                return False
            
            # Check version if specified
            if version and tool_meta.version != version:
                console.print(f"[red]Tool '{name}' version mismatch. Requested: {version}, Available: {tool_meta.version}[/red]")
                return False
            
            # Get source path
            if tool_meta.path:
                source_path = self.registry_path / tool_meta.path
            else:
                source_path = self.registry_path / "tools" / (tool_meta.category or "misc") / name
            
            if not source_path.exists():
                console.print(f"[red]Tool source path not found: {source_path}[/red]")
                return False
            
            # Create target directory
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Copy tool to target
            console.print(f"[cyan]Installing tool '{name}' to {target_path}...[/cyan]")
            
            # If target_path is a directory, copy the tool into it
            if target_path.is_dir():
                tool_target = target_path / name
                if tool_target.exists():
                    if tool_target.is_dir():
                        shutil.rmtree(tool_target)
                    else:
                        tool_target.unlink()
                shutil.copytree(source_path, tool_target)
            else:
                # Target path is a file path, copy parent directory
                shutil.copytree(source_path, target_path.parent)
            
            console.print(f"[green]Tool '{name}' installed successfully[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error installing tool '{name}': {e}[/red]")
            return False
    
    def validate_registry(self) -> bool:
        """Validate that the registry is properly structured."""
        registry_file = self.registry_path / "registry.json"
        if not registry_file.exists():
            console.print(f"[red]Registry file not found: {registry_file}[/red]")
            return False
        
        try:
            metadata = self._load_registry_metadata()
            
            # Check required structure
            if "tools" not in metadata:
                console.print(f"[red]Invalid registry structure: missing 'tools' section[/red]")
                return False
            
            # Validate each tool
            tools_dir = self.registry_path / "tools"
            if tools_dir.exists():
                for name, tool_data in metadata["tools"].items():
                    tool_path = None
                    if tool_data.get("path"):
                        tool_path = self.registry_path / tool_data["path"]
                    else:
                        category = tool_data.get("category")
                        if category:
                            tool_path = tools_dir / category / name
                    
                    if tool_path and not tool_path.exists():
                        console.print(f"[yellow]Warning: Tool path not found: {tool_path}[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error validating registry: {e}[/red]")
            return False
    
    def get_categories(self) -> List[str]:
        """Get available categories."""
        try:
            metadata = self._load_registry_metadata()
            categories = set()
            
            for tool_data in metadata.get("tools", {}).values():
                if tool_data.get("category"):
                    categories.add(tool_data["category"])
            
            return sorted(list(categories))
        except Exception:
            return []
    
    def get_dependencies(self, tool_name: str) -> List[str]:
        """Get dependencies for a specific tool."""
        tool_meta = self.get_item(tool_name)
        if tool_meta:
            return tool_meta.dependencies
        return []
