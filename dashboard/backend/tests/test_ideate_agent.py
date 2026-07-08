from src.services.ideate_agent import AgentEvent, parse_action


def test_parse_action_tool():
    a = parse_action('{"action": {"tool": "glean_search", "args": {"query": "x"}}}')
    assert a == {"kind": "tool", "tool": "glean_search", "args": {"query": "x"}}


def test_parse_action_final():
    a = parse_action('Here you go:\n```json\n{"final": {"stories": [{"title": "T"}]}}\n```')
    assert a["kind"] == "final"
    assert a["stories"] == [{"title": "T"}]


def test_parse_action_tolerates_prose_prefix():
    a = parse_action('thinking... {"action": {"tool": "jira_search", "args": {}}} trailing')
    assert a["kind"] == "tool" and a["tool"] == "jira_search" and a["args"] == {}


def test_parse_action_malformed_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_action("no json here")


def test_agent_event_defaults():
    e = AgentEvent(type="thinking", text="hi")
    assert e.type == "thinking" and e.text == "hi"
    assert e.tool is None and e.stories is None


import asyncio
from src.services.ideate_agent import run_agent
from src.services.ideate_tools import ToolContext


class _FakeProvider:
    """Returns scripted outputs in order for each generate() call."""
    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._outputs.pop(0) if self._outputs else '{"final": {"stories": []}}'

    def get_name(self) -> str:
        return "fake"


async def _collect(gen):
    return [e async for e in gen]


def test_run_agent_tool_then_final(monkeypatch):
    import src.services.ideate_tools as tools

    async def fake_call(name, args, ctx):
        return {"text": "found stuff"}
    monkeypatch.setattr(tools, "call_tool", fake_call)

    provider = _FakeProvider([
        '{"action": {"tool": "glean_search", "args": {"query": "auth"}}}',
        '{"final": {"stories": [{"title": "Login"}]}}',
    ])
    ctx = ToolContext(project_key="CGF")
    events = asyncio.run(_collect(run_agent("draft stories", "context", ctx, provider=provider)))
    types = [e.type for e in events]
    assert "tool_call" in types and "tool_result" in types
    assert types[-1] in ("stories", "final")
    final = [e for e in events if e.stories is not None][-1]
    assert final.stories == [{"title": "Login"}]


def test_run_agent_falls_back_on_malformed(monkeypatch):
    import src.services.ideate_service as isvc
    from src.services.ideate_service import DraftResult, Story
    monkeypatch.setattr(isvc, "draft_stories",
                        lambda context, count=5, model=None: DraftResult(stories=[Story(title="FB")], source="heuristic"))

    provider = _FakeProvider(["not json", "still not json"])
    ctx = ToolContext(project_key="CGF")
    events = asyncio.run(_collect(run_agent("draft", "ctx", ctx, provider=provider, max_iters=2)))
    final = [e for e in events if e.stories is not None][-1]
    assert final.stories[0]["title"] == "FB"


def test_run_agent_respects_iteration_cap(monkeypatch):
    import src.services.ideate_tools as tools

    async def fake_call(name, args, ctx):
        return {"text": "more"}
    monkeypatch.setattr(tools, "call_tool", fake_call)
    import src.services.ideate_service as isvc
    from src.services.ideate_service import DraftResult
    monkeypatch.setattr(isvc, "draft_stories",
                        lambda context, count=5, model=None: DraftResult(stories=[], source="heuristic"))

    # Always asks for a tool, never final → must stop at max_iters and fall back.
    provider = _FakeProvider(['{"action": {"tool": "glean_search", "args": {"query": "x"}}}'] * 10)
    ctx = ToolContext(project_key="CGF")
    events = asyncio.run(_collect(run_agent("draft", "ctx", ctx, provider=provider, max_iters=3)))
    tool_calls = [e for e in events if e.type == "tool_call"]
    assert len(tool_calls) <= 3
    assert any(e.stories is not None for e in events)
