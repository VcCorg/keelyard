"""Read/write OKF concept documents during enrichment.

Adapted from the GCP agent's bundle_tools, but built on our `Concept` model so
the output is byte-compatible with `keel kg okf validate`. Includes the GCP
**augmentation guard**: the enrichment (Confluence) pass may add to a document
but must never shrink an existing `# Schema`/`# Acceptance Criteria`/`# Citations`
section that the structural pass populated from authoritative metadata.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_cli.kg.okf.model import Concept

# Frontmatter we prefer at the top of every concept, in this order (OKF §4.1).
_PREFERRED_KEY_ORDER = ("type", "title", "description", "resource", "tags", "timestamp")
# Sections whose content the enrichment pass must not silently drop.
_GUARDED_SECTIONS = ("# Schema", "# Acceptance Criteria", "# Citations")
_FIELD_NAME_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`")


def concept_id_to_relpath(concept_id: str) -> str:
    """('features/cwow-27901') -> '/features/cwow-27901.md' (bundle-absolute)."""
    cid = concept_id.strip().strip("/")
    if not cid.endswith(".md"):
        cid = cid + ".md"
    return "/" + cid


def read_existing_doc(bundle_root: Path, concept_id: str) -> dict[str, Any] | None:
    """Return {'frontmatter', 'body'} for an existing concept, or None."""
    rel = concept_id_to_relpath(concept_id).lstrip("/")
    path = bundle_root / rel
    if not path.exists():
        return None
    c = Concept.read(path, bundle_root)
    if c is None:
        return None
    return {"frontmatter": c.fm, "body": c.body}


def _section_lines(body: str, heading: str) -> list[str]:
    in_section = False
    out: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("# "):
            in_section = s == heading
            continue
        if in_section and s:
            out.append(line)
    return out


def _schema_field_names(body: str) -> set[str]:
    names: set[str] = set()
    for line in _section_lines(body, "# Schema"):
        names.update(_FIELD_NAME_RE.findall(line))
    return names


def _reorder_frontmatter(fm: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in _PREFERRED_KEY_ORDER:
        if key in fm:
            ordered[key] = fm[key]
    for key, value in fm.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def check_augmentation_guard(old_body: str, new_body: str) -> str | None:
    """Return an error string if `new_body` shrinks a guarded section, else None."""
    # Schema fields must not disappear.
    old_fields = _schema_field_names(old_body)
    new_fields = _schema_field_names(new_body)
    missing = sorted(old_fields - new_fields)
    if missing:
        shown = ", ".join(f"`{m}`" for m in missing[:10])
        return (
            f"refusing to write: # Schema would lose {len(missing)} field(s) "
            f"populated by the structural pass: {shown}. Augment, do not replace."
        )
    # Acceptance criteria / citations entry counts must not drop.
    for heading in ("# Acceptance Criteria", "# Citations"):
        old_n = len(_section_lines(old_body, heading))
        new_n = len(_section_lines(new_body, heading))
        if new_n < old_n:
            return (
                f"refusing to write: {heading} had {old_n} entries but new body "
                f"has {new_n}. Append rather than replace."
            )
    return None


def write_concept_doc(
    bundle_root: Path,
    concept_id: str,
    frontmatter: dict[str, Any],
    body: str,
    *,
    enforce_guard: bool = False,
) -> dict[str, Any]:
    """Write (or augment) an OKF concept document.

    When `enforce_guard` is True (the enrichment pass), refuses writes that
    shrink guarded sections of an existing doc.
    Returns {'path', 'bytes'} on success or {'error', 'concept_id'} on refusal.
    """
    rel = concept_id_to_relpath(concept_id)
    path = bundle_root / rel.lstrip("/")

    fm = dict(frontmatter)
    if not fm.get("type"):
        return {"error": "frontmatter missing required 'type'", "concept_id": concept_id}
    if not fm.get("timestamp"):
        fm["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fm = _reorder_frontmatter(fm)

    if enforce_guard and path.exists():
        existing = Concept.read(path, bundle_root)
        if existing is not None:
            err = check_augmentation_guard(existing.body, body or "")
            if err:
                return {"error": err, "concept_id": concept_id}

    concept = Concept(fm=fm, body=body or "", rel_path=rel)
    written = concept.write(bundle_root)
    text = written.read_text(encoding="utf-8")
    return {"path": str(written.relative_to(bundle_root)), "bytes": len(text.encode("utf-8"))}
