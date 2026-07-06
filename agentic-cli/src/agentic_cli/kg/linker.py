"""KG Linker — connect Code::* nodes to Document (requirement) nodes in Neo4j.

This module implements the missing bridge between code context and business context.

Architecture:
  1. Pull Code::* nodes (developer persona) for a domain from Neo4j
  2. Pull Document nodes (business persona) for the same domain from Neo4j
  3. Ingest both into LightRAG for semantic embeddings (if configured)
  4. Query LightRAG for semantic similarity between code and docs
  5. Batch evaluate with Vertex AI: which code implements/references which requirement?
  6. Combine LightRAG similarity scores + LLM evaluation for confidence
  7. Write typed relationship edges back to Neo4j (idempotent via MERGE)

Relationship types:
  IMPLEMENTS  — code directly fulfills a requirement
  REFERENCES  — code uses concepts/vocabulary from the doc
  TESTED_BY   — test class validates a requirement
  CONFIGURES  — config/infra enables a requirement

Usage:
  from agentic_cli.kg.linker import KGLinker
  linker = KGLinker(domain="cwow-facility", use_lightrag=True)
  result = linker.run(dry_run=True)
  result = linker.run()
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from agentic_cli.kg.config import KGConfig
from agentic_cli.kg.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

VALID_RELATIONSHIP_TYPES = {"IMPLEMENTS", "REFERENCES", "TESTED_BY", "CONFIGURES"}

LINK_PROMPT_TEMPLATE = """You are analyzing a healthcare software system (example CWOW platform).

DOMAIN: {domain}

REQUIREMENT DOCUMENTS (OneView specifications):
{docs_section}

CODE ENTITIES to evaluate:
{code_section}

TASK:
For each CODE entity, identify which REQUIREMENT document(s) it implements, references, or tests.
Use these relationship types ONLY:
  - IMPLEMENTS  : code directly fulfills the requirement's functional behaviour
  - REFERENCES  : code uses terminology, data structures, or concepts from the doc
  - TESTED_BY   : this is a test class/method that validates the requirement
  - CONFIGURES  : configuration or infrastructure that enables the requirement

Rules:
  - Only include matches with confidence >= 0.7
  - A single code entity may match multiple requirements
  - Return empty array [] if no confident matches exist for a batch entry
  - Base evidence on actual names, field names, method names, or content overlap

Return ONLY a valid JSON array, no other text, no markdown:
[
  {{
    "code_id": "<exact id from CODE entity>",
    "doc_id": "<exact id from REQUIREMENT document>",
    "relationship": "IMPLEMENTS" | "REFERENCES" | "TESTED_BY" | "CONFIGURES",
    "confidence": <float 0.0-1.0>,
    "evidence": "<one sentence explaining the match>"
  }}
]
"""


@dataclass
class CodeEntity:
    id: str
    name: str
    entity_type: str
    content: str
    domain: Optional[str] = None
    repo: Optional[str] = None


@dataclass
class BusinessDoc:
    id: str
    name: str
    content: str
    title: Optional[str] = None
    domain: Optional[str] = None


@dataclass
class LinkCandidate:
    code_id: str
    doc_id: str
    relationship: str
    confidence: float
    evidence: str


@dataclass
class LinkResult:
    domain: str
    total_code_entities: int
    total_docs: int
    batches_processed: int
    candidates_found: int
    edges_written: int
    dry_run: bool
    skipped_low_confidence: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run_preview: List[Dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Domain:            {self.domain}",
            f"Code entities:     {self.total_code_entities}",
            f"Requirement docs:  {self.total_docs}",
            f"Batches:           {self.batches_processed}",
            f"Candidates found:  {self.candidates_found}",
            f"Low confidence:    {self.skipped_low_confidence} (skipped)",
            f"Edges written:     {'[DRY RUN — none written]' if self.dry_run else self.edges_written}",
        ]
        if self.errors:
            lines.append(f"Errors:            {len(self.errors)}")
        return "\n".join(lines)


class KGLinker:
    """Links Code::* nodes to Document (requirement) nodes in Neo4j via LLM evaluation."""

    def __init__(
        self,
        domain: str,
        config: Optional[KGConfig] = None,
        confidence_threshold: float = 0.75,
        batch_size: int = 50,
        use_lightrag: bool = True,
        lightrag_weight: float = 0.6,
    ):
        self.domain = domain
        self.config = config or KGConfig.load()
        self.confidence_threshold = confidence_threshold
        self.batch_size = batch_size
        self.use_lightrag = use_lightrag
        self.lightrag_weight = lightrag_weight
        self._model = None
        self._lightrag_client = None

    # ── LightRAG client ───────────────────────────────────────────────────────

    def _get_lightrag_client(self):
        """Lazy initialization of LightRAG client."""
        if self._lightrag_client is not None:
            return self._lightrag_client

        if not self.use_lightrag:
            return None

        try:
            from agentic_cli.kg.lightrag_client import LightRAGClient
            self._lightrag_client = LightRAGClient(
                base_url=self.config.lightrag_url,
                timeout=self.config.lightrag_timeout
            )
            logger.info(f"LightRAG client initialized: {self.config.lightrag_url}")
            return self._lightrag_client
        except ImportError as e:
            logger.warning(f"LightRAG client not available: {e}")
            self.use_lightrag = False
            return None
        except Exception as e:
            logger.warning(f"LightRAG client initialization failed: {e}")
            self.use_lightrag = False
            return None

    # ── Vertex AI model ──────────────────────────────────────────────────────

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model

        if not self.config.is_vertex_ai_configured():
            raise ValueError(
                "Vertex AI is not configured. Run `keel init vertex-ai` first.\n"
                f"Config: project_id={self.config.google_project_id}"
            )

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
        except ImportError:
            raise ImportError(
                "Vertex AI packages not installed. "
                "Install with: pip install google-cloud-aiplatform"
            )

        vertexai.init(
            project=self.config.google_project_id,
            location=self.config.google_location,
        )
        self._model = GenerativeModel("gemini-2.5-flash")
        logger.info("Vertex AI model initialized: gemini-2.5-flash")
        return self._model

    # ── Data pull ────────────────────────────────────────────────────────────

    def pull_code_entities(self, client: Neo4jClient) -> List[CodeEntity]:
        """Pull all Code::* nodes tagged with this domain from Neo4j."""
        query = """
        MATCH (n)
        WHERE n._source = 'keel_kg'
          AND n.persona = 'developer'
          AND n.domain = $domain
        RETURN n.id AS id,
               n.name AS name,
               labels(n) AS labels,
               n.content AS content,
               n.domain AS domain
        LIMIT 5000
        """
        records = client.execute_cypher(query, {"domain": self.domain})
        entities = []
        for r in records:
            entity_type = next(
                (lb for lb in (r.get("labels") or []) if lb.startswith("Code")),
                "Code::Entity",
            )
            entities.append(CodeEntity(
                id=r["id"] or "",
                name=r["name"] or "",
                entity_type=entity_type,
                content=(r["content"] or "")[:600],
                domain=r.get("domain"),
                repo=r.get("file_path"),
            ))
        logger.info(f"Pulled {len(entities)} code entities for domain '{self.domain}'")
        return entities

    def pull_business_docs(self, client: Neo4jClient) -> List[BusinessDoc]:
        """Pull all Document nodes tagged with this domain from Neo4j."""
        query = """
        MATCH (n:Document)
        WHERE n._source = 'keel_kg'
          AND n.domain = $domain
        RETURN n.id AS id,
               n.name AS name,
               n.content AS content,
               n.domain AS domain
        LIMIT 500
        """
        records = client.execute_cypher(query, {"domain": self.domain})
        docs = []
        for r in records:
            docs.append(BusinessDoc(
                id=r["id"] or "",
                name=r["name"] or "",
                content=(r["content"] or "")[:500],
                title=r.get("name"),
                domain=r.get("domain"),
            ))
        logger.info(f"Pulled {len(docs)} business docs for domain '{self.domain}'")
        return docs

    # ── LightRAG ingestion ─────────────────────────────────────────────────────

    def _ingest_to_lightrag(self, entities: List[Any], entity_type: str) -> bool:
        """Ingest entities into LightRAG for semantic embeddings.

        Args:
            entities: List of CodeEntity or BusinessDoc objects
            entity_type: 'code' or 'doc'

        Returns:
            True if successful, False otherwise
        """
        client = self._get_lightrag_client()
        if not client:
            logger.warning("LightRAG client not available, skipping ingestion")
            return False

        logger.info(f"Ingesting {len(entities)} {entity_type} entities into LightRAG...")
        success_count = 0

        for entity in entities:
            try:
                # Build document text
                if entity_type == 'code':
                    text = f"Code: {entity.name}\nType: {entity.entity_type}\nContent: {entity.content}"
                    metadata = {
                        "id": entity.id,
                        "type": "code",
                        "domain": self.domain,
                        "entity_type": entity.entity_type,
                    }
                else:  # doc
                    text = f"Document: {entity.name}\nTitle: {entity.title}\nContent: {entity.content}"
                    metadata = {
                        "id": entity.id,
                        "type": "document",
                        "domain": self.domain,
                    }

                client.insert(text, metadata)
                success_count += 1

            except Exception as e:
                logger.warning(f"Failed to ingest {entity_type} entity {entity.id}: {e}")
                continue

        logger.info(f"Ingested {success_count}/{len(entities)} {entity_type} entities into LightRAG")
        return success_count > 0

    # ── LightRAG semantic similarity ───────────────────────────────────────────

    def _query_lightrag_similarity(
        self,
        code_entity: CodeEntity,
        docs: List[BusinessDoc]
    ) -> Dict[str, float]:
        """Query LightRAG for semantic similarity between code and docs.

        Args:
            code_entity: Code entity to query
            docs: List of business docs to compare against

        Returns:
            Dict mapping doc_id to similarity score (0.0-1.0)
        """
        client = self._get_lightrag_client()
        if not client:
            return {}

        similarity_scores = {}

        for doc in docs:
            try:
                # Use LightRAG search to find semantic similarity
                query_text = f"Code: {code_entity.name}\n{code_entity.content}"
                result = client.search(query_text, top_k=5)

                # Parse results to find matching doc
                if result and 'results' in result:
                    for item in result['results']:
                        doc_text = item.get('text', '')
                        # Check if this result matches our doc
                        if doc.id in doc_text or doc.name in doc_text:
                            similarity_scores[doc.id] = item.get('score', 0.5)
                            break

            except Exception as e:
                logger.warning(f"LightRAG similarity query failed for {code_entity.id}: {e}")
                continue

        return similarity_scores

    # ── Prompt building ───────────────────────────────────────────────────────

    def _build_docs_section(self, docs: List[BusinessDoc]) -> str:
        lines = []
        for doc in docs:
            display = doc.title or doc.name
            lines.append(f"[REQ:{doc.id}] {display}")
            if doc.content.strip():
                lines.append(f"  Summary: {doc.content[:400]}")
            lines.append("  ---")
        return "\n".join(lines)

    def _build_code_section(self, batch: List[CodeEntity]) -> str:
        lines = []
        for entity in batch:
            repo_hint = f" (repo: {entity.repo})" if entity.repo else ""
            lines.append(f"[CODE:{entity.id}] {entity.entity_type}: {entity.name}{repo_hint}")
            if entity.content.strip():
                lines.append(f"  Content: {entity.content[:300]}")
            lines.append("  ---")
        return "\n".join(lines)

    def _build_prompt(self, batch: List[CodeEntity], docs: List[BusinessDoc]) -> str:
        return LINK_PROMPT_TEMPLATE.format(
            domain=self.domain,
            docs_section=self._build_docs_section(docs),
            code_section=self._build_code_section(batch),
        )

    # ── LLM evaluation ────────────────────────────────────────────────────────

    def _parse_llm_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse JSON from LLM response, stripping markdown fences if present."""
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        return json.loads(text)

    def _evaluate_batch(
        self,
        batch: List[CodeEntity],
        docs: List[BusinessDoc],
    ) -> Tuple[List[LinkCandidate], int]:
        """
        Call Vertex AI to evaluate one batch of code entities against all docs.
        Combines LightRAG semantic similarity with LLM evaluation if configured.
        Returns (candidates_above_threshold, skipped_low_confidence_count).
        """
        model = self._get_model()
        prompt = self._build_prompt(batch, docs)

        # Get LightRAG similarity scores if configured
        lightrag_scores = {}
        if self.use_lightrag:
            logger.info("Querying LightRAG for semantic similarity...")
            for entity in batch:
                lightrag_scores[entity.id] = self._query_lightrag_similarity(entity, docs)

        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
        except Exception as e:
            logger.error(f"Vertex AI call failed: {e}")
            raise

        try:
            items = self._parse_llm_response(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}\nRaw: {raw[:300]}")
            return [], 0

        candidates = []
        skipped = 0
        for item in items:
            rel = item.get("relationship", "").upper()
            if rel not in VALID_RELATIONSHIP_TYPES:
                rel = "REFERENCES"

            code_id = str(item.get("code_id", "")).replace("CODE:", "")
            doc_id = str(item.get("doc_id", "")).replace("REQ:", "")

            # Combine LLM confidence with LightRAG similarity
            llm_confidence = float(item.get("confidence", 0.0))
            lightrag_score = lightrag_scores.get(code_id, {}).get(doc_id, 0.0)

            if self.use_lightrag and lightrag_score > 0:
                # Hybrid scoring: weighted average
                combined_confidence = (
                    self.lightrag_weight * lightrag_score +
                    (1 - self.lightrag_weight) * llm_confidence
                )
                logger.debug(f"Hybrid score for {code_id}→{doc_id}: "
                           f"LightRAG={lightrag_score:.2f}, LLM={llm_confidence:.2f}, "
                           f"Combined={combined_confidence:.2f}")
                confidence = combined_confidence
            else:
                confidence = llm_confidence

            if confidence < self.confidence_threshold:
                skipped += 1
                continue

            candidates.append(LinkCandidate(
                code_id=code_id,
                doc_id=doc_id,
                relationship=rel,
                confidence=confidence,
                evidence=str(item.get("evidence", "")),
            ))

        return candidates, skipped

    # ── Neo4j edge writing ────────────────────────────────────────────────────

    def _write_edges(self, candidates: List[LinkCandidate], client: Neo4jClient) -> int:
        """Write MERGE edges for all candidates. Returns count of edges written."""
        now = datetime.now(timezone.utc).isoformat()
        written = 0

        for c in candidates:
            query = f"""
            MATCH (code {{id: $code_id}}), (doc {{id: $doc_id}})
            MERGE (code)-[r:{c.relationship}]->(doc)
            ON CREATE SET
                r.confidence   = $confidence,
                r.evidence     = $evidence,
                r.linked_by    = 'keel-kg-link',
                r.domain       = $domain,
                r.created_at   = $now,
                r.updated_at   = $now
            ON MATCH SET
                r.confidence   = $confidence,
                r.evidence     = $evidence,
                r.updated_at   = $now
            RETURN r
            """
            try:
                result = client.execute_cypher(query, {
                    "code_id": c.code_id,
                    "doc_id": c.doc_id,
                    "confidence": c.confidence,
                    "evidence": c.evidence,
                    "domain": self.domain,
                    "now": now,
                })
                if result:
                    written += 1
            except Exception as e:
                logger.warning(
                    f"Failed to write edge {c.code_id} -[{c.relationship}]-> {c.doc_id}: {e}"
                )

        return written

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self, dry_run: bool = False) -> LinkResult:
        """
        Execute the full linking pipeline for this domain.

        Args:
            dry_run: If True, evaluate and report candidates but do not write edges.

        Returns:
            LinkResult with full statistics.
        """
        result = LinkResult(
            domain=self.domain,
            total_code_entities=0,
            total_docs=0,
            batches_processed=0,
            candidates_found=0,
            edges_written=0,
            dry_run=dry_run,
        )

        with Neo4jClient(self.config) as client:
            # Step 1: pull both sides
            code_entities = self.pull_code_entities(client)
            business_docs = self.pull_business_docs(client)

            result.total_code_entities = len(code_entities)
            result.total_docs = len(business_docs)

            if not code_entities:
                result.errors.append(
                    f"No code entities found for domain '{self.domain}'. "
                    "Run `keel code onboard --kg --extract-entities` first."
                )
                return result

            if not business_docs:
                result.errors.append(
                    f"No business docs found for domain '{self.domain}'. "
                    "Run `keel kg ingest submit --domain {self.domain} --format confluence` first."
                )
                return result

            # Step 2: ingest into LightRAG if configured
            if self.use_lightrag:
                logger.info("Ingesting entities into LightRAG for semantic search...")
                code_ingested = self._ingest_to_lightrag(code_entities, 'code')
                docs_ingested = self._ingest_to_lightrag(business_docs, 'doc')
                if code_ingested and docs_ingested:
                    logger.info("LightRAG ingestion completed successfully")
                else:
                    logger.warning("LightRAG ingestion incomplete, falling back to LLM-only")
                    self.use_lightrag = False

            # Step 2: batch evaluate
            all_candidates: List[LinkCandidate] = []
            total_skipped = 0

            for i in range(0, len(code_entities), self.batch_size):
                batch = code_entities[i: i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(code_entities) + self.batch_size - 1) // self.batch_size
                logger.info(f"Evaluating batch {batch_num}/{total_batches} ({len(batch)} entities)...")

                try:
                    candidates, skipped = self._evaluate_batch(batch, business_docs)
                    all_candidates.extend(candidates)
                    total_skipped += skipped
                    result.batches_processed += 1
                except Exception as e:
                    msg = f"Batch {batch_num} failed: {e}"
                    logger.error(msg)
                    result.errors.append(msg)
                    continue

            result.candidates_found = len(all_candidates)
            result.skipped_low_confidence = total_skipped

            # Step 3: write or preview
            if dry_run:
                result.dry_run_preview = [
                    {
                        "code_id": c.code_id,
                        "doc_id": c.doc_id,
                        "relationship": c.relationship,
                        "confidence": c.confidence,
                        "evidence": c.evidence,
                    }
                    for c in all_candidates[:50]
                ]
            else:
                result.edges_written = self._write_edges(all_candidates, client)

        return result
