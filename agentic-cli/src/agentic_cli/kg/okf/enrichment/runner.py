"""Two-pass OKF enrichment runner (Vertex AI Gemini).

Pass 1 (structural): for each concept a `Source` advertises, ask the model to
write one conformant OKF document from the raw metadata.

Pass 2 (enrichment): for each tracked Confluence page, ask the model which
existing concept(s) to augment (or whether to mint a `references/<slug>` doc),
enforcing the augmentation guard so structured sections never shrink.

After both passes, regenerate OKF §6 `index.md` files across the bundle.

The model is obtained from `agentic_cli.agents.onboard.models.init_model`, so it
shares Vertex AI configuration (project/location) with the rest of the CLI. No
external agent framework (ADK) is required.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic_cli.kg.okf.enrichment.prompts import enrichment_prompt, structural_prompt
from agentic_cli.kg.okf.enrichment.source import ConceptRef, Source
from agentic_cli.kg.okf.enrichment.sources.confluence import ConfluenceSource
from agentic_cli.kg.okf.enrichment.tools.bundle_tools import (
    read_existing_doc,
    write_concept_doc,
)
from agentic_cli.kg.okf.model import Concept

log = logging.getLogger(__name__)

_RESERVED = {"index.md", "log.md", "okf.schema.yaml", "nonconforming.md"}


@dataclass
class EnrichResult:
    bundle_root: Path
    concepts_written: int = 0
    concepts_enriched: int = 0
    pages_processed: int = 0
    skipped: int = 0
    guard_blocks: int = 0
    errors: list[str] = field(default_factory=list)
    planned: list[dict[str, Any]] = field(default_factory=list)  # dry-run preview


def _parse_json(text: str) -> Any:
    """Parse JSON from a model response, tolerating markdown fences."""
    from agentic_cli.agents.onboard.models import parse_json_response
    return parse_json_response(text)


class EnrichmentRunner:
    def __init__(
        self,
        source: Source,
        bundle_root: Path,
        model: Any | None = None,
        model_name: str | None = None,
        confluence_source: ConfluenceSource | None = None,
        dry_run: bool = False,
    ):
        self.source = source
        self.bundle_root = Path(bundle_root)
        self.confluence_source = confluence_source
        self.dry_run = dry_run
        self._model = model
        self._model_name = model_name
        self.bundle_root.mkdir(parents=True, exist_ok=True)

    # -- model (lazy) -----------------------------------------------------
    @property
    def model(self) -> Any:
        if self._model is None:
            from agentic_cli.agents.onboard.models import init_model
            self._model = init_model(model_name=self._model_name)
        return self._model

    def _generate(self, prompt: str) -> str:
        resp = self.model.generate_content(prompt)
        return getattr(resp, "text", "") or ""

    # -- Pass 1: structural ----------------------------------------------
    def run_structural(self, only: list[tuple[str, ...]] | None = None) -> EnrichResult:
        result = EnrichResult(bundle_root=self.bundle_root)
        concepts = self.source.list_concepts()
        if only is not None:
            wanted = set(only)
            concepts = [c for c in concepts if c.id in wanted]

        for ref in concepts:
            try:
                raw = self.source.read_concept(ref)
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"{ref.id_str}: read failed: {e}")
                continue

            if self.dry_run:
                result.planned.append({"concept_id": ref.id_str, "type": ref.type, "pass": "structural"})
                continue

            try:
                out = self._parse_concept(ref, raw)
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"{ref.id_str}: model/parse failed: {e}")
                continue

            fm = {
                "type": ref.type,
                "title": out.get("title") or ref.id[-1],
                "description": out.get("description") or "",
                "tags": out.get("tags") or [],
            }
            if ref.resource:
                fm["resource"] = ref.resource
            res = write_concept_doc(self.bundle_root, ref.id_str, fm, out.get("body") or "")
            if "error" in res:
                result.errors.append(f"{ref.id_str}: {res['error']}")
            else:
                result.concepts_written += 1
                log.info("wrote %s (%d bytes)", res["path"], res["bytes"])

        return result

    def _parse_concept(self, ref: ConceptRef, raw: dict[str, Any]) -> dict[str, Any]:
        text = self._generate(structural_prompt(ref.id_str, ref.type, raw))
        data = _parse_json(text)
        if not isinstance(data, dict):
            raise ValueError("model did not return a JSON object")
        return data

    # -- Pass 2: enrichment from Confluence ------------------------------
    def run_enrichment(self, result: EnrichResult | None = None) -> EnrichResult:
        result = result or EnrichResult(bundle_root=self.bundle_root)
        if not self.confluence_source or not self.confluence_source.page_ids:
            return result

        index = self._concept_index()
        for pid in self.confluence_source.page_ids:
            page = self.confluence_source.fetch_page(pid)
            if page.get("error"):
                result.errors.append(f"confluence:{pid}: {page['error']}")
                continue
            result.pages_processed += 1

            if self.dry_run:
                result.planned.append({"page_id": pid, "title": page.get("title", ""), "pass": "enrichment"})
                continue

            try:
                plan = _parse_json(self._generate(enrichment_prompt(page, index)))
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"confluence:{pid}: model/parse failed: {e}")
                continue

            actions = plan.get("actions", []) if isinstance(plan, dict) else []
            if not actions:
                result.skipped += 1
                continue

            for act in actions:
                self._apply_enrichment(act, page, result)
                # refresh index after potential new concept
            index = self._concept_index()

        return result

    def _apply_enrichment(self, act: dict[str, Any], page: dict[str, Any], result: EnrichResult) -> None:
        cid = (act.get("concept_id") or "").strip().strip("/")
        if not cid:
            return
        ctype = act.get("type") or "Requirement"
        existing = read_existing_doc(self.bundle_root, cid)
        is_new = existing is None

        fm = {
            "type": ctype,
            "title": act.get("title") or cid.split("/")[-1],
            "description": act.get("description") or "",
            "tags": act.get("tags") or [],
            "resource": page.get("url") or f"confluence://{page.get('page_id')}",
        }
        res = write_concept_doc(
            self.bundle_root, cid, fm, act.get("body") or "",
            enforce_guard=not is_new,
        )
        if "error" in res:
            result.guard_blocks += 1
            result.errors.append(f"{cid}: {res['error']}")
        elif is_new:
            result.concepts_written += 1
        else:
            result.concepts_enriched += 1

    def _concept_index(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for p in sorted(self.bundle_root.rglob("*.md")):
            if p.name in _RESERVED:
                continue
            c = Concept.read(p, self.bundle_root)
            if c is None:
                continue
            out.append({"id": c.id, "type": c.type, "title": c.title})
        return out

    # -- full pipeline ----------------------------------------------------
    def enrich_all(self, only: list[tuple[str, ...]] | None = None) -> EnrichResult:
        result = self.run_structural(only=only)
        self.run_enrichment(result)
        if not self.dry_run:
            regenerate_indexes(self.bundle_root)
        return result


# ── OKF §6 index regeneration (directory-walking, layout-agnostic) ───────────
def regenerate_indexes(bundle_root: Path) -> int:
    """(Re)write an index.md in every directory that holds concepts/subdirs.

    Index files carry NO frontmatter except the bundle root, which MAY declare
    `okf_version` (OKF §6/§11). Returns the number of index files written.
    """
    bundle_root = Path(bundle_root)
    written = 0
    for d in sorted({p.parent for p in bundle_root.rglob("*.md")} | {bundle_root}):
        if not d.is_dir():
            continue
        concepts: list[tuple[str, str, str]] = []  # (filename, title, desc)
        subdirs: list[str] = []
        for child in sorted(d.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                if any(child.rglob("*.md")):
                    subdirs.append(child.name)
            elif child.is_file() and child.suffix == ".md" and child.name not in _RESERVED:
                c = Concept.read(child, bundle_root)
                if c is None:
                    continue
                concepts.append((child.name, c.title, str(c.fm.get("description", ""))))

        if not concepts and not subdirs:
            continue

        lines: list[str] = []
        is_root = d == bundle_root
        if is_root:
            lines += ["---", "okf_version: '0.1'", "---", ""]
        lines.append(f"# {d.name if not is_root else bundle_root.name} — index")
        lines.append("")
        if subdirs:
            lines.append("# Sections")
            for sd in subdirs:
                lines.append(f"* [{sd}/]({sd}/)")
            lines.append("")
        if concepts:
            lines.append("# Concepts")
            for fname, title, desc in concepts:
                suffix = f" - {desc}" if desc else ""
                lines.append(f"* [{title}]({fname}){suffix}")
            lines.append("")
        (d / "index.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        written += 1
    return written
