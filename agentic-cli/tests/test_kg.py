"""Tests for knowledge graph module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from agentic_cli.kg.config import KGConfig
from agentic_cli.commands.kg import load_data_config, resolve_data_source


class TestKGConfig:
    """Tests for KGConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = KGConfig()
        
        assert config.provider == "neo4j"
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.neo4j_username == "neo4j"
        assert config.embeddings_provider == "vertex-ai"
    
    def test_is_neo4j_configured(self):
        """Test Neo4j configuration check."""
        # Not configured (missing password)
        config = KGConfig()
        assert not config.is_neo4j_configured()
        
        # Configured
        config.neo4j_password = "password"
        assert config.is_neo4j_configured()
    
    def test_is_vertex_ai_configured(self):
        """Test Vertex AI configuration check."""
        # Not configured
        config = KGConfig()
        assert not config.is_vertex_ai_configured()
        
        # Configured
        config.google_project_id = "test-project"
        assert config.is_vertex_ai_configured()
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading configuration."""
        # Create config
        config = KGConfig(
            provider="neo4j",
            neo4j_uri="bolt://test:7687",
            neo4j_username="test_user",
            neo4j_password="test_pass",
            google_project_id="test-project",
        )
        
        # Mock config path
        config_file = tmp_path / "kg-config.json"
        
        with patch.object(KGConfig, "get_config_path", return_value=config_file):
            # Save
            config.save()
            
            # Verify file exists
            assert config_file.exists()
            
            # Load
            loaded_config = KGConfig.load()
            
            assert loaded_config.provider == "neo4j"
            assert loaded_config.neo4j_uri == "bolt://test:7687"
            assert loaded_config.neo4j_username == "test_user"
            assert loaded_config.neo4j_password == "test_pass"


class TestParsers:
    """Tests for file parsers."""
    
    def test_parse_text(self, tmp_path):
        """Test text file parsing."""
        from agentic_cli.kg.parsers import parse_text
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is a test document.")
        
        # Parse
        documents = parse_text(str(test_file))
        
        assert len(documents) == 1
        assert documents[0]["title"] == "test"
        assert documents[0]["content"] == "This is a test document."
        assert documents[0]["metadata"]["format"] == "text"
    
    def test_parse_json(self, tmp_path):
        """Test JSON file parsing."""
        from agentic_cli.kg.parsers import parse_json
        
        # Create test file
        test_file = tmp_path / "test.json"
        test_data = {"name": "Test", "value": 123}
        test_file.write_text(json.dumps(test_data))
        
        # Parse
        documents = parse_json(str(test_file))
        
        assert len(documents) == 1
        assert documents[0]["title"] == "test"
        assert "Test" in documents[0]["content"]
        assert documents[0]["metadata"]["format"] == "json"
    
    def test_parse_csv(self, tmp_path):
        """Test CSV file parsing."""
        from agentic_cli.kg.parsers import parse_csv
        
        # Create test file
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,age\nJohn,30\nJane,25")
        
        # Parse
        documents = parse_csv(str(test_file))
        
        assert len(documents) == 2
        assert "John" in documents[0]["content"]
        assert "Jane" in documents[1]["content"]
        assert documents[0]["metadata"]["format"] == "csv"


class TestToolGenerator:
    """Tests for tool generator."""
    
    def test_generate_tool_with_search(self):
        """Test generating tool with search operation."""
        from agentic_cli.kg.tool_generator import generate_tool
        
        code = generate_tool(name="test_tool", operations=["search"])
        
        assert "class TestToolTool:" in code
        assert "def search(" in code
        assert "search_graph" in code
    
    def test_generate_tool_with_query(self):
        """Test generating tool with query operation."""
        from agentic_cli.kg.tool_generator import generate_tool
        
        code = generate_tool(name="test_tool", operations=["query"])
        
        assert "class TestToolTool:" in code
        assert "def query(" in code
        assert "execute_query" in code
    
    def test_generate_tool_with_traverse(self):
        """Test generating tool with traverse operation."""
        from agentic_cli.kg.tool_generator import generate_tool
        
        code = generate_tool(name="test_tool", operations=["traverse"])
        
        assert "class TestToolTool:" in code
        assert "def traverse(" in code
    
    def test_generate_tool_with_multiple_operations(self):
        """Test generating tool with multiple operations."""
        from agentic_cli.kg.tool_generator import generate_tool
        
        code = generate_tool(
            name="multi_tool",
            operations=["search", "query", "traverse"],
        )
        
        assert "class MultiToolTool:" in code
        assert "def search(" in code
        assert "def query(" in code
        assert "def traverse(" in code


class TestQuery:
    """Tests for query module."""
    
    def test_simple_query_to_cypher(self):
        """Test simple natural language to Cypher conversion."""
        from agentic_cli.kg.query import simple_query_to_cypher
        
        # Test "all nodes" query
        cypher = simple_query_to_cypher("show all nodes", limit=5)
        assert "MATCH (n)" in cypher
        assert "LIMIT 5" in cypher
        
        # Test "find" query
        cypher = simple_query_to_cypher("find John Doe", limit=10)
        assert "MATCH (n)" in cypher
        assert "CONTAINS" in cypher
    
    def test_format_result(self):
        """Test result formatting."""
        from agentic_cli.kg.query import format_result
        
        result = {
            "n": {"name": "Test Node", "type": "Person"},
            "count": 5,
        }
        
        formatted = format_result(result)
        assert "Person: Test Node" in formatted
        assert "count: 5" in formatted


@pytest.mark.integration
class TestIntegration:
    """Integration tests (require Neo4j and Vertex AI)."""
    
    @pytest.mark.skip(reason="Requires Neo4j running")
    def test_neo4j_connection(self):
        """Test Neo4j connection."""
        from agentic_cli.kg.neo4j_client import Neo4jClient
        
        config = KGConfig(
            neo4j_uri="bolt://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="password",
        )
        
        with Neo4jClient(config) as client:
            stats = client.get_stats()
            assert "nodes" in stats
            assert "relationships" in stats
    
    @pytest.mark.skip(reason="Requires Vertex AI configured")
    def test_entity_extraction(self):
        """Test entity extraction with Vertex AI."""
        from agentic_cli.kg.entity_extraction import extract_entities_from_documents
        
        documents = [
            {
                "title": "Test",
                "content": "John works at Google in Mountain View.",
                "metadata": {"source": "test.txt"},
            }
        ]
        
        entities, relationships = extract_entities_from_documents(
            documents,
            build_relationships=True,
        )
        
        assert len(entities) > 0
        assert any(e["name"] == "John" for e in entities)


class TestDataSourceIntegration:
    """Tests for data source integration with kg commands."""
    
    def test_load_data_config_empty(self, tmp_path):
        """Test loading data config when no config exists."""
        with patch("agentic_cli.commands.kg.CONFIG_FILE", tmp_path / "nonexistent.json"):
            config = load_data_config()
            assert config == {}
    
    def test_load_data_config_with_data(self, tmp_path):
        """Test loading data config with existing data."""
        config_file = tmp_path / "config.json"
        test_config = {
            "data": {
                "sources": [
                    {
                        "name": "test-source",
                        "type": "doc",
                        "location": "/tmp/test"
                    }
                ]
            }
        }
        config_file.write_text(json.dumps(test_config))
        
        with patch("agentic_cli.commands.kg.CONFIG_FILE", config_file):
            config = load_data_config()
            assert "sources" in config
            assert len(config["sources"]) == 1
            assert config["sources"][0]["name"] == "test-source"
    
    def test_resolve_data_source_doc_type(self, tmp_path):
        """Test resolving doc type data source."""
        config_file = tmp_path / "config.json"
        test_config = {
            "data": {
                "sources": [
                    {
                        "name": "my-docs",
                        "type": "doc",
                        "location": "/path/to/docs"
                    }
                ]
            }
        }
        config_file.write_text(json.dumps(test_config))
        
        with patch("agentic_cli.commands.kg.CONFIG_FILE", config_file):
            location, source_type = resolve_data_source("my-docs")
            assert location == "/path/to/docs"
            assert source_type == "doc"
    
    def test_resolve_data_source_confluence_type(self, tmp_path):
        """Test resolving confluence type data source."""
        config_file = tmp_path / "config.json"
        test_config = {
            "data": {
                "sources": [
                    {
                        "name": "my-wiki",
                        "type": "confluence",
                        "location": "https://example.atlassian.net"
                    }
                ]
            }
        }
        config_file.write_text(json.dumps(test_config))
        
        with patch("agentic_cli.commands.kg.CONFIG_FILE", config_file):
            location, source_type = resolve_data_source("my-wiki")
            assert location == "https://example.atlassian.net"
            assert source_type == "confluence"
    
    def test_resolve_data_source_git_type_raises_error(self, tmp_path):
        """Test that git type data sources raise an error."""
        config_file = tmp_path / "config.json"
        test_config = {
            "data": {
                "sources": [
                    {
                        "name": "my-repo",
                        "type": "git",
                        "location": "https://github.com/user/repo.git"
                    }
                ]
            }
        }
        config_file.write_text(json.dumps(test_config))
        
        with patch("agentic_cli.commands.kg.CONFIG_FILE", config_file):
            with pytest.raises(typer.Exit):
                resolve_data_source("my-repo")
    
    def test_resolve_data_source_not_found(self, tmp_path):
        """Test resolving non-existent data source."""
        config_file = tmp_path / "config.json"
        test_config = {
            "data": {
                "sources": []
            }
        }
        config_file.write_text(json.dumps(test_config))
        
        with patch("agentic_cli.commands.kg.CONFIG_FILE", config_file):
            with pytest.raises(typer.Exit):
                resolve_data_source("nonexistent")
    
    def test_resolve_data_source_no_sources_configured(self, tmp_path):
        """Test resolving when no sources are configured."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")
        
        with patch("agentic_cli.commands.kg.CONFIG_FILE", config_file):
            with pytest.raises(typer.Exit):
                resolve_data_source("any-source")
