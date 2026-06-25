"""OKF schema: canonical model, conformance contract, and Neo4j->OKF mapping.

The canonical schema is the curated, anti-label-explosion contract. The exporter
uses a *hybrid* strategy: known Neo4j labels/relationship types are mapped onto the
canonical model; anything unknown is quarantined under an `Unmapped_*` concept type
or `unmapped-*` role (added to the emitted schema + a report) so nothing is lost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


# ── Canonical model ──────────────────────────────────────────────────────────
CANONICAL_CONCEPT_TYPES: list[str] = [
    # Domain entities
    "Facility", "Patient", "Encounter", "Assessment", "PlanOfCare",
    "CarePlan", "Provider",
    # Delivery artifacts
    "Release", "Feature", "Requirement", "FREQ", "UserStory",
    # Implementation
    "Code", "Test",
    # Codebase knowledge (produced by the enrichment agent during onboarding)
    "Component", "CodeModule", "APIEndpoint", "DataModel",
]

CANONICAL_RELATIONSHIPS: list[str] = [
    "implements", "references", "tested-by", "configures", "part-of", "depends-on",
    "exposes", "contains",
]

CANONICAL_TRIPLES: dict[str, list[list[str]]] = {
    "implements": [["Code", "Requirement"], ["Code", "FREQ"]],
    "configures": [["Code", "Requirement"], ["Code", "FREQ"]],
    "tested-by": [["Code", "Test"], ["Requirement", "Test"], ["FREQ", "Test"]],
    "depends-on": [["Code", "Code"], ["CodeModule", "CodeModule"]],
    "exposes": [["Component", "APIEndpoint"], ["CodeModule", "APIEndpoint"]],
    "contains": [["Component", "CodeModule"], ["CodeModule", "DataModel"]],
    "part-of": [
        ["Requirement", "Feature"], ["FREQ", "Requirement"], ["FREQ", "Feature"],
        ["Feature", "Release"], ["UserStory", "Feature"],
        ["Assessment", "Encounter"], ["Encounter", "Patient"], ["Patient", "Facility"],
        ["CodeModule", "Component"], ["APIEndpoint", "Component"],
    ],
    "references": [
        ["Requirement", "Facility"], ["Requirement", "Patient"],
        ["Requirement", "Encounter"], ["Requirement", "Assessment"],
        ["Requirement", "PlanOfCare"], ["Requirement", "CarePlan"],
        ["Requirement", "Provider"],
        ["FREQ", "Facility"], ["FREQ", "Patient"], ["FREQ", "Encounter"],
        ["Code", "Facility"], ["Code", "Patient"], ["Code", "Encounter"],
        ["UserStory", "Facility"], ["UserStory", "Patient"],
    ],
}

TRANSIENT_FIELDS: list[str] = [
    "status", "assignee", "sprint", "story_points",
    "pr_status", "build_status", "updated", "owner",
]


# ── Neo4j -> OKF mapping (hybrid export) ─────────────────────────────────────
# Exact label -> canonical concept type.
LABEL_MAP: dict[str, str] = {
    "Facility": "Facility",
    "Patient": "Patient",
    "Encounter": "Encounter",
    "Assessment": "Assessment",
    "PlanOfCare": "PlanOfCare",
    "CarePlan": "CarePlan",
    "Provider": "Provider",
    "Release": "Release",
    "Feature": "Feature",
    "Requirement": "Requirement",
    "Document": "Requirement",      # business requirement docs
    "UserStory": "UserStory",
    "Story": "UserStory",
    "Test": "Test",
}
# Prefix-based fallbacks (label.startswith(prefix) -> type).
LABEL_PREFIX_MAP: list[tuple[str, str]] = [
    ("Test", "Test"),
    ("Code", "Code"),
]

# Neo4j relationship type -> (canonical role, reverse_direction?).
# reverse=True means the OKF edge points the opposite way to the Neo4j edge,
# e.g. Release-[HAS_DOCUMENT]->Document  becomes  Requirement-[part-of]->Release.
REL_MAP: dict[str, tuple[str, bool]] = {
    "IMPLEMENTS": ("implements", False),
    "REFERENCES": ("references", False),
    "TESTED_BY": ("tested-by", False),
    "CONFIGURES": ("configures", False),
    "BELONGS_TO": ("part-of", False),
    "SPECIFIES_RELEASE": ("part-of", False),
    "IS_BASED_ON": ("references", False),
    "HAS_DOCUMENT": ("part-of", True),
    "CONTAINS": ("part-of", True),
    "PART_OF": ("part-of", False),
    "DEPENDS_ON": ("depends-on", False),
    "DESCRIBES": ("references", False),
}


def slugify(text: str, max_len: int = 60) -> str:
    """Filesystem/id-safe slug."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (s[:max_len].rstrip("-")) or "concept"


def map_label(label: str) -> tuple[str, bool]:
    """Return (concept_type, is_mapped) for a Neo4j label."""
    if label in LABEL_MAP:
        return LABEL_MAP[label], True
    for prefix, ctype in LABEL_PREFIX_MAP:
        if label.startswith(prefix):
            return ctype, True
    return f"Unmapped_{re.sub(r'[^A-Za-z0-9]', '_', label)}", False


def map_relationship(rel_type: str) -> tuple[str, bool, bool]:
    """Return (role, reverse, is_mapped) for a Neo4j relationship type."""
    if rel_type in REL_MAP:
        role, reverse = REL_MAP[rel_type]
        return role, reverse, True
    return f"unmapped-{rel_type.lower().replace('_', '-')}", False, False


def canonical_schema_dict(domain: str = "", product: str = "") -> dict[str, Any]:
    """The curated canonical schema as a serializable dict."""
    return {
        "version": "0.1.0",
        "domain": domain,
        "product": product,
        "concept_types": list(CANONICAL_CONCEPT_TYPES),
        "relationships": list(CANONICAL_RELATIONSHIPS),
        "triples": {k: [list(t) for t in v] for k, v in CANONICAL_TRIPLES.items()},
        "transient_fields": list(TRANSIENT_FIELDS),
        "rules": {
            "required_frontmatter": ["type", "title"],
            "forbid_transient_fields": True,
            "unique_ids": True,
            "links_must_resolve": True,
            "require_citations_for": ["Requirement"],
            "freq_id_required_for": ["FREQ"],
            "resource_required_for": ["Code"],
        },
    }


@dataclass
class OKFSchema:
    """Loaded okf.schema.yaml with conformance helpers."""

    raw: dict[str, Any]

    @classmethod
    def canonical(cls, domain: str = "", product: str = "") -> "OKFSchema":
        return cls(canonical_schema_dict(domain, product))

    @classmethod
    def load(cls, path: Path) -> "OKFSchema":
        if yaml is None:
            raise RuntimeError("PyYAML required for OKF schema")
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {})

    def dump(self, path: Path) -> None:
        if yaml is None:
            raise RuntimeError("PyYAML required for OKF schema")
        Path(path).write_text(
            yaml.safe_dump(self.raw, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    # accessors
    @property
    def concept_types(self) -> set[str]:
        return set(self.raw.get("concept_types", []))

    @property
    def relationships(self) -> set[str]:
        return set(self.raw.get("relationships", []))

    @property
    def transient_fields(self) -> set[str]:
        return set(self.raw.get("transient_fields", []))

    @property
    def rules(self) -> dict[str, Any]:
        return self.raw.get("rules", {}) or {}

    def triples(self) -> dict[str, set[tuple[str, str]]]:
        return {
            role: {tuple(t) for t in pairs}
            for role, pairs in (self.raw.get("triples", {}) or {}).items()
        }

    def triple_allowed(self, role: str, src: str, dst: str) -> bool:
        return (src, dst) in self.triples().get(role, set())

    # mutation (used by hybrid exporter to quarantine unmapped items)
    def add_concept_type(self, ctype: str) -> None:
        if ctype not in self.raw.setdefault("concept_types", []):
            self.raw["concept_types"].append(ctype)

    def add_relationship(self, role: str) -> None:
        if role not in self.raw.setdefault("relationships", []):
            self.raw["relationships"].append(role)

    def add_triple(self, role: str, src: str, dst: str) -> None:
        triples = self.raw.setdefault("triples", {})
        pairs = triples.setdefault(role, [])
        if [src, dst] not in pairs:
            pairs.append([src, dst])
