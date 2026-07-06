"""OKF enrichment agent — produces/enriches OKF bundles from CLI domain sources.

Adapted from the GoogleCloudPlatform/knowledge-catalog OKF enrichment agent
(https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf), wired
to KEEL CLI domain data instead of BigQuery + arbitrary web crawl:

  GCP enrichment agent          ->   KEEL OKF enrichment
  ---------------------------        --------------------------------
  BigQuerySource                ->   CodebaseSource (domain repos)
  web pass (fetch_url crawl)    ->   Confluence pass (tracked domain docs via MCP)
  ADK + Gemini                  ->   Vertex AI Gemini (agentic_cli.agents.onboard.models)

Two-pass philosophy is preserved:
  Pass 1 (structural): one OKF doc per concept the Source advertises.
  Pass 2 (enrichment): an LLM augments existing docs from authoritative prose
                       (Confluence), never shrinking structured sections.

All paths (bundle dir, codebase roots, Confluence page ids, Jira project) are
resolved from registered CLI domain data — see `domain_paths`.
"""
from __future__ import annotations

from agentic_cli.kg.okf.enrichment.source import ConceptRef, Source

__all__ = ["ConceptRef", "Source"]
