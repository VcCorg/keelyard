"""OKF (Open Knowledge Format) — Markdown-native knowledge bundles for the KG.

A bundle is a directory of Markdown concept files governed by an `okf.schema.yaml`
contract (concept types + relationship roles + legal triples). The bundle is the
source of truth; Neo4j/LightRAG are optional derived projections.

Modules:
  schema    - OKFSchema + canonical model + Neo4j->OKF mapping tables
  model     - Concept (frontmatter + body), link parsing/serialization
  bundle    - load a bundle from disk (schema + concepts + edges)
  validate  - conformance validation against the schema
  trace     - FREQ dev/QA traceability views
  exporter  - build a bundle from an already-ingested Neo4j domain (no reindex)
"""

from agentic_cli.kg.okf.schema import OKFSchema, canonical_schema_dict

__all__ = ["OKFSchema", "canonical_schema_dict"]
