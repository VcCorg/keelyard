"""Build an OKF bundle from an already-ingested Neo4j domain (no re-indexing).

Hybrid strategy: known Neo4j labels/relationship types are mapped onto the canonical
OKF schema; unknown ones are quarantined (added to the emitted schema under
`Unmapped_*` / `unmapped-*` plus a nonconforming report) so nothing is lost.

Transient state (Jira status, assignee, build status, ...) is never copied; only
stable knowledge + anchors are written.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic_cli.kg.okf.model import Concept
from agentic_cli.kg.okf.schema import (
    OKFSchema,
    TRANSIENT_FIELDS,
    map_label,
    map_relationship,
    slugify,
)

FREQ_RE = re.compile(r"(CWOW-\d+)")
_EXCERPT_LEN = 600


@dataclass
class ExportResult:
    domain: str
    out_dir: Path
    concepts: int = 0
    edges_typed: int = 0
    minted_freqs: int = 0
    unmapped_labels: dict[str, int] = field(default_factory=dict)
    unmapped_rels: dict[str, int] = field(default_factory=dict)
    quarantined_triples: set[tuple[str, str, str]] = field(default_factory=set)
    skipped_edges: int = 0


@dataclass
class _Node:
    node_id: str
    ctype: str
    mapped: bool
    slug: str
    fm: dict[str, Any]
    excerpt: str
    rel_path: str = ""  # assigned AFTER feature assignment (see _finalize_paths)
    links: list[tuple[str, str, str]] = field(default_factory=list)  # (role, dst_id, dst_title)

    @property
    def title(self) -> str:
        return str(self.fm.get("title", self.node_id))


def _anchor_fields(source: str | None) -> dict[str, str]:
    fm: dict[str, str] = {}
    if not source:
        return fm
    low = source.lower()
    if "jira" in low or "/browse/" in low:
        fm["jira"] = source
    elif "confluence" in low or "/spaces/" in low or "/pages/" in low:
        fm["confluence"] = source
    else:
        fm["source"] = source
    return fm


def _excerpt(content: str | None) -> str:
    if not content:
        return ""
    text = " ".join(str(content).split())
    return text[:_EXCERPT_LEN] + ("…" if len(text) > _EXCERPT_LEN else "")


def _first_sentence(content: str | None, limit: int = 160) -> str:
    """A one-line `description` per OKF §4.1 — first sentence, clamped."""
    if not content:
        return ""
    text = " ".join(str(content).split())
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    sentence = (m.group(1) if m else text).strip()
    return sentence[:limit].rstrip() + ("…" if len(sentence) > limit else "")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _feature_key_from_path(rel_path: str) -> str:
    """`/features/cwow-27901/x.md` -> `cwow-27901`; else ''."""
    parts = rel_path.lstrip("/").split("/")
    return parts[1] if len(parts) >= 3 and parts[0] == "features" else ""


def _assign_features(
    all_nodes: list[_Node],
    freq_nodes: list[_Node],
    by_id: dict[str, _Node],
) -> dict[str, str]:
    """Multi-source BFS over the (undirected) relationship graph from each FREQ.

    Returns {node_id -> feature_key}. The nearest FREQ owns a concept; ties break
    on the lexicographically smallest feature key (FREQs are seeded sorted).
    Concepts not reachable from any FREQ are absent from the map (-> shared/).
    """
    from collections import defaultdict, deque

    adj: dict[str, set[str]] = defaultdict(set)
    for node in all_nodes:
        for _role, dst_id, _t in node.links:
            if dst_id in by_id:
                adj[node.node_id].add(dst_id)
                adj[dst_id].add(node.node_id)

    owner: dict[str, str] = {}
    dq: deque[str] = deque()
    for f in sorted(freq_nodes, key=lambda n: n.fm.get("freq_id", "")):
        owner[f.node_id] = f.fm["freq_id"]
        dq.append(f.node_id)
    while dq:
        cur = dq.popleft()
        for nb in sorted(adj[cur]):
            if nb not in owner:
                owner[nb] = owner[cur]
                dq.append(nb)
    return owner


def _finalize_paths(all_nodes: list[_Node], owner: dict[str, str]) -> None:
    """Assign each node's bundle-absolute rel_path based on its feature owner.

    FREQ      -> /features/<key>/freq-<key>.md
    owned     -> /features/<key>/<slug>-<id8>.md
    unowned   -> /shared/<slug>-<id8>.md
    """
    used: set[str] = set()
    for node in all_nodes:
        key = owner.get(node.node_id, "")
        if node.ctype == "FREQ":
            rel = f"/features/{node.fm['freq_id'].lower()}/{node.slug}.md"
        elif key:
            rel = f"/features/{key.lower()}/{node.slug}-{str(node.node_id)[:8]}.md"
        else:
            rel = f"/shared/{node.slug}-{str(node.node_id)[:8]}.md"
        base, n = rel, 2
        while rel in used:
            rel = f"{base[:-3]}-{n}.md"
            n += 1
        used.add(rel)
        node.rel_path = rel


def export_domain(
    domain: str,
    out_dir: Path,
    product: str = "",
    mint_freqs: bool = True,
    node_limit: int = 5000,
    config: Any = None,
) -> ExportResult:
    """Export a Neo4j domain subgraph to an OKF bundle at out_dir."""
    from agentic_cli.kg.neo4j_client import Neo4jClient

    out_dir = Path(out_dir)
    schema = OKFSchema.canonical(domain=domain, product=product)
    # Relax authoring-quality rules for exported (legacy) data. The structural
    # contract (concept_types / relationships / triples / transient_fields) still
    # applies — that is the anti-label-explosion guarantee. Citation/resource
    # requirements are for hand-authored bundles, not graph exports.
    schema.rules["require_citations_for"] = []
    schema.rules["resource_required_for"] = []
    result = ExportResult(domain=domain, out_dir=out_dir)

    nodes: dict[str, _Node] = {}
    freq_concepts: dict[str, _Node] = {}  # freq_id -> node

    with Neo4jClient(config=config) as client:
        node_rows = client.execute_cypher(
            """
            MATCH (n) WHERE n.domain = $domain
            RETURN n.id AS id, n.name AS name, labels(n) AS labels,
                   n.source AS source, n.content AS content, n.repo AS repo
            LIMIT $limit
            """,
            {"domain": domain, "limit": node_limit},
        )

        for row in node_rows:
            nid = row.get("id")
            name = row.get("name") or nid
            if not nid or not name:
                continue
            labels = [lb for lb in (row.get("labels") or []) if lb]
            # choose primary label: first that maps cleanly, else first label
            primary = next((lb for lb in labels if map_label(lb)[1]), labels[0] if labels else "Entity")
            ctype, mapped = map_label(primary)
            if not mapped:
                result.unmapped_labels[primary] = result.unmapped_labels.get(primary, 0) + 1
                schema.add_concept_type(ctype)

            slug = slugify(f"{ctype}-{name}")

            # OKF §4.1 frontmatter — `type` required; recommend title/description/
            # resource/timestamp. Concept ID is derived from the file path (§2), so
            # no `id` key is written. `domain`/anchor keys are producer extensions.
            fm: dict[str, Any] = {"type": ctype, "title": str(name)}
            desc = _first_sentence(row.get("content"))
            if desc:
                fm["description"] = desc
            anchors = _anchor_fields(row.get("source"))
            fm.update(anchors)
            resource = next(iter(anchors.values()), "")
            if ctype == "Code" and row.get("repo"):
                resource = row["repo"]
            if resource:
                fm["resource"] = resource
            fm["domain"] = domain
            # never copy transient state
            for tf in TRANSIENT_FIELDS:
                fm.pop(tf, None)

            nodes[nid] = _Node(
                node_id=nid, ctype=ctype, mapped=mapped, slug=slug,
                fm=fm, excerpt=_excerpt(row.get("content")),
            )

            # mint FREQ concepts from requirement-like content
            if mint_freqs and ctype == "Requirement":
                blob = f"{name} {row.get('content') or ''}"
                for fid in dict.fromkeys(FREQ_RE.findall(blob)):
                    if fid in freq_concepts:
                        fnode = freq_concepts[fid]
                    else:
                        jira = f"https://jira.example.com/browse/{fid}"
                        fnode = _Node(
                            node_id=f"freq:{fid}", ctype="FREQ", mapped=True,
                            slug=f"freq-{fid.lower()}",
                            fm={
                                "type": "FREQ",
                                "title": fid,
                                "description": f"Functional requirement {fid}.",
                                "freq_id": fid,
                                "jira": jira,
                                "resource": jira,
                                "domain": domain,
                            },
                            excerpt=f"Functional requirement extracted from {name}.",
                        )
                        freq_concepts[fid] = fnode
                    # FREQ part-of its Requirement (canonical triple); store dst id
                    fnode.links.append(("part-of", nid, str(name)))

        # relationships (both endpoints in-domain -> self-contained bundle)
        rel_rows = client.execute_cypher(
            """
            MATCH (a)-[r]->(b)
            WHERE a.domain = $domain AND b.domain = $domain
            RETURN a.id AS src, b.id AS dst, type(r) AS type
            """,
            {"domain": domain},
        )

    for row in rel_rows:
        src_id, dst_id, rtype = row.get("src"), row.get("dst"), row.get("type")
        if not src_id or not dst_id or not rtype:
            continue
        role, reverse, rmapped = map_relationship(rtype)
        a, b = (dst_id, src_id) if reverse else (src_id, dst_id)
        src_node, dst_node = nodes.get(a), nodes.get(b)
        if not src_node or not dst_node:
            result.skipped_edges += 1
            continue
        if not rmapped:
            result.unmapped_rels[rtype] = result.unmapped_rels.get(rtype, 0) + 1
            schema.add_relationship(role)
        # enforce/quarantine triple
        if not schema.triple_allowed(role, src_node.ctype, dst_node.ctype):
            schema.add_triple(role, src_node.ctype, dst_node.ctype)
            if rmapped:  # canonical role but novel endpoint combo
                result.quarantined_triples.add((src_node.ctype, role, dst_node.ctype))
        src_node.links.append((role, b, dst_node.title))
        result.edges_typed += 1

    # assemble & write concepts (feature-grouped, spec-conformant)
    all_nodes = list(nodes.values()) + list(freq_concepts.values())
    result.minted_freqs = len(freq_concepts)
    _assemble_and_write(
        out_dir, domain, product, schema, all_nodes,
        list(freq_concepts.values()), result,
    )
    return result


def _build_body(node: _Node, owner: dict[str, str], by_id: dict[str, _Node]) -> str:
    """Concept body: breadcrumb + excerpt + a typed-link Relationships section."""
    key = owner.get(node.node_id, "")
    crumb = f"features/{key.lower()}" if key else "shared"
    lines = [f"\n# {node.fm['title']}\n",
             f"\n> **OKF path:** `{node.rel_path}` · **group:** `{crumb}`\n"]
    if node.excerpt:
        lines.append(f"\n{node.excerpt}\n")
    if node.links:
        rels, seen = [], set()
        for role, dst_id, dst_title in node.links:
            dn = by_id.get(dst_id)
            if not dn:
                continue
            k = (role, dn.rel_path)
            if k in seen:
                continue
            seen.add(k)
            rels.append(f'- [{dst_title}]({dn.rel_path} "{role}")')
        if rels:
            lines.append("\n## Relationships\n\n" + "\n".join(sorted(rels)) + "\n")
    return "".join(lines)


def _assemble_and_write(
    out_dir: Path,
    domain: str,
    product: str,
    schema: Any,
    all_nodes: list[_Node],
    freq_nodes: list[_Node],
    result: ExportResult,
) -> None:
    """Assign features, finalize paths, write concepts + §6 index files + schema.

    Factored out of ``export_domain`` so it can be unit-tested without Neo4j.
    """
    by_id: dict[str, _Node] = {n.node_id: n for n in all_nodes}
    owner = _assign_features(all_nodes, freq_nodes, by_id)
    _finalize_paths(all_nodes, owner)

    ts = _now_iso()
    for node in all_nodes:
        key = owner.get(node.node_id, "")
        tags = [t for t in (key, node.ctype.lower()) if t]
        if tags:
            node.fm["tags"] = tags
        node.fm["timestamp"] = ts
        body = _build_body(node, owner, by_id)
        Concept(fm=node.fm, body=body, rel_path=node.rel_path).write(out_dir)
    result.concepts = len(all_nodes)

    schema.dump(out_dir / "okf.schema.yaml")
    _write_indexes(out_dir, domain, product, all_nodes, owner)
    _write_report(out_dir, result)


def _index_file(path: Path, body_lines: list[str], frontmatter: dict[str, Any] | None = None) -> None:
    """Write a §6 index.md. Index files carry NO frontmatter, except the bundle
    root MAY declare ``okf_version`` (§11) — the only permitted exception."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    if frontmatter:
        import yaml as _yaml
        out += ["---", _yaml.safe_dump(frontmatter, sort_keys=False).rstrip(), "---", ""]
    out += body_lines
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _write_indexes(
    out_dir: Path, domain: str, product: str,
    all_nodes: list[_Node], owner: dict[str, str],
) -> None:
    """Emit spec §6 progressive-disclosure index files at every level."""
    features: dict[str, list[_Node]] = {}
    shared: list[_Node] = []
    for n in all_nodes:
        key = owner.get(n.node_id, "")
        if key:
            features.setdefault(key.lower(), []).append(n)
        else:
            shared.append(n)

    def _desc(n: _Node) -> str:
        d = n.fm.get("description", "")
        return f" - {d}" if d else ""

    # root index.md — only place frontmatter is allowed (okf_version)
    root_body = [
        f"# {domain} — OKF Knowledge Bundle",
        "",
        f"Product: {product}. Exported from the existing Neo4j graph (no re-indexing)."
        if product else "Exported from the existing Neo4j graph (no re-indexing).",
        "",
        "# Sections",
        "",
        f"* [features/](features/) - {len(features)} feature group(s)",
    ]
    if shared:
        root_body.append(f"* [shared/](shared/) - {len(shared)} concept(s) not bound to a feature")
    _index_file(out_dir / "index.md", root_body, frontmatter={"okf_version": "0.1"})

    # features/index.md — lists each feature subdirectory
    if features:
        feat_body = ["# Features", ""]
        for key in sorted(features):
            feat_body.append(f"* [{key}]({key}/) - {len(features[key])} concept(s)")
        _index_file(out_dir / "features" / "index.md", feat_body)
        # one index.md per feature directory
        for key, members in features.items():
            body = [f"# Feature {key}", ""]
            for n in sorted(members, key=lambda x: str(x.fm.get("title", ""))):
                fname = n.rel_path.rsplit("/", 1)[-1]
                body.append(f"* [{n.fm.get('title', fname)}]({fname}){_desc(n)}")
            _index_file(out_dir / "features" / key / "index.md", body)

    # shared/index.md
    if shared:
        body = ["# Shared concepts", "",
                "Concepts not reachable from any feature (FREQ) in the graph.", ""]
        for n in sorted(shared, key=lambda x: str(x.fm.get("title", ""))):
            fname = n.rel_path.rsplit("/", 1)[-1]
            body.append(f"* [{n.fm.get('title', fname)}]({fname}){_desc(n)}")
        _index_file(out_dir / "shared" / "index.md", body)


def _write_report(out_dir: Path, r: ExportResult) -> None:
    lines = [f"# Export report — {r.domain}", "",
             f"- concepts: {r.concepts}", f"- typed edges: {r.edges_typed}",
             f"- minted FREQs: {r.minted_freqs}", f"- skipped edges (endpoint outside domain): {r.skipped_edges}",
             ""]
    lines.append("## Quarantined: unmapped node labels")
    lines.append("")
    if r.unmapped_labels:
        for lbl, cnt in sorted(r.unmapped_labels.items(), key=lambda x: -x[1]):
            lines.append(f"- `{lbl}` -> `Unmapped_{re.sub(r'[^A-Za-z0-9]', '_', lbl)}` ({cnt})")
    else:
        lines.append("- none")
    lines += ["", "## Quarantined: unmapped relationship types", ""]
    if r.unmapped_rels:
        for rel, cnt in sorted(r.unmapped_rels.items(), key=lambda x: -x[1]):
            lines.append(f"- `{rel}` -> `unmapped-{rel.lower().replace('_', '-')}` ({cnt})")
    else:
        lines.append("- none")
    lines += ["", "## Quarantined: novel triples (canonical role, new endpoints)", ""]
    if r.quarantined_triples:
        for s, role, d in sorted(r.quarantined_triples):
            lines.append(f"- ({s})-[{role}]->({d})")
    else:
        lines.append("- none")
    lines.append("")
    (out_dir / "nonconforming-report.md").write_text("\n".join(lines), encoding="utf-8")
