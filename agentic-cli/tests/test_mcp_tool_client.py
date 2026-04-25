"""Tests for MCP Tool Client — SSE negotiation, tool calls, helpers."""

import json
import pytest
from unittest.mock import patch, MagicMock

from agentic_cli.mcp_tool_client import (
    MCPToolClient,
    MCPToolError,
    parse_project_key,
    parse_space_key,
)


# ---------------------------------------------------------------------------
# parse_project_key
# ---------------------------------------------------------------------------

class TestParseProjectKey:
    def test_plain_key(self):
        assert parse_project_key("CGF") == "CGF"

    def test_url(self):
        assert parse_project_key("https://bitbucket.example.com/projects/CGF") == "CGF"

    def test_url_with_repos(self):
        assert parse_project_key("https://bitbucket.example.com/projects/CGF/repos/something") == "CGF"

    def test_empty(self):
        assert parse_project_key("") == ""

    def test_no_projects_segment(self):
        assert parse_project_key("https://example.com/foo") == "https://example.com/foo"


# ---------------------------------------------------------------------------
# parse_space_key
# ---------------------------------------------------------------------------

class TestParseSpaceKey:
    def test_plain_key(self):
        assert parse_space_key("MTT") == "MTT"

    def test_display_url(self):
        assert parse_space_key("https://confluence.example.com/display/MTT") == "MTT"

    def test_display_url_subpath(self):
        assert parse_space_key("https://confluence.example.com/display/MTT/Some+Page") == "MTT"

    def test_spaces_url(self):
        assert parse_space_key("https://confluence.example.com/spaces/DEV/overview") == "DEV"

    def test_empty(self):
        assert parse_space_key("") == ""

    def test_unknown_pattern(self):
        assert parse_space_key("https://example.com/foo/bar") == "https://example.com/foo/bar"


# ---------------------------------------------------------------------------
# MCPToolClient
# ---------------------------------------------------------------------------

class TestMCPToolClient:
    def test_init(self):
        client = MCPToolClient("http://localhost:9999/sse")
        assert client.sse_url == "http://localhost:9999/sse"
        client.close()

    def test_context_manager(self):
        with MCPToolClient("http://localhost:9999/sse") as client:
            assert client.sse_url

    def test_is_available_false_when_not_running(self):
        """is_available returns False when server is not reachable."""
        client = MCPToolClient("http://localhost:59999/sse", timeout=1.0)
        assert client.is_available() is False
        client.close()

    def test_call_tool_connection_error(self):
        """call_tool raises MCPToolError with is_connection_error when server unreachable."""
        with patch("agentic_cli.mcp_tool_client.call_mcp_tool",
                   side_effect=MCPToolError("Cannot connect", is_connection_error=True)):
            client = MCPToolClient("http://localhost:59999/sse", timeout=1.0)
            with pytest.raises(MCPToolError) as exc_info:
                client.call_tool("some_tool", {"arg": "value"})
            assert exc_info.value.is_connection_error is True
            client.close()

    def test_call_tool_success(self):
        """Verify tool call delegates to call_mcp_tool and returns parsed JSON."""
        mock_result = {"repos": [{"slug": "my-repo"}]}
        with patch("agentic_cli.mcp_tool_client.call_mcp_tool", return_value=mock_result):
            client = MCPToolClient("http://localhost:9999/sse")
            result = client.call_tool("list_project_repos", {"project": "CGF"})
        assert result == {"repos": [{"slug": "my-repo"}]}
        client.close()

    def test_call_tool_mcp_error(self):
        """Verify MCP error response is raised as MCPToolError."""
        with patch("agentic_cli.mcp_tool_client.call_mcp_tool",
                   side_effect=MCPToolError("MCP tool error: Space not found")):
            client = MCPToolClient("http://localhost:9999/sse")
            with pytest.raises(MCPToolError, match="Space not found"):
                client.call_tool("get_confluence_space", {"space_key": "NOPE"})
        client.close()

    def test_call_tool_plain_text_response(self):
        """Non-JSON text content is returned as string."""
        with patch("agentic_cli.mcp_tool_client.call_mcp_tool",
                   return_value="Some plain text response"):
            client = MCPToolClient("http://localhost:9999/sse")
            result = client.call_tool("some_tool", {})
        assert result == "Some plain text response"
        client.close()


# ---------------------------------------------------------------------------
# MCPToolError
# ---------------------------------------------------------------------------

class TestMCPToolError:
    def test_default(self):
        err = MCPToolError("something failed")
        assert str(err) == "something failed"
        assert err.is_connection_error is False

    def test_connection_error(self):
        err = MCPToolError("no connection", is_connection_error=True)
        assert err.is_connection_error is True
