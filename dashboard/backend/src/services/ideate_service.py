"""Ideate — requirements gathering → drafted Jira stories.

Turns free-text / document / enterprise-search context into structured,
reviewable user stories that a human approves before anything is pushed to
Jira (draft → review → push). Story drafting uses the configured LLM provider
and degrades to a deterministic heuristic when no provider is configured, so
the module always returns something to review.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Story(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: List[str] = []
    priority: str = "Medium"
    labels: List[str] = []


class DraftResult(BaseModel):
    stories: List[Story]
    source: str  # "llm" | "heuristic"


_PRIORITIES = {"high", "medium", "low"}


def _coerce_story(raw: Dict[str, Any]) -> Optional[Story]:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    priority = str(raw.get("priority") or "Medium").strip().capitalize()
    if priority.lower() not in _PRIORITIES:
        priority = "Medium"
    ac = raw.get("acceptance_criteria") or []
    if isinstance(ac, str):
        ac = [ac]
    labels = raw.get("labels") or []
    if isinstance(labels, str):
        labels = [labels]
    return Story(
        title=title[:200],
        description=str(raw.get("description") or "").strip(),
        acceptance_criteria=[str(x).strip() for x in ac if str(x).strip()],
        priority=priority,
        labels=[str(x).strip() for x in labels if str(x).strip()],
    )


def _parse_stories(text: str) -> List[Story]:
    """Extract a JSON array of stories from an LLM response (tolerant)."""
    if not text:
        return []
    # Strip code fences and locate the first JSON array.
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    out: List[Story] = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict):
            story = _coerce_story(item)
            if story:
                out.append(story)
    return out


def _fallback_stories(context: str, count: int) -> List[Story]:
    """Deterministic drafting when no LLM is configured: one story per bullet /
    sentence in the context, so the module still produces reviewable output."""
    # Prefer explicit bullet lines; else split into sentences.
    lines = [ln.strip(" -*\t") for ln in context.splitlines() if ln.strip(" -*\t")]
    if len(lines) < 2:
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", context) if s.strip()]
    stories: List[Story] = []
    for chunk in lines[:count]:
        title = chunk[:80] + ("…" if len(chunk) > 80 else "")
        stories.append(
            Story(
                title=title,
                description=f"As a user, I want: {chunk}",
                acceptance_criteria=["The described behavior is implemented and verified."],
                priority="Medium",
                labels=["ideate"],
            )
        )
    return stories


def draft_stories(context: str, count: int = 5, model: Optional[str] = None) -> DraftResult:
    """Draft up to ``count`` user stories from gathered requirements."""
    context = (context or "").strip()
    if not context:
        return DraftResult(stories=[], source="heuristic")

    prompt = (
        f"You are a product analyst. From the requirements below, write up to {count} "
        "concise Jira user stories. Return ONLY a JSON array; each item must be an object "
        'with keys: "title" (string), "description" (string, in "As a … I want … so that …" '
        'form), "acceptance_criteria" (array of strings), "priority" ("High"|"Medium"|"Low"), '
        '"labels" (array of strings).\n\nRequirements:\n'
        f"{context}\n"
    )
    try:
        from agentic_cli.llm.factory import get_llm_provider

        provider = get_llm_provider(
            model_name=model,
            system_instruction="You write clear, testable Jira user stories as strict JSON.",
        )
        raw = provider.generate(prompt)
        stories = _parse_stories(raw)
        if stories:
            return DraftResult(stories=stories[:count], source="llm")
    except Exception:  # noqa: BLE001 - any provider/SDK issue → heuristic
        pass

    return DraftResult(stories=_fallback_stories(context, count), source="heuristic")


def extract_text(content: bytes, filename: str) -> str:
    """Extract text from an uploaded requirements document (best-effort)."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            import io

            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception:  # noqa: BLE001 - no pypdf / unreadable PDF
            return ""
    # Text-like formats.
    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception:  # noqa: BLE001
        return ""
