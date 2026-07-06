"""LLM instructions for the two enrichment passes.

Adapted from the GCP OKF agent's prompts/enrichment_instruction.md and
web_ingestion_instruction.md, rewritten for KEEL OKF concept types and a
JSON-in/JSON-out (single-shot) protocol so they work with a plain Vertex AI
GenerativeModel rather than an ADK tool-loop.
"""
from __future__ import annotations

import json
from typing import Any

OKF_BODY_CONVENTIONS = """\
OKF document conventions (follow exactly):
- Output STRUCTURAL markdown: headings, bullet lists, tables, fenced code blocks.
- Use these conventional headings when applicable:
    `# Overview`        one-paragraph summary of the concept.
    `# Schema`          fields/columns/inputs as a markdown table (one row each,
                        field names in backticks).
    `# Examples`        concrete usage, often fenced code blocks.
    `# Acceptance Criteria`  for Requirement/FREQ concepts, one `- ACn: ...` per line.
    `# Citations`       numbered external sources, `[1] [title](url)`.
- Cross-link other concepts with bundle-absolute markdown links, e.g.
  `See the [auth module](/modules/auth.md).`
- Do NOT invent facts. Only describe what the provided metadata supports.
"""


def structural_prompt(concept_id: str, ctype: str, raw: dict[str, Any]) -> str:
    """Pass 1: turn raw source metadata into one OKF concept document."""
    return f"""\
You are an OKF (Open Knowledge Format) enrichment agent. Write ONE concept
document for the following concept, using only the metadata provided.

Concept id: {concept_id}
OKF type:   {ctype}

Raw metadata (JSON):
{json.dumps(raw, indent=2, default=str)[:6000]}

{OKF_BODY_CONVENTIONS}

Return STRICT JSON (no markdown fence) with exactly these keys:
{{
  "title": "<concise human title>",
  "description": "<one sentence>",
  "tags": ["<short>", "..."],
  "body": "<the markdown body, starting with '# Overview'>"
}}
"""


def enrichment_prompt(page: dict[str, Any], concept_index: list[dict[str, str]]) -> str:
    """Pass 2: decide which existing concept(s) a Confluence page enriches."""
    index_lines = "\n".join(
        f"- {c['id']} ({c['type']}): {c.get('title', '')}" for c in concept_index
    )
    return f"""\
You are enriching an existing OKF bundle from an authoritative Confluence page.
Decide whether this page adds knowledge to one or more EXISTING concepts, or
deserves its own `references/<slug>` concept, or should be skipped.

Existing concepts:
{index_lines or "(none)"}

Confluence page:
  title: {page.get('title', '')}
  url:   {page.get('url', '')}
  text:
{page.get('text', '')[:6000]}

{OKF_BODY_CONVENTIONS}

CRITICAL augmentation rule: when enriching an existing concept you MUST preserve
every existing `# Schema` field, `# Acceptance Criteria` entry, and `# Citations`
entry, and only ADD to them. Never remove or shorten those sections.

Return STRICT JSON (no markdown fence):
{{
  "actions": [
    {{
      "concept_id": "<existing id, or new references/<slug>>",
      "type": "<OKF type, e.g. Requirement>",
      "title": "<title>",
      "description": "<one sentence>",
      "tags": ["..."],
      "body": "<full markdown body to write for this concept>",
      "is_new": true
    }}
  ]
}}
If the page should be skipped, return {{"actions": []}}.
"""
