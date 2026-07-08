"""Structured enterprise-search results for the Ideate Gather step."""
import asyncio
import json
from types import SimpleNamespace

from src.services import ideate_service as svc


def _mcp_result(*texts):
    return SimpleNamespace(content=[SimpleNamespace(text=t) for t in texts])


def test_parse_confluence_json_results():
    payload = json.dumps({
        "total": 2,
        "results": [
            {"title": "Deploy Guide", "url": "https://wiki/x/1",
             "excerpt": "How to deploy", "space_key": "DEV"},
            {"title": "Runbook", "url": "https://wiki/x/2", "excerpt": "On-call"},
        ],
    })
    out = svc._parse_mcp_results(_mcp_result(payload), limit=5)
    assert [r.title for r in out] == ["Deploy Guide", "Runbook"]
    assert out[0].url == "https://wiki/x/1"
    assert out[0].snippet == "How to deploy"


def test_parse_json_list_and_nested_links():
    payload = json.dumps([
        {"title": "A", "_links": {"webui": "https://wiki/a"}, "description": "desc a"},
    ])
    out = svc._parse_mcp_results(_mcp_result(payload), limit=5)
    assert out[0].title == "A" and out[0].url == "https://wiki/a" and out[0].snippet == "desc a"


def test_parse_plaintext_falls_back_to_snippet():
    out = svc._parse_mcp_results(_mcp_result("just some prose, not json"), limit=5)
    assert len(out) == 1
    assert out[0].snippet == "just some prose, not json"
    assert out[0].title == "" and out[0].url == ""


def test_parse_respects_limit():
    payload = json.dumps({"results": [{"title": f"t{i}", "excerpt": "x"} for i in range(10)]})
    out = svc._parse_mcp_results(_mcp_result(payload), limit=3)
    assert len(out) == 3


def test_glean_parses_mcp_json():
    """Glean now routes through its MCP server; JSON hits map to SearchResults."""
    payload = json.dumps({"results": [
        {"title": "Doc", "url": "https://g/1", "snippet": "snip"},
    ]})
    out = svc._parse_mcp_results(_mcp_result(payload), limit=5)
    assert out[0].title == "Doc" and out[0].url == "https://g/1" and out[0].snippet == "snip"


def test_glean_parses_nested_document_and_snippets():
    """Glean's real REST shape nests title/url under `document` and uses a
    `snippets` array — these must map to a linkable SearchResult."""
    payload = json.dumps({"results": [
        {
            "trackingToken": "abc",
            "document": {"id": "d1", "title": "Facility Onboarding",
                         "url": "https://confluence/x/FAC/123", "datasource": "confluence"},
            "snippets": [
                {"text": "Step one of onboarding"},
                {"snippet": {"text": "Step two details"}},
            ],
        },
    ]})
    out = svc._parse_mcp_results(_mcp_result(payload), limit=5)
    assert len(out) == 1
    assert out[0].title == "Facility Onboarding"
    assert out[0].url == "https://confluence/x/FAC/123"
    assert "Step one of onboarding" in out[0].snippet
    assert "Step two details" in out[0].snippet


def test_search_source_joins_structured_blocks(monkeypatch):
    async def fake_results(source, query, limit=5, user_token=None):
        return [svc.SearchResult(title="T", url="https://u/1", snippet="body")]
    monkeypatch.setattr(svc, "search_results", fake_results)
    text = asyncio.run(svc.search_source("confluence", "q"))
    assert "T" in text and "https://u/1" in text and "body" in text


class _AsyncCM:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *a):
        return False


class _FakeSession:
    def __init__(self, result):
        self._result = result

    async def initialize(self):
        return None

    async def list_tools(self):
        tool = SimpleNamespace(name="search_glean", inputSchema={"properties": {"query": {}}})
        return SimpleNamespace(tools=[tool])

    async def call_tool(self, name, args):
        return self._result


def _install_fake_mcp(monkeypatch, result):
    """Stub the mcp modules imported inside search_results with a fake session."""
    mcp_mod = SimpleNamespace(ClientSession=lambda r, w: _AsyncCM(_FakeSession(result)))
    sse_mod = SimpleNamespace(sse_client=lambda url: _AsyncCM((object(), object())))
    client_pkg = SimpleNamespace(sse=sse_mod)
    monkeypatch.setitem(__import__("sys").modules, "mcp", mcp_mod)
    monkeypatch.setitem(__import__("sys").modules, "mcp.client", client_pkg)
    monkeypatch.setitem(__import__("sys").modules, "mcp.client.sse", sse_mod)


def test_search_results_raises_on_tool_error(monkeypatch):
    """An MCP tool error (e.g. 'Glean is not configured') surfaces as RuntimeError."""
    err = SimpleNamespace(
        isError=True,
        content=[SimpleNamespace(text="Error executing tool search_glean: Glean is not configured. Set GLEAN_API_TOKEN")],
    )
    _install_fake_mcp(monkeypatch, err)
    try:
        asyncio.run(svc.search_results("glean", "test", limit=3))
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "not configured" in str(e)


def test_search_results_ok_via_mcp(monkeypatch):
    """A successful MCP tool result is parsed into structured hits."""
    ok = SimpleNamespace(
        isError=False,
        content=[SimpleNamespace(text=json.dumps({"results": [
            {"title": "Doc", "url": "https://g/1", "snippet": "snip"}]}))],
    )
    _install_fake_mcp(monkeypatch, ok)
    out = asyncio.run(svc.search_results("glean", "test", limit=3))
    assert out[0].title == "Doc" and out[0].url == "https://g/1"
