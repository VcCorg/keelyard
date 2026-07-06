"""Base classes for registry system."""

import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class RegistryConfig:
    """Configuration for a registry."""
    name: str
    type: str  # "skills", "agent-templates", "agent-tools"
    url: Optional[str] = None  # Git URL for remote registries
    path: Optional[str] = None  # Local path for local registries
    enabled: bool = True
    default: bool = False
    
    def __post_init__(self):
        if self.path:
            self.path = str(Path(self.path).expanduser())
    
    @property
    def is_remote(self) -> bool:
        """Check if this is a remote registry."""
        return self.url is not None
    
    @property
    def is_local(self) -> bool:
        """Check if this is a local registry."""
        return self.path is not None


@dataclass
class RegistryMetadata:
    """Base metadata for registry items."""
    name: str
    description: str
    version: str
    author: str
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    path: Optional[str] = None  # Path to the item within the registry


class BaseRegistry(ABC):
    """Base class for all registries."""
    
    def __init__(self, config: RegistryConfig):
        self.config = config
        self._metadata_cache: Optional[Dict[str, Any]] = None
    
    @property
    def registry_path(self) -> Path:
        """Get the local path to the registry."""
        if self.config.is_local:
            return Path(self.config.path)
        elif self.config.is_remote:
            # For remote registries, use cached local path
            cache_path = Path.home() / ".keel" / "registries" / self.config.name
            if not cache_path.exists():
                self._clone_remote_registry(cache_path)
            return cache_path
        else:
            raise ValueError(f"Registry {self.config.name} has no valid path or URL")
    
    def _clone_remote_registry(self, target_path: Path) -> None:
        """Clone a remote registry to local cache."""
        if not self.config.url:
            raise ValueError(f"Registry {self.config.name} has no URL for cloning")
        
        console.print(f"[dim]Cloning {self.config.type} registry from {self.config.url}...[/dim]")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", self.config.url, str(target_path)],
                capture_output=True, 
                check=True,
                text=True
            )
            console.print(f"[green]Cloned {self.config.type} registry to {target_path}[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to clone registry: {e.stderr}[/red]")
            raise
    
    def _load_registry_metadata(self) -> Dict[str, Any]:
        """Load the registry metadata (registry.json)."""
        if self._metadata_cache is not None:
            return self._metadata_cache
        
        registry_file = self.registry_path / "registry.json"
        if not registry_file.exists():
            raise FileNotFoundError(f"Registry file not found: {registry_file}")
        
        try:
            self._metadata_cache = json.loads(registry_file.read_text())
            return self._metadata_cache
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in registry file: {e}")
    
    def _refresh_remote_registry(self) -> None:
        """Refresh a remote registry by pulling latest changes."""
        if not self.config.is_remote:
            return
        
        try:
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.registry_path,
                capture_output=True,
                check=True,
                text=True
            )
            self._metadata_cache = None  # Clear cache
            console.print(f"[green]Updated {self.config.type} registry[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Warning: Failed to update registry: {e.stderr}[/yellow]")
    
    @abstractmethod
    def list_items(self, **filters) -> List[RegistryMetadata]:
        """List items in the registry with optional filters."""
        pass
    
    @abstractmethod
    def get_item(self, name: str) -> Optional[RegistryMetadata]:
        """Get a specific item by name."""
        pass
    
    @abstractmethod
    def install_item(self, name: str, target_path: Path, version: Optional[str] = None) -> bool:
        """Install an item to a target path."""
        pass
    
    @abstractmethod
    def validate_registry(self) -> bool:
        """Validate that the registry is properly structured."""
        pass
    
    def ensure_available(self) -> bool:
        """Ensure the registry is available and up-to-date."""
        try:
            # Refresh remote registries
            if self.config.is_remote:
                self._refresh_remote_registry()
            
            # Validate structure
            return self.validate_registry()
        except Exception as e:
            console.print(f"[red]Registry {self.config.name} unavailable: {e}[/red]")
            return False
