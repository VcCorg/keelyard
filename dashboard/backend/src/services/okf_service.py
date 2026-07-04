"""OKF bundle service — thin proxy over agentic_cli.kg.okf.

Design principle (mirrors kg_ingest_service.py / domain_service.py):
- Reads (list bundles, validate, trace) import the CLI's `agentic_cli.kg.okf`
  package directly — fast, no subprocess.
- The long-running `okf export` (which reads the live Neo4j graph) is executed
  by shelling out to the real `dva kg okf export ...` and streaming its stdout,
  so all export logic lives in exactly one place.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

# Repo root: .../dashboard/backend/src/services/okf_service.py -> parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
# Hand-authored bundles live alongside the domain skills; generated exports go
# to a separate top-level dir so a UI "Generate" never overwrites authored work.
DOMAINS_DIR = REPO_ROOT / "skills" / "domains"
EXPORT_DIR = REPO_ROOT / "knowledge-export"

SOURCE_AUTHORED = "authored"
SOURCE_EXPORT = "export"


# ── Transport models ─────────────────────────────────────────────────────────

class OKFBundleInfo(BaseModel):
    domain: str
    source: str = SOURCE_EXPORT  # "authored" | "export"
    product: str = ""
    path: str
    exists: bool = False
    concepts: int = 0
    freqs: int = 0
    has_report: bool = False
    # Freshness vs the repos' code graphs (provenance-based).
    freshness: str = "n/a"            # "fresh" | "stale" | "unknown" | "n/a"
    stale_repos: list[str] = []
    enriched_at: Optional[str] = None


class OKFFreqRow(BaseModel):
    freq_id: str
    title: str
    dev_gap: bool
    qa_gap: bool
    acceptance_criteria: int = 0


class OKFValidation(BaseModel):
    ok: bool = False
    concepts: int = 0
    links: int = 0
    typed_links: int = 0
    error_count: int = 0
    errors: list[str] = []


class OKFBundleDetail(BaseModel):
    info: OKFBundleInfo
    validation: OKFValidation
    freqs: list[OKFFreqRow] = []
    gap_count: int = 0
    unmapped_labels: int = 0
    unmapped_rels: int = 0
    quarantined_triples: int = 0


# ── Path helpers ─────────────────────────────────────────────────────────────

def bundle_dir(domain: str, source: str = SOURCE_EXPORT) -> Path:
    if source == SOURCE_AUTHORED:
        return DOMAINS_DIR / domain / "knowledge"
    return EXPORT_DIR / domain


def _schema_path(domain: str, source: str) -> Path:
    return bundle_dir(domain, source) / "okf.schema.yaml"


# ── Reads (library import) ───────────────────────────────────────────────────

def _bundle_info(domain: str, source: str = SOURCE_EXPORT) -> OKFBundleInfo:
    bdir = bundle_dir(domain, source)
    schema = _schema_path(domain, source)
    info = OKFBundleInfo(domain=domain, source=source, path=str(bdir), exists=schema.exists())
    if not schema.exists():
        return info
    try:
        import yaml
        raw = yaml.safe_load(schema.read_text(encoding="utf-8")) or {}
        info.product = raw.get("product", "") or ""
    except Exception:
        pass
    concepts_dir = bdir / "concepts"
    if concepts_dir.exists():
        files = list(concepts_dir.rglob("*.md"))
        info.concepts = len(files)
        info.freqs = sum(1 for f in files if f.name.startswith("freq-"))
    info.has_report = (bdir / "nonconforming-report.md").exists()
    _attach_freshness(info, bdir)
    return info


def _attach_freshness(info: OKFBundleInfo, bdir: Path) -> None:
    """Populate freshness fields from the bundle's provenance (best-effort).

    Only bundles stamped at enrich time carry ``.okf-provenance.json``. We
    re-hash each linked repo's current graph and compare. Any failure leaves the
    default ``freshness='n/a'`` so listing never breaks.
    """
    try:
        from agentic_cli.kg.okf.provenance import PROVENANCE_FILE, check_freshness
        if not (bdir / PROVENANCE_FILE).exists():
            return
        from agentic_cli.kg.okf.enrichment.domain_paths import (
            resolve_domain_enrichment_context,
        )
        ctx = resolve_domain_enrichment_context(info.domain)
        report = check_freshness(bdir, ctx.codebase_paths)
        info.enriched_at = report.enriched_at
        if not report.has_provenance:
            info.freshness = "unknown"
        else:
            info.freshness = "stale" if report.stale else "fresh"
            info.stale_repos = report.stale_repos
    except Exception:
        info.freshness = "unknown"


def list_okf_bundles() -> list[OKFBundleInfo]:
    """List OKF bundles from both the authored and export locations."""
    out: list[OKFBundleInfo] = []
    if DOMAINS_DIR.exists():
        for child in sorted(DOMAINS_DIR.iterdir()):
            if child.is_dir() and (child / "knowledge" / "okf.schema.yaml").exists():
                out.append(_bundle_info(child.name, SOURCE_AUTHORED))
    if EXPORT_DIR.exists():
        for child in sorted(EXPORT_DIR.iterdir()):
            if child.is_dir() and (child / "okf.schema.yaml").exists():
                out.append(_bundle_info(child.name, SOURCE_EXPORT))
    return out


def _parse_report_counts(domain: str, source: str) -> tuple[int, int, int]:
    """(unmapped_labels, unmapped_rels, quarantined_triples) from the report."""
    report = bundle_dir(domain, source) / "nonconforming-report.md"
    if not report.exists():
        return 0, 0, 0
    text = report.read_text(encoding="utf-8")
    sections = re.split(r"^## ", text, flags=re.MULTILINE)
    labels = rels = triples = 0
    for sec in sections:
        bullets = len([ln for ln in sec.splitlines() if ln.strip().startswith("- ")
                       and "none" not in ln.lower()])
        head = sec.splitlines()[0].lower() if sec.splitlines() else ""
        if "node labels" in head:
            labels = bullets
        elif "relationship types" in head:
            rels = bullets
        elif "triples" in head:
            triples = bullets
    return labels, rels, triples


def validate_okf_bundle(domain: str, source: str = SOURCE_EXPORT) -> OKFValidation:
    from agentic_cli.kg.okf.validate import validate_bundle

    bdir = bundle_dir(domain, source)
    if not (bdir / "okf.schema.yaml").exists():
        return OKFValidation(ok=False, error_count=1, errors=[f"No OKF bundle for '{domain}' ({source})"])
    rep = validate_bundle(bdir)
    return OKFValidation(
        ok=rep.ok,
        concepts=rep.concepts,
        links=rep.links,
        typed_links=rep.typed_links,
        error_count=len(rep.errors),
        errors=rep.errors[:100],
    )


def get_okf_bundle_detail(domain: str, source: str = SOURCE_EXPORT) -> OKFBundleDetail:
    from agentic_cli.kg.okf.trace import trace_bundle

    info = _bundle_info(domain, source)
    validation = validate_okf_bundle(domain, source)
    freqs: list[OKFFreqRow] = []
    gap_count = 0
    if info.exists:
        try:
            report = trace_bundle(bundle_dir(domain, source))
            gap_count = report.gap_count
            for f in report.freqs:
                freqs.append(OKFFreqRow(
                    freq_id=f.freq_id, title=f.title,
                    dev_gap=f.dev_gap, qa_gap=f.qa_gap,
                    acceptance_criteria=len(f.acceptance_criteria),
                ))
        except Exception:
            pass
    labels, rels, triples = _parse_report_counts(domain, source)
    return OKFBundleDetail(
        info=info, validation=validation, freqs=freqs, gap_count=gap_count,
        unmapped_labels=labels, unmapped_rels=rels, quarantined_triples=triples,
    )


# ── Export (subprocess + streaming, reuses kg_ingest_service) ────────────────

def okf_export_args(
    domain: str,
    product: Optional[str] = None,
    mint_freqs: bool = True,
) -> list[str]:
    """Build args for `dva kg okf export ...` (consumed by stream_kg_command)."""
    out = bundle_dir(domain, SOURCE_EXPORT)
    args = ["okf", "export", "--domain", domain, "--out", str(out)]
    if product:
        args += ["--product", product]
    args += ["--mint-freqs"] if mint_freqs else ["--no-mint-freqs"]
    return args


def okf_enrich_args(
    domain: str,
    source: str = "both",
    code_source: str = "auto",
    generate_graphs: bool = True,
    no_confluence: bool = False,
    model: Optional[str] = None,
    dry_run: bool = False,
) -> list[str]:
    """Build args for `dva kg okf enrich ...` (consumed by stream_kg_command).

    This is the structural (graphify, no-LLM by default via --code-source auto)
    + Confluence enrichment path. Unlike export, it resolves all repo/doc inputs
    from the registered domain and writes to the AUTHORED bundle location.
    """
    args = ["okf", "enrich", "--domain", domain, "--source", source,
            "--code-source", code_source]
    args += ["--generate-graphs"] if generate_graphs else ["--no-generate-graphs"]
    if no_confluence:
        args += ["--no-confluence"]
    if model:
        args += ["--model", model]
    if dry_run:
        args += ["--dry-run"]
    return args


def domain_busy(domain: str) -> bool:
    """True if a per-domain OKF lock is currently held (enrich/export/sync running).

    Best-effort: leverages the CLI's machine-scoped advisory lock so the dashboard
    can reject a concurrent run before starting one. The CLI lock remains the
    authoritative guard against bundle corruption.
    """
    try:
        from agentic_cli.kg.okf.locking import is_locked
        return is_locked(domain, scope="okf")
    except Exception:
        return False


def devin_api_key_present() -> bool:
    """True if a Devin API key is available to the backend process (for live push)."""
    return bool(os.environ.get("DEVIN_API_KEY"))


def okf_push_devin_args(
    domain: str,
    source: str = SOURCE_EXPORT,
    types: str = "FREQ,Requirement",
    dry_run: bool = True,
) -> list[str]:
    """Build args for `dva kg okf push-devin ...` (consumed by stream_kg_command).

    The API key is NEVER passed as an argument — the CLI reads $DEVIN_API_KEY
    from the (inherited) process environment so it is never logged in URLs.
    """
    bdir = bundle_dir(domain, source)
    args = ["okf", "push-devin", "--bundle", str(bdir), "--types", types]
    if dry_run:
        args += ["--dry-run"]
    return args


# ── Projection status (canonical → Devin drift + provenance) ─────────────────

class ProjectionEntry(BaseModel):
    concept_id: str
    name: str
    source_ref: str                 # canonical ref, e.g. okf://payments/features/...
    state: str                      # in_sync | drift | unprojected | orphan
    knowledge_id: Optional[str] = None
    version: int = 0
    synced_at: Optional[str] = None


class ProjectionStatusModel(BaseModel):
    domain: str
    source: str = SOURCE_EXPORT
    exists: bool = False
    state: str = "empty"            # in_sync | drift | unprojected | empty
    total_canonical: int = 0
    projected: int = 0
    in_sync: int = 0
    drift: int = 0
    unprojected: int = 0
    orphan: int = 0
    entries: list[ProjectionEntry] = []


def projection_status(domain: str, source: str = SOURCE_EXPORT,
                      types: str = "FREQ,Requirement") -> ProjectionStatusModel:
    """Read how the canonical OKF bundle maps onto its Devin projection.

    Pure/local (no Devin API): delegates to the CLI's ``projection_status`` which
    compares the current bundle against ``.devin-sync.json`` to classify drift,
    unprojected concepts, and orphans. The CLI is the source of truth for the
    computation; the dashboard is a lens.
    """
    bdir = bundle_dir(domain, source)
    if not (bdir / "okf.schema.yaml").exists():
        return ProjectionStatusModel(domain=domain, source=source, exists=False)

    from agentic_cli.kg.okf.devin import projection_status as cli_projection_status

    type_tuple = tuple(t.strip() for t in types.split(",") if t.strip())
    st = cli_projection_status(bdir, type_tuple)
    return ProjectionStatusModel(
        domain=domain, source=source, exists=True, state=st.state,
        total_canonical=st.total_canonical, projected=st.projected,
        in_sync=st.in_sync, drift=st.drift, unprojected=st.unprojected, orphan=st.orphan,
        entries=[
            ProjectionEntry(
                concept_id=e.concept_id, name=e.name, source_ref=e.source_ref,
                state=e.state, knowledge_id=e.knowledge_id, version=e.version,
                synced_at=e.synced_at or None,
            ) for e in st.entries
        ],
    )


# ── Devin Knowledge management (in-process API calls) ────────────────────────

class DevinKnowledgeItem(BaseModel):
    id: str
    name: str
    body: str = ""
    trigger_description: str = ""
    pinned_repo: Optional[str] = None
    parent_folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class DevinKnowledgeUpdate(BaseModel):
    """Partial update — only provided fields are changed."""
    name: Optional[str] = None
    body: Optional[str] = None
    trigger_description: Optional[str] = None
    pinned_repo: Optional[str] = None
    parent_folder_id: Optional[str] = None


class DevinFolder(BaseModel):
    id: str
    name: str
    description: str = ""


class DevinKnowledgeList(BaseModel):
    folders: list[DevinFolder] = []
    knowledge: list[DevinKnowledgeItem] = []


def devin_list_knowledge() -> DevinKnowledgeList:
    """List all Devin Knowledge entries + folders (live API, in-process)."""
    from agentic_cli.kg.okf.devin import list_entries

    data = list_entries()
    folders = [DevinFolder(id=f.get("id", ""), name=f.get("name", ""),
                           description=f.get("description") or "")
               for f in data.get("folders", [])]
    folder_by_id = {f.id: f.name for f in folders}
    items: list[DevinKnowledgeItem] = []
    for k in data.get("knowledge", []):
        cb = k.get("created_by") or {}
        items.append(DevinKnowledgeItem(
            id=k.get("id", ""),
            name=k.get("name", ""),
            body=k.get("body", "") or "",
            trigger_description=k.get("trigger_description", "") or "",
            pinned_repo=k.get("pinned_repo"),
            parent_folder_id=k.get("parent_folder_id"),
            folder_name=folder_by_id.get(k.get("parent_folder_id")),
            created_by=(cb.get("full_name") if isinstance(cb, dict) else None),
            created_at=k.get("created_at"),
        ))
    return DevinKnowledgeList(folders=folders, knowledge=items)


def devin_delete_knowledge(note_id: str) -> None:
    from agentic_cli.kg.okf.devin import delete_entries

    _, failed = delete_entries([note_id])
    if failed:
        raise RuntimeError(failed[0][1])


def devin_bulk_delete(note_ids: list[str]) -> dict:
    """Delete several entries; returns ``{deleted: [...], failed: [[id, err], ...]}``."""
    from agentic_cli.kg.okf.devin import delete_entries

    deleted, failed = delete_entries(note_ids)
    return {"deleted": deleted, "failed": [list(f) for f in failed]}


def devin_move_knowledge(note_id: str, folder_id: Optional[str]) -> None:
    from agentic_cli.kg.okf.devin import move_entry

    move_entry(note_id, folder_id or None)


def devin_update_knowledge(note_id: str, update: "DevinKnowledgeUpdate") -> None:
    """Partial update — only the fields explicitly set in ``update`` are changed."""
    from agentic_cli.kg.okf.devin import update_entry

    fields = update.model_dump(exclude_unset=True)
    if not fields:
        raise RuntimeError("No fields provided to update.")
    update_entry(note_id, fields)
