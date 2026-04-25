"""Tests for workspace management."""

import json
import pytest
import shutil
from pathlib import Path
from datetime import datetime, timezone

from agentic_cli.kg.workspace import WorkspaceManager, WorkspaceMetadata
from agentic_cli.kg.config import KGConfig


@pytest.fixture
def temp_workspace_dir(tmp_path):
    """Create a temporary workspace directory."""
    workspace_dir = tmp_path / "test_workspaces"
    workspace_dir.mkdir()
    yield workspace_dir
    # Cleanup
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)


@pytest.fixture
def workspace_manager(temp_workspace_dir):
    """Create a workspace manager with temp directory."""
    return WorkspaceManager(str(temp_workspace_dir))


class TestWorkspaceMetadata:
    """Test WorkspaceMetadata model."""
    
    def test_create_metadata(self):
        """Test creating workspace metadata."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            created_at=datetime.now(timezone.utc).isoformat(),
            description="Test workspace",
            tags=["test", "demo"],
            environment="development"
        )
        
        assert metadata.name == "test-workspace"
        assert metadata.description == "Test workspace"
        assert metadata.tags == ["test", "demo"]
        assert metadata.environment == "development"
        assert metadata.document_count == 0
        assert metadata.entity_count == 0
        assert metadata.provider == "lightrag"
    
    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = WorkspaceMetadata(
            name="minimal",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        assert metadata.description is None
        assert metadata.tags == []
        assert metadata.document_count == 0
        assert metadata.environment == "development"
        assert metadata.provider == "lightrag"


class TestWorkspaceManager:
    """Test WorkspaceManager class."""
    
    def test_init(self, temp_workspace_dir):
        """Test manager initialization."""
        manager = WorkspaceManager(str(temp_workspace_dir))
        
        assert manager.base_dir == temp_workspace_dir
        assert manager.metadata_file == temp_workspace_dir / "workspaces.json"
        assert temp_workspace_dir.exists()
    
    def test_create_workspace(self, workspace_manager, temp_workspace_dir):
        """Test creating a workspace."""
        metadata = workspace_manager.create_workspace(
            name="test-workspace",
            description="Test workspace",
            tags=["test"],
            environment="development"
        )
        
        assert metadata.name == "test-workspace"
        assert metadata.description == "Test workspace"
        assert metadata.tags == ["test"]
        assert metadata.environment == "development"
        
        # Check directory was created
        workspace_dir = temp_workspace_dir / "test-workspace"
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()
        
        # Check metadata was saved
        assert workspace_manager.metadata_file.exists()
    
    def test_create_duplicate_workspace(self, workspace_manager):
        """Test creating duplicate workspace fails."""
        workspace_manager.create_workspace("test-workspace")
        
        with pytest.raises(ValueError, match="already exists"):
            workspace_manager.create_workspace("test-workspace")
    
    def test_validate_workspace_name(self, workspace_manager):
        """Test workspace name validation."""
        # Empty name
        with pytest.raises(ValueError, match="cannot be empty"):
            workspace_manager._validate_workspace_name("")
        
        # Too long
        with pytest.raises(ValueError, match="too long"):
            workspace_manager._validate_workspace_name("a" * 101)
        
        # Invalid characters
        invalid_names = ["test/workspace", "test\\workspace", "test:workspace", 
                        "test workspace", "test*workspace"]
        for name in invalid_names:
            with pytest.raises(ValueError, match="cannot contain"):
                workspace_manager._validate_workspace_name(name)
        
        # Must start with alphanumeric
        with pytest.raises(ValueError, match="must start with alphanumeric"):
            workspace_manager._validate_workspace_name("-test")
    
    def test_list_workspaces(self, workspace_manager):
        """Test listing workspaces."""
        # Create multiple workspaces
        workspace_manager.create_workspace("workspace-1")
        workspace_manager.create_workspace("workspace-2")
        workspace_manager.create_workspace("workspace-3")
        
        workspaces = workspace_manager.list_workspaces()
        
        assert len(workspaces) == 3
        names = [ws.name for ws in workspaces]
        assert "workspace-1" in names
        assert "workspace-2" in names
        assert "workspace-3" in names
    
    def test_list_empty_workspaces(self, workspace_manager):
        """Test listing when no workspaces exist."""
        workspaces = workspace_manager.list_workspaces()
        assert workspaces == []
    
    def test_get_workspace(self, workspace_manager):
        """Test getting workspace metadata."""
        workspace_manager.create_workspace("test-workspace", description="Test")
        
        metadata = workspace_manager.get_workspace("test-workspace")
        
        assert metadata.name == "test-workspace"
        assert metadata.description == "Test"
    
    def test_get_nonexistent_workspace(self, workspace_manager):
        """Test getting nonexistent workspace fails."""
        with pytest.raises(ValueError, match="does not exist"):
            workspace_manager.get_workspace("nonexistent")
    
    def test_workspace_exists(self, workspace_manager):
        """Test checking workspace existence."""
        assert not workspace_manager.workspace_exists("test-workspace")
        
        workspace_manager.create_workspace("test-workspace")
        
        assert workspace_manager.workspace_exists("test-workspace")
    
    def test_delete_workspace(self, workspace_manager, temp_workspace_dir):
        """Test deleting a workspace."""
        workspace_manager.create_workspace("test-workspace")
        
        workspace_dir = temp_workspace_dir / "test-workspace"
        assert workspace_dir.exists()
        
        workspace_manager.delete_workspace("test-workspace")
        
        assert not workspace_dir.exists()
        assert not workspace_manager.workspace_exists("test-workspace")
    
    def test_delete_nonexistent_workspace(self, workspace_manager):
        """Test deleting nonexistent workspace fails."""
        with pytest.raises(ValueError, match="does not exist"):
            workspace_manager.delete_workspace("nonexistent")
    
    def test_delete_default_workspace(self, workspace_manager):
        """Test deleting default workspace requires force."""
        workspace_manager.create_workspace("default")
        
        with pytest.raises(ValueError, match="Cannot delete default workspace"):
            workspace_manager.delete_workspace("default")
        
        # Should work with force
        workspace_manager.delete_workspace("default", force=True)
        assert not workspace_manager.workspace_exists("default")
    
    def test_update_workspace_stats(self, workspace_manager):
        """Test updating workspace statistics."""
        workspace_manager.create_workspace("test-workspace")
        
        workspace_manager.update_workspace_stats(
            "test-workspace",
            document_count=10,
            entity_count=50,
            relation_count=100
        )
        
        metadata = workspace_manager.get_workspace("test-workspace")
        assert metadata.document_count == 10
        assert metadata.entity_count == 50
        assert metadata.relation_count == 100
        assert metadata.last_updated is not None
    
    def test_update_workspace_metadata(self, workspace_manager):
        """Test updating workspace metadata."""
        workspace_manager.create_workspace("test-workspace")
        
        updated = workspace_manager.update_workspace_metadata(
            "test-workspace",
            description="Updated description",
            tags=["updated", "test"],
            environment="production"
        )
        
        assert updated.description == "Updated description"
        assert updated.tags == ["updated", "test"]
        assert updated.environment == "production"
        assert updated.last_updated is not None
    
    def test_clone_workspace(self, workspace_manager, temp_workspace_dir):
        """Test cloning a workspace."""
        # Create source workspace with some content
        workspace_manager.create_workspace("source", description="Source workspace")
        source_dir = temp_workspace_dir / "source"
        test_file = source_dir / "test.txt"
        test_file.write_text("test content")
        
        # Update stats
        workspace_manager.update_workspace_stats("source", document_count=5)
        
        # Clone workspace
        cloned = workspace_manager.clone_workspace(
            "source",
            "target",
            description="Cloned workspace"
        )
        
        assert cloned.name == "target"
        assert cloned.description == "Cloned workspace"
        assert cloned.parent_workspace == "source"
        assert cloned.document_count == 5
        assert cloned.snapshot_of is not None
        
        # Check directory was cloned
        target_dir = temp_workspace_dir / "target"
        assert target_dir.exists()
        assert (target_dir / "test.txt").exists()
        assert (target_dir / "test.txt").read_text() == "test content"
    
    def test_clone_nonexistent_source(self, workspace_manager):
        """Test cloning nonexistent source fails."""
        with pytest.raises(ValueError, match="does not exist"):
            workspace_manager.clone_workspace("nonexistent", "target")
    
    def test_clone_to_existing_target(self, workspace_manager):
        """Test cloning to existing target fails."""
        workspace_manager.create_workspace("source")
        workspace_manager.create_workspace("target")
        
        with pytest.raises(ValueError, match="already exists"):
            workspace_manager.clone_workspace("source", "target")
    
    def test_get_workspace_path(self, workspace_manager, temp_workspace_dir):
        """Test getting workspace path."""
        path = workspace_manager.get_workspace_path("test-workspace")
        
        assert path == temp_workspace_dir / "test-workspace"
        assert isinstance(path, Path)
    
    def test_orphaned_workspace(self, workspace_manager, temp_workspace_dir):
        """Test handling orphaned workspace (directory without metadata)."""
        # Create directory manually without metadata
        orphaned_dir = temp_workspace_dir / "orphaned"
        orphaned_dir.mkdir()
        
        # Should be detected in list
        workspaces = workspace_manager.list_workspaces()
        names = [ws.name for ws in workspaces]
        assert "orphaned" in names
        
        # Should be able to get it (creates metadata)
        metadata = workspace_manager.get_workspace("orphaned")
        assert metadata.name == "orphaned"
        assert "(Orphaned workspace" in metadata.description
    
    def test_invalid_environment(self, workspace_manager):
        """Test invalid environment fails."""
        with pytest.raises(ValueError, match="Invalid environment"):
            workspace_manager.create_workspace(
                "test-workspace",
                environment="invalid"
            )
    
    def test_metadata_persistence(self, workspace_manager, temp_workspace_dir):
        """Test metadata persists across manager instances."""
        # Create workspace
        workspace_manager.create_workspace(
            "test-workspace",
            description="Test",
            tags=["test"]
        )
        
        # Create new manager instance
        new_manager = WorkspaceManager(str(temp_workspace_dir))
        
        # Should load existing metadata
        metadata = new_manager.get_workspace("test-workspace")
        assert metadata.name == "test-workspace"
        assert metadata.description == "Test"
        assert metadata.tags == ["test"]


class TestKGConfigWorkspace:
    """Test KGConfig workspace methods."""
    
    def test_get_workspace_dir_lightrag(self):
        """Test getting workspace directory for LightRAG."""
        import os
        default_dir = os.path.expanduser("~/.dva-agentic/lightrag-workspaces")
        
        config = KGConfig(
            provider="lightrag",
            workspace="test-workspace",
            workspace_base_dir=default_dir
        )
        
        assert config.get_workspace_dir() == f"{default_dir}/test-workspace"
    
    def test_get_workspace_dir_neo4j(self):
        """Test getting workspace directory for Neo4j (not supported)."""
        config = KGConfig(
            provider="neo4j",
            workspace_base_dir="/data/lightrag"
        )
        
        # Should return base dir for Neo4j
        assert config.get_workspace_dir() == "/data/lightrag"
    
    def test_supports_workspaces(self):
        """Test checking workspace support."""
        lightrag_config = KGConfig(provider="lightrag")
        assert lightrag_config.supports_workspaces() is True
        
        neo4j_config = KGConfig(provider="neo4j")
        assert neo4j_config.supports_workspaces() is False
