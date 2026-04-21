"""Generate test files."""

from pathlib import Path
from dva_agentic_cli.templates.config import TemplateConfig


def generate_test_files(tests_dir: Path, config: TemplateConfig) -> None:
    """Generate test files."""
    (tests_dir / "__init__.py").write_text("")
    
    content = f'''"""Tests for {config.name}."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.google_project_id = "test-project"
    settings.google_location = "us-central1"
    settings.vertex_ai_model = "gemini-2.0-flash-001"
    return settings


class TestAgent:
    """Test the main agent."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_settings):
        """Test agent can be initialized."""
        # Import will vary based on use case
        pass
    
    @pytest.mark.asyncio
    async def test_agent_process(self, mock_settings):
        """Test agent can process input."""
        pass


class TestTools:
    """Test the tools."""
    
    def test_tools_exist(self):
        """Test that tool files exist."""
        from pathlib import Path
        tools_dir = Path(__file__).parent.parent / "src" / "tools"
        assert tools_dir.exists()
'''
    (tests_dir / "test_agent.py").write_text(content)
