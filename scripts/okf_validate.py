#!/usr/bin/env python3
"""OKF bundle conformance validator (prototype / seed for `dva kg okf validate`).

Validates an OKF knowledge bundle against its okf.schema.yaml:
  - required frontmatter fields present
  - concept `type` is in schema.concept_types
  - ids are unique
  - typed cross-links use an allowed relationship role
  - typed links resolve to an existing concept
  - each (source_type)-[role]->(target_type) is a legal triple
  - citation / resource rules

Usage:
  python scripts/okf_validate.py [BUNDLE_DIR]

Default BUNDLE_DIR: skills/domains/cwow-facility/knowledge
Exit code 0 = conformant, 1 = violations found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

# [text](/path/to.md "role")  — role optional
LINK_RE = re.compile(r'\[[^\]]+\]\((?P<target>[^)\s]+)(?:\s+"(?P<role>[^"]+)")?\)')
FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)


def parse_concept(path: Path):
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text, "missing YAML frontmatter"
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return None, text, f"invalid frontmatter YAML: {e}"
    body = text[m.end():]
    return fm, body, None


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent
        / "skills/domains/cwow-facility/knowledge"
    )
    schema_path = root / "okf.schema.yaml"
    if not schema_path.exists():
        sys.exit(f"No okf.schema.yaml in {root}")

    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    concept_types = set(schema.get("concept_types", []))
    relationships = set(schema.get("relationships", []))
    triples = {
        role: {tuple(t) for t in pairs}
        for role, pairs in (schema.get("triples", {}) or {}).items()
    }
    rules = schema.get("rules", {}) or {}
    required_fm = rules.get("required_frontmatter", [])
    require_cites = set(rules.get("require_citations_for", []))
    require_resource = set(rules.get("resource_required_for", []))
    require_freq_id = set(rules.get("freq_id_required_for", []))
    transient_fields = set(schema.get("transient_fields", []))
    forbid_transient = rules.get("forbid_transient_fields", False)

    md_files = sorted(p for p in root.rglob("*.md"))
    errors: list[str] = []
    warnings: list[str] = []

    # Pass 1: load all concepts, map bundle-absolute path -> type
    path_to_type: dict[str, str] = {}
    concepts = []  # (path, fm, body)
    ids_seen: dict[str, Path] = {}

    for path in md_files:
        fm, body, err = parse_concept(path)
        rel = "/" + str(path.relative_to(root))
        if err:
            errors.append(f"{rel}: {err}")
            continue
        concepts.append((path, rel, fm, body))
        path_to_type[rel] = fm.get("type")

        for field in required_fm:
            if field not in fm:
                errors.append(f"{rel}: missing required frontmatter '{field}'")

        cid = fm.get("id")
        if cid:
            if cid in ids_seen and rules.get("unique_ids", True):
                errors.append(f"{rel}: duplicate id '{cid}' (also in {ids_seen[cid].name})")
            ids_seen[cid] = path

        ctype = fm.get("type")
        if ctype and ctype not in concept_types:
            errors.append(f"{rel}: type '{ctype}' not in schema.concept_types")

        if ctype in require_cites and not fm.get("cites"):
            errors.append(f"{rel}: type '{ctype}' requires 'cites:' (citation)")
        if ctype in require_resource and not fm.get("resource"):
            errors.append(f"{rel}: type '{ctype}' requires 'resource:' binding")
        if ctype in require_freq_id and not fm.get("freq_id"):
            errors.append(f"{rel}: type '{ctype}' requires 'freq_id:' (e.g. CWOW-NNNNNN)")
        if forbid_transient:
            for tf in transient_fields & set(fm):
                errors.append(
                    f"{rel}: transient field '{tf}' must not be stored "
                    f"(hydrate live via MCP)"
                )

    # Pass 2: validate links / relationships
    link_count = 0
    typed_count = 0
    for path, rel, fm, body in concepts:
        src_type = fm.get("type")
        for lm in LINK_RE.finditer(body):
            target = lm.group("target")
            role = lm.group("role")
            if not target.startswith("/"):
                continue  # external/relative resource link; skip
            link_count += 1
            if rules.get("links_must_resolve", True) and target not in path_to_type:
                errors.append(f"{rel}: link target does not resolve -> {target}")
                continue
            if role is None:
                continue  # navigational link, no relationship semantics
            typed_count += 1
            if role not in relationships:
                errors.append(f"{rel}: role '{role}' not in schema.relationships")
                continue
            tgt_type = path_to_type.get(target)
            allowed = triples.get(role, set())
            if (src_type, tgt_type) not in allowed:
                errors.append(
                    f"{rel}: illegal triple ({src_type})-[{role}]->({tgt_type}) "
                    f"target={target}"
                )

    # Report
    print(f"OKF bundle: {root}")
    print(f"  concepts:        {len(concepts)}")
    print(f"  concept types:   {len(concept_types)} allowed")
    print(f"  links:           {link_count} ({typed_count} typed)")
    print(f"  warnings:        {len(warnings)}")
    for w in warnings:
        print(f"    ! {w}")
    if errors:
        print(f"\n  VIOLATIONS: {len(errors)}")
        for e in errors:
            print(f"    x {e}")
        print("\nFAIL")
        return 1
    print("\nPASS — bundle is conformant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
