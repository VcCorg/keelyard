"""Resolve canonical context refs into portable content — best-effort.

Turns engine-neutral references into :class:`ContextItem` objects with real
bodies. Two schemes resolve to content:

- ``okf://<domain>/<concept_id>`` — a concept from the org's OKF bundle.
- ``domain://<slug>/<file>``      — a finalized onboarding instruction file
  from the domain meta-repo's ``.domain/`` directory.

Everything is defensive: if a bundle or its optional deps are unavailable, the
ref is kept as *reference-only* so a bundle can always be produced without a
vendor or a heavy toolchain.

**This module is where context reads are traced.** Retrieval through MCP, the
KG and retrievers was already instrumented; assembling a session's context
bundle was not, so the onboarding material this platform generates was read
without any record that it had been. Every resolution below records one ledger
row under ``source="context"``.

One limit worth stating plainly rather than discovering later: this sees the
context **Keel assembles**. An agent that opens ``.domain/setup.md`` itself,
inside a vendor engine or an IDE, is reading outside anything we mediate and
records nothing. What the ledger answers is "what did Keel put in front of this
session", which is not the same claim as "everything the session read".
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from agentic_cli import tracing
from agentic_cli.context.portable import ContextItem

#: Ledger source family for context assembled by this module.
TRACE_SOURCE = "context"


def _repo_root() -> Path:
    return Path.cwd()


def locate_bundle_dir(domain: str) -> Optional[Path]:
    """Find a domain's OKF bundle dir, preferring the generated export."""
    if not domain:
        return None
    root = _repo_root()
    for candidate in (root / "knowledge-export" / domain,
                      root / "skills" / "domains" / domain / "knowledge"):
        if (candidate / "okf.schema.yaml").exists():
            return candidate
    return None


def _record(operation: str, ref: str, item: Optional[ContextItem]) -> None:
    """Record one context read. Never raises — telemetry is not load-bearing."""
    tracing.record_context_read(
        source=TRACE_SOURCE,
        operation=operation,
        entity_id=ref,
        size_bytes=tracing.measure(item.body if item else ""),
        status="success" if (item and item.resolved) else "empty",
    )


def _parse_domain_ref(ref: str) -> Optional[tuple[str, str]]:
    """``domain://<slug>/<file>`` -> (slug, file); else None."""
    if not ref.startswith("domain://"):
        return None
    slug, _, name = ref[len("domain://"):].partition("/")
    if not slug or not name:
        return None
    return slug, name


def _strip_frontmatter(text: str) -> str:
    """Drop the provenance/reviewed header — it is metadata, not context.

    Feeding it to a model spends tokens on bookkeeping and invites the model to
    quote our own stamps back as domain facts.
    """
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


def _load_domain_item(slug: str, name: str) -> Optional[ContextItem]:
    """Load one finalized ``.domain/`` file — returns None if unavailable."""
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    meta = detect_domain_meta_repo(slug)
    if meta is None:
        return None
    # Resolve under .domain/ and refuse anything that escapes it: a ref is
    # caller-supplied, and "../../.ssh/id_rsa" is a context ref too.
    root = (meta / ".domain").resolve()
    try:
        path = (root / name).resolve()
        path.relative_to(root)
        body = path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None

    # Filler must never be served as context. `domain init` writes
    # "will be populated from the Knowledge Graph" when the KG query returns
    # nothing, and an agent handed that reads it as a statement about the
    # domain. Refusing here is the point of stamping provenance at all: an
    # unresolved ref shows up as a gap in the ledger and in the score, where a
    # confident-sounding placeholder would not.
    from agentic_cli.onboarding import provenance

    # Only *filler* is refused, not merely-unattributed content. A pre-stamping
    # `.domain/` file reads as UNKNOWN provenance, and dropping those would
    # silently empty out every legacy domain — a worse failure than serving
    # real text whose origin we cannot name.
    if provenance.read(path).provenance == provenance.PLACEHOLDER:
        return None

    return ContextItem(
        ref=f"domain://{slug}/{name}",
        title=name,
        body=_strip_frontmatter(body).strip(),
        source=str(path),
    )


def domain_context_refs(slug: str) -> list[str]:
    """Finalized ``.domain/`` files for a domain, as resolvable refs.

    Placeholder files are omitted: the question this answers is "what context
    can this domain actually provide", and a ref that resolves to filler is a
    worse answer than no ref at all. Files that merely lack a provenance stamp
    are kept — unattributed is not the same as empty.
    """
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo
    from agentic_cli.onboarding import provenance

    meta = detect_domain_meta_repo(slug)
    if meta is None:
        return []
    return [f"domain://{slug}/{p.name}"
            for p in sorted((meta / ".domain").glob("*.md"))
            if provenance.read(p).provenance != provenance.PLACEHOLDER]


def _parse_okf_ref(ref: str) -> Optional[tuple[str, str]]:
    """``okf://<domain>/<concept_id>`` -> (domain, concept_id); else None."""
    if not ref.startswith("okf://"):
        return None
    rest = ref[len("okf://"):]
    domain, _, concept = rest.partition("/")
    if not domain or not concept:
        return None
    return domain, concept


def _load_okf_item(domain: str, concept_id: str) -> Optional[ContextItem]:
    """Load a single OKF concept body — returns None if unavailable."""
    try:
        from agentic_cli.kg.okf.bundle import Bundle  # optional deps
    except Exception:  # noqa: BLE001
        return None
    bundle_dir = locate_bundle_dir(domain)
    if not bundle_dir:
        return None
    try:
        bundle = Bundle.load(bundle_dir)
    except Exception:  # noqa: BLE001
        return None
    for c in bundle.concepts.values():
        if getattr(c, "id", "") == concept_id:
            return ContextItem(
                ref=f"okf://{domain}/{concept_id}",
                title=getattr(c, "title", "") or concept_id,
                body=getattr(c, "body", "") or "",
                source=str(bundle_dir),
            )
    return None


def resolve_refs(refs: Iterable[str], default_domain: str = "") -> list[ContextItem]:
    """Resolve each ref to a :class:`ContextItem` (body filled when possible)."""
    items: list[ContextItem] = []
    for ref in refs:
        ref = (ref or "").strip()
        if not ref:
            continue
        okf = _parse_okf_ref(ref)
        if okf:
            loaded = _load_okf_item(*okf)
            _record("resolve/okf", ref, loaded)
            items.append(loaded or ContextItem(ref=ref, title=okf[1], source="unresolved"))
            continue

        domain_ref = _parse_domain_ref(ref)
        if domain_ref:
            loaded = _load_domain_item(*domain_ref)
            _record("resolve/domain", ref, loaded)
            items.append(loaded or ContextItem(ref=ref, title=domain_ref[1], source="unresolved"))
            continue

        # An unrecognised ref resolves to nothing, but it was still asked for —
        # recording it is how a missing source shows up as a gap rather than
        # as silence.
        _record("resolve/external", ref, None)
        items.append(ContextItem(ref=ref, title=ref, source="external"))
    return items


def load_governance(domain: str) -> str:
    """Best-effort domain governance text for the preamble (empty if none)."""
    if not domain:
        return ""
    root = _repo_root()
    for candidate in (root / "skills" / "domains" / domain / "GOVERNANCE.md",
                      root / "skills" / "domains" / domain / "governance.md",
                      root / "knowledge-export" / domain / "GOVERNANCE.md"):
        try:
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8").strip()
                _record("resolve/governance", f"governance://{domain}",
                        ContextItem(ref=domain, body=text))
                return text
        except Exception:  # noqa: BLE001
            continue
    return ""
