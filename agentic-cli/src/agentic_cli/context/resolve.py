"""Resolve canonical context refs into portable content — best-effort.

Turns engine-neutral references (``okf://<domain>/<concept_id>`` or plain
strings) into :class:`ContextItem` objects with real bodies pulled from the
org's OKF bundles. Everything is defensive: if a bundle or its optional deps
are unavailable, the ref is kept as *reference-only* so a bundle can always be
produced without a vendor or a heavy toolchain.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from agentic_cli.context.portable import ContextItem


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
        parsed = _parse_okf_ref(ref)
        if parsed:
            domain, concept = parsed
            loaded = _load_okf_item(domain, concept)
            items.append(loaded or ContextItem(ref=ref, title=concept, source="unresolved"))
        else:
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
                return candidate.read_text(encoding="utf-8").strip()
        except Exception:  # noqa: BLE001
            continue
    return ""
