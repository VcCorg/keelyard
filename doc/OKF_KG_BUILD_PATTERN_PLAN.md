# OKF-Based KG Build Pattern — Implementation Plan

Status: PLANNED
Reference: Open Knowledge Format (OKF) — https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

## Decisions

1. **Bundle as source of truth.** The OKF Markdown bundle is the canonical KG.
   Neo4j / LightRAG become *optional derived projections* produced on demand by
   `dva kg okf compile`. Infra is removed from the default path.
2. **Per-domain in meta-repo.** Each bundle lives at
   `domain-<slug>-meta/knowledge/` with its own `okf.schema.yaml`, PR-reviewed
   per domain alongside existing domain context.

## Motivation

Current KG generation (`dva kg ingest submit`) parses sources, LLM-extracts
free-form entities/relationships, and writes them to Neo4j + LightRAG via
sync/async workers. Problems:

- Infra overhead: always-on Neo4j + LightRAG servers, async workers, embeddings.
- Knowledge locked in a DB: not diffable, not PR-reviewable, not co-located with
  code or domain context.
- Relationship "strictness" enforced only at LLM-prompt time
  (`linker.py: VALID_RELATIONSHIP_TYPES`), not stored as a committed contract.

OKF replaces this with a git-native bundle of Markdown concept documents, where
relationships are typed cross-links validated against a committed schema.

## Current → OKF mapping

| Today (Neo4j)                              | OKF equivalent                                  |
|--------------------------------------------|-------------------------------------------------|
| Node label (Patient, Release, Document)    | Concept `type` enum in `okf.schema.yaml`        |
| Relationship type (IMPLEMENTS, TESTED_BY)  | Allowed link-semantic role in schema            |
| `linker.VALID_RELATIONSHIP_TYPES`          | `okf.schema.yaml: relationships:` allowlist     |
| Confidence >= 0.7 prompt gate              | Validation rule + required citation             |
| DB unique constraint / sanitize_label      | `dva kg okf validate` conformance check (CI)    |

Strictness improves: a constrained prompt hint becomes a committed schema
validated on every change.

## Target architecture

```
domain-<slug>-meta/knowledge/        # OKF bundle (committed, PR-reviewed)
  okf.schema.yaml                    # allowed concept types + relationship triples
  index.md                           # bundle index (reserved)
  concepts/
    patient.md                       # frontmatter(id,type,resource) + body + typed links
    eligibility-check.md
  log/                               # generation provenance (optional)
        |
        |-- dva kg okf validate ---> conformance gate (CI)
        '-- dva kg okf compile  ---> OPTIONAL Neo4j / LightRAG projection
```

- Default path is infra-free: generate + validate + query Markdown locally / via MCP.
- Neo4j/LightRAG are derived only when graph/vector queries are needed.

## Stable vs transient (anchors, not values)

The bundle stores only **stable knowledge**; **transient state is never written** —
it is hydrated live from the system of record via MCP at query/trace time.

- Stable (in KG): `freq_id`, title, relationships, acceptance criteria, `resource:`
  repo bindings, external anchors (`jira:`, `confluence:` URLs).
- Transient (NOT in KG, hydrate via MCP): Jira `status`, `assignee`, `sprint`,
  `story_points`, PR/`build_status`, `updated`, `owner`.

Rule of thumb: if a field can change without changing the requirement's meaning,
it is transient — store the anchor, resolve the value on demand. Enforced by
`okf.schema.yaml: transient_fields` + rule `forbid_transient_fields: true`, and
hydrated by `dva kg okf trace --hydrate` (Jira MCP `mcp0_jira_get_issue`).

## Schema contract (`okf.schema.yaml`)

Defines, per domain:
- `concept_types:` allowed `type` values (maps to former node labels).
- `relationships:` allowed link-semantic roles.
- `triples:` legal `(source_type)-[role]->(target_type)` combinations,
  e.g. only `Code -implements-> Requirement`.
- Validation rules: required frontmatter fields, citation requirements, link
  resolution.

Seed the initial relationship allowlist from
`agentic_cli/kg/linker.py: VALID_RELATIONSHIP_TYPES`
(`IMPLEMENTS, REFERENCES, TESTED_BY, CONFIGURES`).

## Command changes (`dva kg`)

New `okf` subcommand group:
- `dva kg okf init <domain>` — scaffold `knowledge/` + seed `okf.schema.yaml`.
- `dva kg okf generate --domain <slug> [--source ...]` — reuse `parsers.py`;
  LLM emits schema-constrained OKF concept `.md` files instead of Neo4j writes.
- `dva kg okf validate --domain <slug>` — conformance check (frontmatter, link
  targets resolve, only allowed triples, citations). CI-friendly exit codes.
- `dva kg okf compile --domain <slug> --provider neo4j|lightrag` — derive the
  graph/vectors from the bundle (replaces always-on ingest).
- `dva kg okf query --domain <slug>` — answer over the local bundle
  (grep + frontmatter graph walk), no server required.

Refactored internals (`agentic_cli/kg/okf/`):
- Reuse `parsers.py` unchanged.
- Replace free-form prompt in `entity_extraction.py` with a schema-injected
  prompt (types + relationship allowlist) producing OKF docs.
- Fold `linker.py` constrained-prompt logic into the OKF generator as the single
  relationship authority.

Back-compat: existing `dva kg ingest submit` remains, but can internally route
through `okf generate -> okf compile` so existing graph consumers keep working.

## Phased delivery

- **Phase 1 — Schema + writer.** `okf.schema.yaml` model, OKF concept-doc
  reader/writer in `agentic_cli/kg/okf/`, `okf init`. No LLM.
- **Phase 2 — Generation.** Schema-constrained generator reusing parsers;
  `okf generate`. Strict types/links enforced at write time.
- **Phase 3 — Validation.** `okf validate` conformance engine + CI hook in
  domain-meta repos (wire into `.githooks/pre-push`).
- **Phase 4 — Compile/query.** `okf compile` (bundle -> Neo4j/LightRAG) +
  `okf query` (infra-free). Wire bundle into KG MCP so agents read it for dev
  context.
- **Phase 5 — Migration.** Export existing Neo4j graph -> OKF bundle; deprecate
  always-on ingest as the default.
