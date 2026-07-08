"""Ideate agent — a provider-agnostic ReAct JSON tool loop.

The model emits either an action to call a tool, or a final answer with drafted
stories. We parse tolerant JSON out of the text response (providers only do
text in → text out), execute tools via ``ideate_tools``, feed observations back,
and stream every step as an ``AgentEvent`` for SSE.
"""
from __future__ import annotations

import json
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import BaseModel


class AgentEvent(BaseModel):
    type: str  # thinking | tool_call | tool_result | stories | final | error
    text: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    stories: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


def _extract_json_object(text: str) -> Dict[str, Any]:
    """Find and parse the first balanced JSON object in ``text`` (tolerant)."""
    cleaned = re.sub(r"```(?:json)?", "", text or "")
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            c = cleaned[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    chunk = cleaned[start:i + 1]
                    try:
                        return json.loads(chunk)
                    except json.JSONDecodeError:
                        break  # try next '{'
        start = cleaned.find("{", start + 1)
    raise ValueError("No parseable JSON object found in model output")


def parse_action(text: str) -> Dict[str, Any]:
    """Parse a ReAct step into a normalized dict.

    Returns one of:
      {"kind": "tool", "tool": str, "args": dict}
      {"kind": "final", "stories": list}
    Raises ValueError when neither shape is present.
    """
    obj = _extract_json_object(text)
    if "action" in obj and isinstance(obj["action"], dict):
        act = obj["action"]
        return {"kind": "tool", "tool": act.get("tool", ""), "args": act.get("args") or {}}
    if "final" in obj and isinstance(obj["final"], dict):
        return {"kind": "final", "stories": obj["final"].get("stories") or []}
    raise ValueError("JSON did not contain an 'action' or 'final' key")


_SYSTEM = (
    "You are Ideate's planning agent. You gather requirements using tools and then "
    "draft Jira user stories. On each turn respond with EXACTLY ONE JSON object and "
    "nothing else.\n"
    'To use a tool: {"action": {"tool": "<name>", "args": {...}}}\n'
    'When done: {"final": {"stories": [{"title": str, "description": str, '
    '"acceptance_criteria": [str], "priority": "High|Medium|Low", "issue_type": "Story"}]}}\n'
)


def _tool_catalog(tools_list) -> str:
    lines = []
    for t in tools_list:
        lines.append(f"- {t.name}({', '.join((t.params.get('properties') or {}).keys())}): {t.description}")
    return "\n".join(lines)


def _observation(result) -> str:
    try:
        return json.dumps(result)[:2000]
    except Exception:  # noqa: BLE001
        return str(result)[:2000]


async def run_agent(task: str, context: str, ctx, model: Optional[str] = None,
                    max_iters: int = 6, provider=None) -> AsyncGenerator[AgentEvent, None]:
    """Run the ReAct loop, yielding AgentEvents. Falls back to heuristic drafting
    on malformed output or when the iteration cap is hit without a final answer."""
    from src.services import ideate_tools

    tools_list = ideate_tools.list_tools(ctx)
    if provider is None:
        try:
            from agentic_cli.llm.factory import get_llm_provider
            provider = get_llm_provider(model_name=model, system_instruction=_SYSTEM)
        except Exception:  # noqa: BLE001 - no provider → heuristic
            yield _fallback(task, context)
            return

    transcript = (
        f"{_SYSTEM}\nAvailable tools:\n{_tool_catalog(tools_list)}\n\n"
        f"Task: {task}\n\nGathered context so far:\n{context}\n"
    )
    reprompted = False

    for _ in range(max_iters):
        try:
            raw = provider.generate(transcript)
        except Exception as e:  # noqa: BLE001
            yield AgentEvent(type="error", error=str(e))
            yield _fallback(task, context)
            return

        try:
            action = parse_action(raw)
        except ValueError:
            if not reprompted:
                reprompted = True
                transcript += "\nYour last message was not valid JSON. Respond with ONE JSON object only."
                continue
            yield _fallback(task, context)
            return

        if action["kind"] == "final":
            yield AgentEvent(type="stories", stories=action["stories"])
            yield AgentEvent(type="final", text="Done")
            return

        tool, args = action["tool"], action["args"]
        yield AgentEvent(type="tool_call", tool=tool, args=args)
        result = await ideate_tools.call_tool(tool, args, ctx)
        yield AgentEvent(type="tool_result", tool=tool, result=result)
        transcript += (
            f'\nYou called {tool} with {args}. Observation: {_observation(result)}\n'
            "Respond with the next JSON object (another action, or final).\n"
        )

    # Iteration cap reached without a final answer.
    yield _fallback(task, context)


def _fallback(task: str, context: str) -> AgentEvent:
    """Deterministic drafting when the agent can't produce a final answer."""
    from src.services.ideate_service import draft_stories
    result = draft_stories(context or task, count=5)
    return AgentEvent(type="stories", stories=[s.model_dump() for s in result.stories])
