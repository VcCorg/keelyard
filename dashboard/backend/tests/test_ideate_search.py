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


def test_search_results_glean_configured(monkeypatch):
    from agentic_cli.glean import GleanResult

    class FakeCfg:
        def unavailable_reason(self, tok):
            return None

    import agentic_cli.glean as glean
    monkeypatch.setattr(glean.GleanConfig, "load", classmethod(lambda cls: FakeCfg()))
    monkeypatch.setattr(
        glean, "search",
        lambda q, page_size=5, config=None, user_token=None: [
            GleanResult(title="Doc", url="https://g/1", snippet="snip"),
        ])
    out = asyncio.run(svc.search_results("glean", "auth", limit=5))
    assert out[0].title == "Doc" and out[0].url == "https://g/1" and out[0].snippet == "snip"


def test_search_source_joins_structured_blocks(monkeypatch):
    async def fake_results(source, query, limit=5, user_token=None):
        return [svc.SearchResult(title="T", url="https://u/1", snippet="body")]
    monkeypatch.setattr(svc, "search_results", fake_results)
    text = asyncio.run(svc.search_source("confluence", "q"))
    assert "T" in text and "https://u/1" in text and "body" in text
