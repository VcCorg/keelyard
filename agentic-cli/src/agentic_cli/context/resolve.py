"""Resolve canonical context refs into portable content — best-effort.

Turns engine-neutral references into :class:`ContextItem` objects with real
bodies. Two schemes resolve to content:

- ``okf://<domain>/<concept_id>`` — a concept from the org's OKF bundle.
- ``domain://<slug>/<file>``      — a finalized onboarding instruction file
  from the domain meta-repo's ``.domain/`` directory.

Everything is defensive: if a bundle or its optional deps are unavailable, the
ref is kept as *reference-only* so a bundle can always be produced without a
vendor or a heavy toolchain.

**Fetching and tracing now happen in** :mod:`agentic_cli.retrieval`. This module
used to walk an ``if okf:… elif domain:…`` chain and record each arm itself,
which made it the third place in the codebase that knew how to read a source and
the only one that traced. It is now a thin adapter: refs go to the seam, and what
comes back is shaped into the :class:`ContextItem` the bundle format wants.

One limit worth stating plainly rather than discovering later: this sees the
context **Keel assembles**. An agent that opens ``.domain/setup.md`` itself,
inside a vendor engine or an IDE, is reading outside anything we mediate and
records nothing. What the ledger answers is "what did Keel put in front of this
session", which is not the same claim as "everything the session read".
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from agentic_cli import retrieval, tracing  # noqa: F401  (tracing: patched in tests)
from agentic_cli.context.portable import ContextItem

#: Ledger source family for context assembled by this module.
TRACE_SOURCE = retrieval.CONTEXT_SOURCE


def _as_item(fetched: retrieval.Fetched, ref: str) -> ContextItem:
    """Shape one fetch result into the bundle's context item.

    An unresolved ref still becomes an item. Dropping it would make a bundle
    quietly smaller than the one that was asked for, and the caller would have
    no way to tell a ref that resolved to nothing from a ref that was never in
    the spec. ``source`` carries why, so a rendered bundle says so on its face.
    """
    if fetched.resolved:
        return ContextItem(ref=ref, title=fetched.title or ref,
                           body=fetched.text, source=fetched.origin)
    title = fetched.title or Path(retrieval.parse_ref(ref).path or ref).name or ref
    source = "external" if fetched.status == retrieval.UNSUPPORTED else "unresolved"
    return ContextItem(ref=ref, title=title, body="", source=source)


def resolve_refs(refs: Iterable[str], default_domain: str = "") -> list[ContextItem]:
    """Resolve each ref to a :class:`ContextItem` (body filled when possible)."""
    items: list[ContextItem] = []
    for raw in refs:
        ref = (raw or "").strip()
        if not ref:
            continue
        items.append(_as_item(retrieval.fetch(ref, source=TRACE_SOURCE), ref))
    return items


def domain_context_refs(slug: str) -> list[str]:
    """Finalized ``.domain/`` files for a domain, as resolvable refs.

    Placeholder files are omitted: the question this answers is "what context
    can this domain actually provide", and a ref that resolves to filler is a
    worse answer than no ref at all. Files that merely lack a provenance stamp
    are kept — unattributed is not the same as empty.

    This lists rather than reads, so it does not go through the seam and records
    nothing. Enumerating what is available is not a context read; the reads
    happen when :func:`resolve_refs` is handed the result.
    """
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo
    from agentic_cli.onboarding import provenance

    meta = detect_domain_meta_repo(slug)
    if meta is None:
        return []
    return [f"domain://{slug}/{p.name}"
            for p in sorted((meta / ".domain").glob("*.md"))
            if provenance.read(p).provenance != provenance.PLACEHOLDER]


def load_governance(domain: str) -> str:
    """Best-effort domain governance text for the preamble (empty if none)."""
    if not domain:
        return ""
    fetched = retrieval.fetch(f"governance://{domain}", source=TRACE_SOURCE)
    return fetched.text if fetched.resolved else ""
