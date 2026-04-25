"""Workspace management for knowledge graph."""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class WorkspaceMetadata(BaseModel):
    """Metadata for a workspace."""
    
    name: str = Field(..., description="Workspace name")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    description: Optional[str] = Field(None, description="Workspace description")
    tags: List[str] = Field(default_factory=list, description="Workspace tags")
    document_count: int = Field(default=0, description="Number of documents")
    entity_count: int = Field(default=0, description="Number of entities")
    relation_count: int = Field(default=0, description="Number of relations")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    parent_workspace: Optional[str] = Field(None, description="Parent workspace name")
    snapshot_of: Optional[str] = Field(None, description="Snapshot source")
    environment: str = Field(default="development", description="Environment type")
    provider: str = Field(default="lightrag", description="KG provider (lightrag only)")


class WorkspaceManager:
    """
    Manage LightRAG workspaces.
    
    Note: Workspaces are only supported for LightRAG provider.
    Neo4j uses a single database instance.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize workspace manager.
        
        Args:
            base_dir: Base directory for all workspaces. 
                     Defaults to ~/.dva-agentic/lightrag-workspaces
        """
        if base_dir is None:
            base_dir = os.path.expanduser("~/.dva-agentic/lightrag-workspaces")
        
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / "workspaces.json"
        self._ensure_base_dir()
    
    def _ensure_base_dir(self) -> None:
        """Ensure base directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self) -> Dict[str, WorkspaceMetadata]:
        """
        Load workspace metadata from file.
        
        Returns:
            Dictionary of workspace name to metadata
        """
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            return {
                name: WorkspaceMetadata(**meta)
                for name, meta in data.get("workspaces", {}).items()
            }
        except (json.JSONDecodeError, ValueError) as e:
            # If metadata file is corrupted, return empty dict
            # and log warning
            import logging
            logging.warning(f"Failed to load workspace metadata: {e}")
            return {}
    
    def _save_metadata(self, metadata: Dict[str, WorkspaceMetadata]) -> None:
        """
        Save workspace metadata to file.
        
        Args:
            metadata: Dictionary of workspace metadata
        """
        data = {
            "workspaces": {
                name: meta.model_dump()
                for name, meta in metadata.items()
            },
            "version": "1.0.0",
            "last_modified": datetime.now(timezone.utc).isoformat()
        }
        
        # Write atomically by writing to temp file first
        temp_file = self.metadata_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Rename to actual file (atomic on POSIX systems)
        temp_file.replace(self.metadata_file)
    
    def _validate_workspace_name(self, name: str) -> None:
        """
        Validate workspace name.
        
        Args:
            name: Workspace name to validate
            
        Raises:
            ValueError: If name is invalid
        """
        if not name:
            raise ValueError("Workspace name cannot be empty")
        
        if len(name) > 100:
            raise ValueError("Workspace name too long (max 100 characters)")
        
        # Check for invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
        for char in invalid_chars:
            if char in name:
                raise ValueError(
                    f"Workspace name cannot contain '{char}'. "
                    f"Use alphanumeric characters, hyphens, and underscores only."
                )
        
        # Must start with alphanumeric
        if not name[0].isalnum():
            raise ValueError("Workspace name must start with alphanumeric character")
    
    def create_workspace(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        environment: str = "development",
        parent_workspace: Optional[str] = None
    ) -> WorkspaceMetadata:
        """
        Create a new workspace.
        
        Args:
            name: Workspace name
            description: Optional description
            tags: Optional list of tags
            environment: Environment type (development, evaluation, production)
            parent_workspace: Optional parent workspace to reference
            
        Returns:
            Created workspace metadata
            
        Raises:
            ValueError: If workspace already exists or name is invalid
        """
        self._validate_workspace_name(name)
        
        workspace_dir = self.base_dir / name
        
        if workspace_dir.exists():
            raise ValueError(f"Workspace '{name}' already exists")
        
        # Validate parent workspace if specified
        if parent_workspace:
            parent_dir = self.base_dir / parent_workspace
            if not parent_dir.exists():
                raise ValueError(f"Parent workspace '{parent_workspace}' does not exist")
        
        # Validate environment
        valid_environments = ["development", "evaluation", "production", "staging"]
        if environment not in valid_environments:
            raise ValueError(
                f"Invalid environment '{environment}'. "
                f"Must be one of: {', '.join(valid_environments)}"
            )
        
        # Create workspace directory
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata
        metadata = WorkspaceMetadata(
            name=name,
            created_at=datetime.now(timezone.utc).isoformat(),
            description=description,
            tags=tags or [],
            environment=environment,
            parent_workspace=parent_workspace,
            provider="lightrag"
        )
        
        # Save metadata
        all_metadata = self._load_metadata()
        all_metadata[name] = metadata
        self._save_metadata(all_metadata)
        
        return metadata
    
    def delete_workspace(self, name: str, force: bool = False) -> None:
        """
        Delete a workspace.
        
        Args:
            name: Workspace name to delete
            force: Force deletion of default workspace
            
        Raises:
            ValueError: If workspace doesn't exist or is default without force
        """
        if name == "default" and not force:
            raise ValueError(
                "Cannot delete default workspace. "
                "Use force=True to delete default workspace."
            )
        
        workspace_dir = self.base_dir / name
        
        if not workspace_dir.exists():
            raise ValueError(f"Workspace '{name}' does not exist")
        
        # Remove directory and all contents
        shutil.rmtree(workspace_dir)
        
        # Remove metadata
        all_metadata = self._load_metadata()
        if name in all_metadata:
            del all_metadata[name]
            self._save_metadata(all_metadata)
    
    def list_workspaces(self) -> List[WorkspaceMetadata]:
        """
        List all workspaces.
        
        Returns:
            List of workspace metadata
        """
        metadata = self._load_metadata()
        
        # Also check for directories without metadata (orphaned workspaces)
        if self.base_dir.exists():
            for dir_path in self.base_dir.iterdir():
                if dir_path.is_dir() and dir_path.name not in metadata:
                    # Skip special directories
                    if dir_path.name.startswith('.') or dir_path.name == 'workspaces.json':
                        continue
                    
                    # Create metadata for orphaned workspace
                    metadata[dir_path.name] = WorkspaceMetadata(
                        name=dir_path.name,
                        created_at=datetime.fromtimestamp(
                            dir_path.stat().st_ctime,
                            tz=timezone.utc
                        ).isoformat(),
                        description="(Orphaned workspace - no metadata)",
                        provider="lightrag"
                    )
        
        return list(metadata.values())
    
    def get_workspace(self, name: str) -> WorkspaceMetadata:
        """
        Get workspace metadata.
        
        Args:
            name: Workspace name
            
        Returns:
            Workspace metadata
            
        Raises:
            ValueError: If workspace doesn't exist
        """
        metadata = self._load_metadata()
        
        if name not in metadata:
            # Check if directory exists but no metadata
            workspace_dir = self.base_dir / name
            if workspace_dir.exists() and workspace_dir.is_dir():
                # Create metadata for orphaned workspace
                orphaned_meta = WorkspaceMetadata(
                    name=name,
                    created_at=datetime.fromtimestamp(
                        workspace_dir.stat().st_ctime,
                        tz=timezone.utc
                    ).isoformat(),
                    description="(Orphaned workspace - no metadata)",
                    provider="lightrag"
                )
                # Save it
                metadata[name] = orphaned_meta
                self._save_metadata(metadata)
                return orphaned_meta
            
            raise ValueError(f"Workspace '{name}' does not exist")
        
        return metadata[name]
    
    def workspace_exists(self, name: str) -> bool:
        """
        Check if workspace exists.
        
        Args:
            name: Workspace name
            
        Returns:
            True if workspace exists, False otherwise
        """
        workspace_dir = self.base_dir / name
        return workspace_dir.exists() and workspace_dir.is_dir()
    
    def update_workspace_stats(
        self,
        name: str,
        document_count: Optional[int] = None,
        entity_count: Optional[int] = None,
        relation_count: Optional[int] = None
    ) -> None:
        """
        Update workspace statistics.
        
        Args:
            name: Workspace name
            document_count: Optional document count
            entity_count: Optional entity count
            relation_count: Optional relation count
            
        Raises:
            ValueError: If workspace doesn't exist
        """
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
        
        workspace.last_updated = datetime.now(timezone.utc).isoformat()
        
        self._save_metadata(metadata)
    
    def update_workspace_metadata(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        environment: Optional[str] = None
    ) -> WorkspaceMetadata:
        """
        Update workspace metadata.
        
        Args:
            name: Workspace name
            description: Optional new description
            tags: Optional new tags
            environment: Optional new environment
            
        Returns:
            Updated workspace metadata
            
        Raises:
            ValueError: If workspace doesn't exist or environment is invalid
        """
        metadata = self._load_metadata()
        
        if name not in metadata:
            raise ValueError(f"Workspace '{name}' does not exist")
        
        workspace = metadata[name]
        
        if description is not None:
            workspace.description = description
        
        if tags is not None:
            workspace.tags = tags
        
        if environment is not None:
            valid_environments = ["development", "evaluation", "production", "staging"]
            if environment not in valid_environments:
                raise ValueError(
                    f"Invalid environment '{environment}'. "
                    f"Must be one of: {', '.join(valid_environments)}"
                )
            workspace.environment = environment
        
        workspace.last_updated = datetime.now(timezone.utc).isoformat()
        
        self._save_metadata(metadata)
        
        return workspace
    
    def clone_workspace(
        self,
        source: str,
        target: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> WorkspaceMetadata:
        """
        Clone a workspace.
        
        Args:
            source: Source workspace name
            target: Target workspace name
            description: Optional description for target
            tags: Optional tags for target
            
        Returns:
            Created target workspace metadata
            
        Raises:
            ValueError: If source doesn't exist or target already exists
        """
        self._validate_workspace_name(target)
        
        source_dir = self.base_dir / source
        target_dir = self.base_dir / target
        
        if not source_dir.exists():
            raise ValueError(f"Source workspace '{source}' does not exist")
        
        if target_dir.exists():
            raise ValueError(f"Target workspace '{target}' already exists")
        
        # Copy directory
        shutil.copytree(source_dir, target_dir)
        
        # Get source metadata
        source_meta = self.get_workspace(source)
        
        # Create target metadata
        target_meta = WorkspaceMetadata(
            name=target,
            created_at=datetime.now(timezone.utc).isoformat(),
            description=description or f"Clone of {source}",
            tags=tags or source_meta.tags.copy(),
            document_count=source_meta.document_count,
            entity_count=source_meta.entity_count,
            relation_count=source_meta.relation_count,
            environment=source_meta.environment,
            parent_workspace=source,
            snapshot_of=f"{source}@{datetime.now(timezone.utc).isoformat()}",
            provider="lightrag"
        )
        
        # Save metadata
        all_metadata = self._load_metadata()
        all_metadata[target] = target_meta
        self._save_metadata(all_metadata)
        
        return target_meta
    
    def get_workspace_path(self, name: str) -> Path:
        """
        Get the full path to a workspace directory.
        
        Args:
            name: Workspace name
            
        Returns:
            Path to workspace directory
        """
        return self.base_dir / name
