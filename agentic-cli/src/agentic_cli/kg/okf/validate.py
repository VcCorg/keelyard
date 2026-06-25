"""OKF bundle conformance validation against okf.schema.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agentic_cli.kg.okf.bundle import Bundle


@dataclass
class ValidationReport:
    concepts: int = 0
    links: int = 0
    typed_links: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_bundle(root: Path) -> ValidationReport:
    bundle = Bundle.load(root)
    schema = bundle.schema
    rules = schema.rules
    required_fm = rules.get("required_frontmatter", [])
    require_cites = set(rules.get("require_citations_for", []))
    require_resource = set(rules.get("resource_required_for", []))
    require_freq_id = set(rules.get("freq_id_required_for", []))
    forbid_transient = rules.get("forbid_transient_fields", False)
    transient = schema.transient_fields
    rep = ValidationReport(concepts=len(bundle.concepts))

    ids_seen: dict[str, str] = {}
    for rel, c in bundle.concepts.items():
        for fieldname in required_fm:
            if fieldname not in c.fm:
                rep.errors.append(f"{rel}: missing required frontmatter '{fieldname}'")

        # Concept ID is derived from the file path (OKF §2), falling back to a
        # legacy `id` frontmatter key. Uniqueness is checked on the effective id.
        cid = c.id
        if cid:
            if cid in ids_seen and rules.get("unique_ids", True):
                rep.errors.append(f"{rel}: duplicate id '{cid}' (also {ids_seen[cid]})")
            ids_seen[cid] = rel

        ctype = c.type
        if ctype and ctype not in schema.concept_types:
            rep.errors.append(f"{rel}: type '{ctype}' not in schema.concept_types")
        if ctype in require_cites and not c.fm.get("cites"):
            rep.errors.append(f"{rel}: type '{ctype}' requires 'cites:'")
        if ctype in require_resource and not c.fm.get("resource"):
            rep.errors.append(f"{rel}: type '{ctype}' requires 'resource:'")
        if ctype in require_freq_id and not c.fm.get("freq_id"):
            rep.errors.append(f"{rel}: type '{ctype}' requires 'freq_id:'")
        if forbid_transient:
            for tf in transient & set(c.fm):
                rep.errors.append(
                    f"{rel}: transient field '{tf}' must not be stored (hydrate via MCP)"
                )

    # links / triples
    triples = schema.triples()
    relationships = schema.relationships
    must_resolve = rules.get("links_must_resolve", True)
    for rel, c in bundle.concepts.items():
        for link in c.links():
            rep.links += 1
            if must_resolve and link.target not in bundle.concepts:
                rep.errors.append(f"{rel}: link target does not resolve -> {link.target}")
                continue
            if link.role is None:
                continue
            rep.typed_links += 1
            if link.role not in relationships:
                rep.errors.append(f"{rel}: role '{link.role}' not in schema.relationships")
                continue
            src_t = c.type
            dst_t = bundle.type_of(link.target)
            if (src_t, dst_t) not in triples.get(link.role, set()):
                rep.errors.append(
                    f"{rel}: illegal triple ({src_t})-[{link.role}]->({dst_t}) "
                    f"target={link.target}"
                )
    return rep
