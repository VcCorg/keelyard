"""Registry manager for unified registry system."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from rich.console import Console
from rich.table import Table

from dva_agentic_cli.registry.base import BaseRegistry, RegistryConfig
from dva_agentic_cli.registry.agent_template import AgentTemplateRegistry
from dva_agentic_cli.registry.agent_tool import AgentToolRegistry

console = Console()


class RegistryManager:
    """Manages multiple registries of different types."""
    
    REGISTRY_TYPES: Dict[str, Type[BaseRegistry]] = {
        "agent-templates": AgentTemplateRegistry,
        "agent-tools": AgentToolRegistry,
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize registry manager.
        
        Args:
            config_path: Path to registry configuration file
        """
        self.config_path = config_path or Path.home() / ".dva" / "registries.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._registries: Dict[str, BaseRegistry] = {}
        self._config: Dict[str, Any] = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load registry configuration from file."""
        if self.config_path.exists():
            try:
                self._config = json.loads(self.config_path.read_text())
            except json.JSONDecodeError as e:
                console.print(f"[red]Error loading registry config: {e}[/red]")
                self._config = self._get_default_config()
        else:
            self._config = self._get_default_config()
            self._save_config()
    
    def _save_config(self) -> None:
        """Save registry configuration to file."""
        self.config_path.write_text(json.dumps(self._config, indent=2))
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default registry configuration."""
        return {
            "registries": {
                "agent-templates": {
                    "type": "agent-templates",
                    "url": "https://bitbucket.example.com/scm/~your-user/dva-agent-templates.git",
                    "path": str(Path.home() / ".dva" / "registries" / "dva-agent-templates"),
                    "enabled": True,
                    "default": True
                },
                "agent-tools": {
                    "type": "agent-tools", 
                    "url": "https://bitbucket.example.com/scm/~your-user/dva-agent-tools.git",
                    "path": str(Path.home() / ".dva" / "registries" / "dva-agent-tools"),
                    "enabled": True,
                    "default": True
                }
            },
            "default_agent_template_registry": "agent-templates",
            "default_agent_tool_registry": "agent-tools"
        }
    
    def _create_registry(self, name: str, config: RegistryConfig) -> BaseRegistry:
        """Create a registry instance from configuration."""
        registry_type = config.type
        if registry_type not in self.REGISTRY_TYPES:
            raise ValueError(f"Unknown registry type: {registry_type}")
        
        registry_class = self.REGISTRY_TYPES[registry_type]
        return registry_class(config)
    
    def get_registry(self, name: str) -> Optional[BaseRegistry]:
        """Get a registry by name."""
        if name not in self._registries:
            if name in self._config.get("registries", {}):
                config_data = self._config["registries"][name].copy()
                config_data["name"] = name
                reg_config = RegistryConfig(**config_data)
                self._registries[name] = self._create_registry(name, reg_config)
            else:
                return None
        
        return self._registries[name]
    
    def add_registry(self, name: str, config: RegistryConfig) -> None:
        """Add a new registry configuration."""
        if "registries" not in self._config:
            self._config["registries"] = {}
        
        self._config["registries"][name] = {
            "name": config.name,
            "type": config.type,
            "url": config.url,
            "path": config.path,
            "enabled": config.enabled,
            "default": config.default
        }
        
        # Update default registry flags
        if config.default:
            for other_name in self._config["registries"]:
                if other_name != name:
                    self._config["registries"][other_name]["default"] = False
        
        self._save_config()
        
        # Create registry instance
        self._registries[name] = self._create_registry(name, config)
    
    def remove_registry(self, name: str) -> bool:
        """Remove a registry configuration."""
        if "registries" not in self._config or name not in self._config["registries"]:
            return False
        
        del self._config["registries"][name]
        
        # Remove from cache
        if name in self._registries:
            del self._registries[name]
        
        self._save_config()
        return True
    
    def list_registries(self, registry_type: Optional[str] = None) -> List[RegistryConfig]:
        """List all registries, optionally filtered by type."""
        registries = []
        for name, config_data in self._config.get("registries", {}).items():
            # Ensure name is included in config data
            config_data["name"] = name
            config = RegistryConfig(**config_data)
            if registry_type is None or config.type == registry_type:
                registries.append(config)
        
        return registries
    
    def get_default_registry(self, registry_type: str) -> Optional[BaseRegistry]:
        """Get the default registry for a given type."""
        # Handle special case for agent-template -> agent_template (singular)
        if registry_type == 'agent-templates':
            default_key = "default_agent_template_registry"
        elif registry_type == 'agent-tools':
            default_key = "default_agent_tool_registry"
        else:
            default_key = f"default_{registry_type.replace('-', '_')}_registry"
        default_name = self._config.get(default_key)
        
        if default_name:
            return self.get_registry(default_name)
        
        # Fallback to first enabled registry of this type
        for config in self.list_registries(registry_type):
            if config.enabled:
                return self.get_registry(config.name)
        
        return None
    
    def show_registries(self, registry_type: Optional[str] = None) -> None:
        """Display registries in a table."""
        registries = self.list_registries(registry_type)
        
        if not registries:
            console.print("[yellow]No registries found[/yellow]")
            return
        
        table = Table(title=f"{'Agent Template' if registry_type == 'agent-templates' else 'Agent Tool' if registry_type == 'agent-tools' else 'All'} Registries")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Location", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Default", style="magenta")
        
        for config in registries:
            location = config.url if config.is_remote else config.path
            status = "Enabled" if config.enabled else "Disabled"
            default = "Yes" if config.default else "No"
            
            table.add_row(config.name, config.type, location, status, default)
        
        console.print(table)
    
    def ensure_registry_available(self, registry_type: str) -> Optional[BaseRegistry]:
        """Ensure at least one registry of the given type is available."""
        registry = self.get_default_registry(registry_type)
        
        if not registry:
            console.print(f"[red]No {registry_type} registry configured[/red]")
            console.print("[dim]Use 'dva agent-template registry add' or 'dva agent-tool registry add' to configure one[/dim]")
            return None
        
        if not registry.ensure_available():
            console.print(f"[red]Registry '{registry.config.name}' is unavailable[/red]")
            return None
        
        return registry
