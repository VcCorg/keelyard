"""Tests for the template system."""

import pytest
import tempfile
from pathlib import Path

from agentic_cli.templates import (
    Framework,
    UseCase,
    Tool,
    TemplateConfig,
    TemplateGenerator,
    USE_CASE_TOOLS,
)


class TestEnums:
    """Test enum classes."""
    
    def test_framework_choices(self):
        choices = Framework.choices()
        assert "adk" in choices
        assert "langgraph" in choices
    
    def test_framework_display_name(self):
        assert "ADK" in Framework.ADK.display_name
        assert "LangGraph" in Framework.LANGGRAPH.display_name
    
    def test_use_case_choices(self):
        choices = UseCase.choices()
        assert "basic" in choices
        assert "rag" in choices
        assert "knowledge-graph" in choices
    
    def test_use_case_description(self):
        assert UseCase.BASIC.description
        assert UseCase.RAG.description
    
    def test_tool_choices(self):
        choices = Tool.choices()
        assert "calculator" in choices
        assert "kg_query" in choices


class TestTemplateConfig:
    """Test TemplateConfig class."""
    
    def test_auto_populate_tools(self):
        config = TemplateConfig(
            name="test",
            framework=Framework.ADK,
            use_case=UseCase.BASIC,
        )
        assert len(config.tools) > 0
        assert Tool.CALCULATOR in config.tools
    
    def test_custom_tools(self):
        config = TemplateConfig(
            name="test",
            framework=Framework.ADK,
            use_case=UseCase.BASIC,
            tools=[Tool.WEB_SEARCH],
        )
        assert Tool.WEB_SEARCH in config.tools
    
    def test_add_tool(self):
        config = TemplateConfig(
            name="test",
            framework=Framework.ADK,
            use_case=UseCase.BASIC,
        )
        config.add_tool(Tool.WEB_SEARCH)
        assert Tool.WEB_SEARCH in config.tools
    
    def test_dependencies(self):
        config = TemplateConfig(
            name="test",
            framework=Framework.ADK,
            use_case=UseCase.BASIC,
        )
        deps = config.dependencies
        assert any("typer" in d for d in deps)
        assert any("google" in d.lower() for d in deps)
    
    def test_kg_dependencies(self):
        config = TemplateConfig(
            name="test",
            framework=Framework.ADK,
            use_case=UseCase.KNOWLEDGE_GRAPH,
        )
        deps = config.dependencies
        assert any("neo4j" in d for d in deps)


class TestUseCaseTools:
    """Test use case to tools mapping."""
    
    def test_basic_tools(self):
        tools = USE_CASE_TOOLS[UseCase.BASIC]
        assert Tool.CALCULATOR in tools
        assert Tool.TEXT_ANALYZER in tools
    
    def test_rag_tools(self):
        tools = USE_CASE_TOOLS[UseCase.RAG]
        assert Tool.VECTOR_SEARCH in tools
        assert Tool.DOCUMENT_LOADER in tools
    
    def test_kg_tools(self):
        tools = USE_CASE_TOOLS[UseCase.KNOWLEDGE_GRAPH]
        assert Tool.KG_QUERY in tools
        assert Tool.KG_INGEST in tools


class TestTemplateGenerator:
    """Test TemplateGenerator class."""
    
    def test_generate_basic_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="test-project",
                framework=Framework.ADK,
                use_case=UseCase.BASIC,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "test-project"
            generator.generate(target)
            
            assert (target / "pyproject.toml").exists()
            assert (target / "README.md").exists()
            assert (target / "src" / "main.py").exists()
            assert (target / "src" / "agents" / "base.py").exists()
            assert (target / "src" / "tools").exists()
    
    def test_generate_kg_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="kg-project",
                framework=Framework.ADK,
                use_case=UseCase.KNOWLEDGE_GRAPH,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "kg-project"
            generator.generate(target)
            
            assert (target / "src" / "tools" / "kg_query.py").exists()
            assert (target / "src" / "agents" / "kg_agent.py").exists()
    
    def test_generate_with_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="test-project",
                framework=Framework.ADK,
                use_case=UseCase.BASIC,
                include_tests=True,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "test-project"
            generator.generate(target)
            
            assert (target / "tests").exists()
            assert (target / "tests" / "test_agent.py").exists()
    
    def test_generate_without_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="test-project",
                framework=Framework.ADK,
                use_case=UseCase.BASIC,
                include_tests=False,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "test-project"
            generator.generate(target)
            
            assert not (target / "tests").exists()
    
    def test_generate_with_docker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="test-project",
                framework=Framework.ADK,
                use_case=UseCase.BASIC,
                include_docker=True,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "test-project"
            generator.generate(target)
            
            assert (target / "Dockerfile").exists()
            assert (target / "docker-compose.yml").exists()
    
    def test_pyproject_contains_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="my-custom-agent",
                framework=Framework.ADK,
                use_case=UseCase.BASIC,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "my-custom-agent"
            generator.generate(target)
            
            content = (target / "pyproject.toml").read_text()
            assert 'name = "my-custom-agent"' in content
    
    def test_generate_with_a2a(self):
        """Test generating multi-agent project with A2A protocol support."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="multi-agent-a2a",
                framework=Framework.ADK,
                use_case=UseCase.MULTI_AGENT,
                include_a2a=True,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "multi-agent-a2a"
            generator.generate(target)
            
            # Check A2A files exist
            assert (target / "src" / "a2a").exists()
            assert (target / "src" / "a2a" / "__init__.py").exists()
            assert (target / "src" / "a2a" / "models.py").exists()
            assert (target / "src" / "a2a" / "server.py").exists()
            assert (target / "src" / "a2a" / "client.py").exists()
            assert (target / "examples" / "a2a_server_example.py").exists()
            
            # Check A2A dependencies in pyproject.toml
            content = (target / "pyproject.toml").read_text()
            assert "fastapi" in content
            assert "uvicorn" in content
            assert "sse-starlette" in content
    
    def test_generate_without_a2a(self):
        """Test that A2A files are not generated when include_a2a is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="multi-agent-no-a2a",
                framework=Framework.ADK,
                use_case=UseCase.MULTI_AGENT,
                include_a2a=False,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "multi-agent-no-a2a"
            generator.generate(target)
            
            # A2A directory should not exist
            assert not (target / "src" / "a2a").exists()

    def test_generate_with_kg_mcp(self):
        """Test generating KG project with MCP server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="kg-mcp-project",
                framework=Framework.ADK,
                use_case=UseCase.KNOWLEDGE_GRAPH,
                include_kg_mcp=True,
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "kg-mcp-project"
            generator.generate(target)
            
            # Check MCP files exist
            assert (target / "src" / "mcp").exists()
            assert (target / "src" / "mcp" / "kg_server.py").exists()
            
            # Check MCP dependencies
            content = (target / "pyproject.toml").read_text()
            assert "mcp" in content

    def test_generate_with_kg_workspace(self):
        """Test generating KG project with workspace integration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TemplateConfig(
                name="kg-workspace-project",
                framework=Framework.ADK,
                use_case=UseCase.KNOWLEDGE_GRAPH,
                kg_workspace="test-workspace",
            )
            generator = TemplateGenerator(config)
            target = Path(tmpdir) / "kg-workspace-project"
            generator.generate(target)
            
            # Check workspace client files exist
            assert (target / "src" / "kg").exists()
            assert (target / "src" / "kg" / "workspace_client.py").exists()
            
            # Check example has workspace name
            example = (target / "examples" / "kg_workspace_example.py").read_text()
            assert "test-workspace" in example
