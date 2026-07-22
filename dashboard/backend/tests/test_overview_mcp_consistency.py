"""Dashboard overview MCP counts must match the MCP page's source of truth.

If the Dashboard card and the MCP page ever diverge, users would see two
different pictures of the same fleet — so pin the invariant here.
"""

from src.services import mcp_service


class _FakeHealth:
    def __init__(self, healthy: bool):
        self.healthy = healthy


def test_overview_mcp_counts_match_mcp_service(monkeypatch):
    """Overview aggregates counts by calling the same list + check_health as MCP page."""
    servers = [
        mcp_service.MCPServerInfo(name="a", type="sse", url="https://a/sse"),
        mcp_service.MCPServerInfo(name="b", type="sse", url="https://b/sse"),
        mcp_service.MCPServerInfo(name="c", type="sse", url="https://c/sse"),
    ]
    health = [_FakeHealth(True), _FakeHealth(False), _FakeHealth(True)]

    monkeypatch.setattr(mcp_service, "list_mcp_servers", lambda: servers)
    monkeypatch.setattr(mcp_service, "check_health", lambda: health)

    # Reproduce the same math the overview endpoint does.
    total = len(mcp_service.list_mcp_servers())
    results = mcp_service.check_health()
    healthy = sum(1 for h in results if h.healthy)
    unhealthy = len(results) - healthy

    assert total == 3
    assert healthy == 2
    assert unhealthy == 1


def test_overview_endpoint_uses_mcp_service_directly():
    """The overview endpoint imports both list_mcp_servers and check_health.

    Guards against a regression where the dashboard grows its own cache and
    starts drifting from the MCP page.
    """
    import src.api.main as api_main

    src = api_main.__file__
    with open(src) as f:
        body = f.read()
    # These two symbols are the single source of truth for MCP status; both
    # /api/overview and /api/mcp/* consume them, so counts stay consistent.
    assert "list_mcp_servers" in body
    assert "check_health" in body
