"""Agent template registry implementation."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from dva_agentic_cli.registry.base import BaseRegistry, RegistryConfig, RegistryMetadata

console = Console()


class AgentTemplateMetadata(RegistryMetadata):
    """Metadata for agent templates."""
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str,
        author: str,
        created_at: str,
        updated_at: str,
        framework: str,
        use_case: str,
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
        self.framework = framework
        self.use_case = use_case


class AgentTemplateRegistry(BaseRegistry):
    """Registry for agent templates."""
    
    def list_items(self, framework: Optional[str] = None, use_case: Optional[str] = None, category: Optional[str] = None, tag: Optional[str] = None) -> List[AgentTemplateMetadata]:
        """List agent templates with optional filters."""
        try:
            metadata = self._load_registry_metadata()
            templates = []
            
            for name, template_data in metadata.get("templates", {}).items():
                # Apply filters
                if framework and template_data.get("framework") != framework:
                    continue
                if use_case and template_data.get("use_case") != use_case:
                    continue
                if category and template_data.get("category") != category:
                    continue
                if tag and tag not in template_data.get("tags", []):
                    continue
                
                template_meta = AgentTemplateMetadata(
                    name=name,
                    description=template_data.get("description", ""),
                    version=template_data.get("version", "1.0.0"),
                    author=template_data.get("author", "Unknown"),
                    created_at=template_data.get("created_at", ""),
                    updated_at=template_data.get("updated_at", ""),
                    framework=template_data.get("framework", ""),
                    use_case=template_data.get("use_case", ""),
                    tags=template_data.get("tags", []),
                    category=template_data.get("category"),
                    dependencies=template_data.get("dependencies", []),
                    path=template_data.get("path"),
                )
                templates.append(template_meta)
            
            return templates
        except Exception as e:
            console.print(f"[red]Error listing templates: {e}[/red]")
            return []
    
    def get_item(self, name: str) -> Optional[AgentTemplateMetadata]:
        """Get a specific agent template by name."""
        try:
            metadata = self._load_registry_metadata()
            templates = metadata.get("templates", {})
            
            if name not in templates:
                return None
            
            template_data = templates[name]
            return AgentTemplateMetadata(
                name=name,
                description=template_data.get("description", ""),
                version=template_data.get("version", "1.0.0"),
                author=template_data.get("author", "Unknown"),
                created_at=template_data.get("created_at", ""),
                updated_at=template_data.get("updated_at", ""),
                framework=template_data.get("framework", ""),
                use_case=template_data.get("use_case", ""),
                tags=template_data.get("tags", []),
                category=template_data.get("category"),
                dependencies=template_data.get("dependencies", []),
                path=template_data.get("path"),
            )
        except Exception as e:
            console.print(f"[red]Error getting template '{name}': {e}[/red]")
            return None
    
    def install_item(self, name: str, target_path: Path, version: Optional[str] = None) -> bool:
        """Install an agent template to the target path."""
        try:
            template_meta = self.get_item(name)
            if not template_meta:
                console.print(f"[red]Template '{name}' not found[/red]")
                return False
            
            # Check version if specified
            if version and template_meta.version != version:
                console.print(f"[red]Template '{name}' version mismatch. Requested: {version}, Available: {template_meta.version}[/red]")
                return False
            
            # Get source path
            if template_meta.path:
                source_path = self.registry_path / template_meta.path
            else:
                source_path = self.registry_path / "templates" / template_meta.framework / name
            
            if not source_path.exists():
                console.print(f"[red]Template source path not found: {source_path}[/red]")
                return False
            
            # Copy template to target
            console.print(f"[cyan]Installing template '{name}' to {target_path}...[/cyan]")
            
            if target_path.exists():
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
            
            shutil.copytree(source_path, target_path)
            
            # Update project name in pyproject.toml if it exists
            pyproject_path = target_path / "pyproject.toml"
            if pyproject_path.exists():
                content = pyproject_path.read_text()
                content = content.replace('name = "agent-project"', f'name = "{target_path.name}"')
                pyproject_path.write_text(content)
            
            console.print(f"[green]Template '{name}' installed successfully[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error installing template '{name}': {e}[/red]")
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
            if "templates" not in metadata:
                console.print(f"[red]Invalid registry structure: missing 'templates' section[/red]")
                return False
            
            # Validate each template
            templates_dir = self.registry_path / "templates"
            if templates_dir.exists():
                for name, template_data in metadata["templates"].items():
                    template_path = None
                    if template_data.get("path"):
                        template_path = self.registry_path / template_data["path"]
                    else:
                        framework = template_data.get("framework")
                        if framework:
                            template_path = templates_dir / framework / name
                    
                    if template_path and not template_path.exists():
                        console.print(f"[yellow]Warning: Template path not found: {template_path}[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error validating registry: {e}[/red]")
            return False
    
    def get_categories(self) -> List[str]:
        """Get available categories."""
        try:
            metadata = self._load_registry_metadata()
            categories = set()
            
            for template_data in metadata.get("templates", {}).values():
                if template_data.get("category"):
                    categories.add(template_data["category"])
            
            return sorted(list(categories))
        except Exception:
            return []
    
    def get_frameworks(self) -> List[str]:
        """Get available frameworks."""
        try:
            metadata = self._load_registry_metadata()
            frameworks = set()
            
            for template_data in metadata.get("templates", {}).values():
                if template_data.get("framework"):
                    frameworks.add(template_data["framework"])
            
            return sorted(list(frameworks))
        except Exception:
            return []
    
    def get_use_cases(self) -> List[str]:
        """Get available use cases."""
        try:
            metadata = self._load_registry_metadata()
            use_cases = set()
            
            for template_data in metadata.get("templates", {}).values():
                if template_data.get("use_case"):
                    use_cases.add(template_data["use_case"])
            
            return sorted(list(use_cases))
        except Exception:
            return []
