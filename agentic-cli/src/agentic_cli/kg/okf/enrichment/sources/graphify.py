"""GraphifyCodeSource — advertise a repo's code structure from graphify output.

This is the no-LLM counterpart to :class:`CodebaseSource`. Instead of running
heuristics over the filesystem and asking a model to author prose, it reads the
AST-derived ``graphify-out/graph.json`` (NetworkX node-link format produced by
the external ``graphify`` CLI) and renders conformant OKF concepts
deterministically via :meth:`render_concept` (no model call).

Concepts advertised:

  Component   - one per repository (architecture anchor)
  CodeModule  - one per source directory that holds code
  Code        - one per code file (capped), carrying its symbols + call edges

Relationships emitted as OKF typed links (schema-legal triples only):

  Component -[contains]->  CodeModule
  CodeModule -[depends-on]-> CodeModule   (cross-module calls)
  Code      -[depends-on]-> Code          (cross-file calls)

All link targets are concepts this source also emits, so the bundle validates
with ``links_must_resolve``. ``Code`` concepts always carry ``resource`` (the
file path) to satisfy ``resource_required_for: [Code]``.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from agentic_cli.kg.okf.enrichment.source import ConceptRef, Source
from agentic_cli.kg.okf.schema import slugify

log = logging.getLogger(__name__)

# Conventional source roots stripped when deriving a module name.
_SOURCE_ROOTS = {"src", "lib", "app", "internal", "pkg", "cmd"}
# Cap how many file-level Code concepts we emit to avoid node explosion.
_MAX_CODE_FILES = 400
_MAX_MODULES = 80


def graph_json_path(project_path: Path) -> Path:
    """Conventional graphify graph path for a repo."""
    return Path(project_path) / "graphify-out" / "graph.json"


class GraphifyCodeSource(Source):
    """Advertise code structure from ``graphify-out/graph.json`` (no LLM)."""

    name = "graphify"

    def __init__(
        self,
        project_path: Path,
        graph_path: Path | None = None,
        max_code_files: int = _MAX_CODE_FILES,
        namespace: str | None = None,
    ):
        self.root = Path(project_path).resolve()
        self.graph_path = Path(graph_path) if graph_path else graph_json_path(self.root)
        self.max_code_files = max_code_files
        # When set, module/code concept IDs and their links are namespaced under
        # the repo (e.g. ``modules/<ns>/auth``) so multiple repos can share one
        # OKF bundle without colliding. ``None`` keeps the flat single-repo layout.
        self.ns = slugify(namespace) if namespace else None
        self._payloads: dict[str, dict[str, Any]] | None = None
        self._refs: list[ConceptRef] | None = None

    # -- availability -----------------------------------------------------
    @classmethod
    def available(cls, project_path: Path, graph_path: Path | None = None) -> bool:
        """True when a readable graphify graph exists for this repo."""
        p = Path(graph_path) if graph_path else graph_json_path(Path(project_path))
        return p.is_file()

    # -- graph loading + adapter -----------------------------------------
    def _load_graph(self) -> dict[str, Any]:
        try:
            data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"could not read graphify graph at {self.graph_path}: {e}")
        if not isinstance(data, dict) or "nodes" not in data or "links" not in data:
            raise ValueError(
                f"unrecognized graphify graph schema at {self.graph_path} "
                f"(expected NetworkX node-link with 'nodes' and 'links')"
            )
        return data

    @staticmethod
    def _is_file_node(node: dict[str, Any]) -> bool:
        """A file node's label is the basename of its source_file."""
        sf = node.get("source_file") or ""
        label = node.get("label") or ""
        return bool(sf) and label == Path(sf).name

    @staticmethod
    def _module_of(source_file: str) -> str:
        """Top-level module key for a file path (strip conventional src roots)."""
        parts = [p for p in source_file.split("/") if p]
        if len(parts) <= 1:
            return "root"
        dirs = parts[:-1]
        if dirs and dirs[0] in _SOURCE_ROOTS:
            dirs = dirs[1:]
        return dirs[0] if dirs else "root"

    # -- build (once) -----------------------------------------------------
    def _build(self) -> dict[str, dict[str, Any]]:
        if self._payloads is not None:
            return self._payloads

        graph = self._load_graph()
        nodes: list[dict[str, Any]] = graph.get("nodes") or []
        links: list[dict[str, Any]] = graph.get("links") or []

        node_by_id = {n.get("id"): n for n in nodes if n.get("id")}
        # Only code nodes participate in code concepts (skip documents).
        code_nodes = {nid: n for nid, n in node_by_id.items()
                      if (n.get("file_type") == "code")}

        # Classify file vs symbol nodes; map symbol -> owning file via `contains`.
        file_ids = {nid for nid, n in code_nodes.items() if self._is_file_node(n)}
        symbol_owner: dict[str, str] = {}
        for lk in links:
            if lk.get("relation") == "contains":
                src, dst = lk.get("source"), lk.get("target")
                if src in file_ids and dst in code_nodes and dst not in file_ids:
                    symbol_owner[dst] = src

        def file_of(node_id: str) -> str | None:
            if node_id in file_ids:
                return node_id
            return symbol_owner.get(node_id)

        # Stable ordering for deterministic output + cap.
        ordered_files = sorted(
            file_ids, key=lambda nid: (code_nodes[nid].get("source_file") or "", nid)
        )
        emitted_files = set(ordered_files[: self.max_code_files])

        # Symbols per file.
        symbols_by_file: dict[str, list[dict[str, Any]]] = {fid: [] for fid in emitted_files}
        for sid, fid in symbol_owner.items():
            if fid in emitted_files:
                symbols_by_file[fid].append(code_nodes[sid])
        for fid in symbols_by_file:
            symbols_by_file[fid].sort(key=lambda n: (n.get("source_location") or "", n.get("label") or ""))

        # File -> module, and module membership.
        file_module: dict[str, str] = {}
        module_files: dict[str, list[str]] = {}
        for fid in emitted_files:
            sf = code_nodes[fid].get("source_file") or ""
            mod = self._module_of(sf)
            file_module[fid] = mod
            module_files.setdefault(mod, []).append(fid)
        modules = sorted(module_files)[: _MAX_MODULES]
        module_set = set(modules)

        # Call edges -> file/module dependency pairs (only emitted endpoints).
        file_deps: dict[str, set[str]] = {fid: set() for fid in emitted_files}
        mod_deps: dict[str, set[str]] = {m: set() for m in module_set}
        for lk in links:
            if lk.get("relation") != "calls":
                continue
            sf, tf = file_of(lk.get("source")), file_of(lk.get("target"))
            if not sf or not tf or sf == tf:
                continue
            if sf in emitted_files and tf in emitted_files:
                file_deps[sf].add(tf)
                sm, tm = file_module.get(sf), file_module.get(tf)
                if sm in module_set and tm in module_set and sm != tm:
                    mod_deps[sm].add(tm)

        # Slugs / concept ids. When a namespace is set the module/code concepts
        # live under it so multiple repos can coexist in one bundle.
        repo_slug = slugify(self.root.name)
        ns = self.ns
        component_id = f"components/{ns}" if ns else f"components/{repo_slug}"

        def _mid(slug: str) -> str:
            return f"modules/{ns}/{slug}" if ns else f"modules/{slug}"

        def _cid(slug: str) -> str:
            return f"code/{ns}/{slug}" if ns else f"code/{slug}"

        file_slug: dict[str, str] = {}
        used: set[str] = set()
        for fid in emitted_files:
            sf = code_nodes[fid].get("source_file") or fid
            base = slugify(sf.replace("/", "-")) or fid
            slug = base
            i = 2
            while slug in used:
                slug = f"{base}-{i}"
                i += 1
            used.add(slug)
            file_slug[fid] = slug
        module_slug = {m: slugify(m) for m in modules}

        languages = sorted({
            Path(code_nodes[fid].get("source_file") or "").suffix.lstrip(".")
            for fid in emitted_files
            if Path(code_nodes[fid].get("source_file") or "").suffix
        })

        payloads: dict[str, dict[str, Any]] = {}

        # Component (repo anchor).
        payloads[component_id] = {
            "type": "Component",
            "title": self.root.name,
            "resource": str(self.root),
            "kind": "repository-overview",
            "languages": languages,
            "module_count": len(modules),
            "file_count": len(emitted_files),
            "modules": [(m, _mid(module_slug[m]), len(module_files.get(m, []))) for m in modules],
        }

        # CodeModule per directory.
        for m in modules:
            payloads[_mid(module_slug[m])] = {
                "type": "CodeModule",
                "title": m,
                "resource": str(self.root / m) if m != "root" else str(self.root),
                "component_id": component_id,
                "files": [
                    (code_nodes[fid].get("source_file") or fid, _cid(file_slug[fid]))
                    for fid in sorted(module_files.get(m, []),
                                      key=lambda f: code_nodes[f].get("source_file") or f)
                    if fid in emitted_files
                ],
                "depends_on": sorted(
                    _mid(module_slug[d]) for d in mod_deps.get(m, set()) if d in module_slug
                ),
            }

        # Code per file.
        for fid in emitted_files:
            n = code_nodes[fid]
            payloads[_cid(file_slug[fid])] = {
                "type": "Code",
                "title": n.get("source_file") or n.get("label") or fid,
                "resource": str(self.root / (n.get("source_file") or "")),
                "graphify_node_id": fid,
                "module": file_module.get(fid, "root"),
                "symbols": [
                    (s.get("label") or "", s.get("source_location") or "")
                    for s in symbols_by_file.get(fid, [])
                ],
                "depends_on": sorted(
                    _cid(file_slug[d]) for d in file_deps.get(fid, set()) if d in file_slug
                ),
            }

        self._payloads = payloads
        return payloads

    # -- Source interface -------------------------------------------------
    def list_concepts(self) -> list[ConceptRef]:
        if self._refs is not None:
            return self._refs
        payloads = self._build()
        refs: list[ConceptRef] = []
        for cid, p in payloads.items():
            refs.append(
                ConceptRef(
                    id=tuple(cid.split("/")),
                    type=p["type"],
                    resource=p.get("resource"),
                    hint={"graphify": True},
                )
            )
        self._refs = refs
        return refs

    def read_concept(self, ref: ConceptRef) -> dict[str, Any]:
        return dict(self._build().get(ref.id_str, {}))

    # -- deterministic rendering (no LLM) --------------------------------
    def render_concept(self, ref: ConceptRef, raw: dict[str, Any]) -> dict[str, Any] | None:
        p = raw or self._build().get(ref.id_str)
        if not p:
            return None
        ctype = p.get("type")
        if ctype == "Component":
            return self._render_component(p)
        if ctype == "CodeModule":
            return self._render_module(p)
        if ctype == "Code":
            return self._render_code(p)
        return None

    @staticmethod
    def _render_component(p: dict[str, Any]) -> dict[str, Any]:
        langs = ", ".join(p.get("languages") or []) or "—"
        lines = [
            f"Repository **{p['title']}** — architecture anchor derived from the "
            f"graphify code graph (AST, no LLM).",
            "",
            "# Overview",
            f"- Languages: {langs}",
            f"- Modules: {p.get('module_count', 0)}",
            f"- Code files: {p.get('file_count', 0)}",
        ]
        mods = p.get("modules") or []
        if mods:
            lines += ["", "# Modules"]
            for name, mid, n in mods:
                lines.append(f"- [{name}](/{mid}.md \"contains\") — {n} file(s)")
        return {
            "title": p["title"],
            "description": f"Repository overview for {p['title']} ({langs}).",
            "tags": ["graphify", "component"],
            "body": "\n".join(lines).rstrip() + "\n",
        }

    @staticmethod
    def _render_module(p: dict[str, Any]) -> dict[str, Any]:
        lines = [
            f"Source module **{p['title']}** — files and dependencies from the "
            f"graphify code graph.",
            "",
            f"Part of [{p.get('component_id')}](/{p.get('component_id')}.md).",
        ]
        files = p.get("files") or []
        if files:
            lines += ["", "# Files"]
            for sf, cid in files:
                lines.append(f"- [{sf}](/{cid}.md)")
        deps = p.get("depends_on") or []
        if deps:
            lines += ["", "# Dependencies"]
            for mid in deps:
                lines.append(f"- [{mid}](/{mid}.md \"depends-on\")")
        return {
            "title": p["title"],
            "description": f"Source module {p['title']} ({len(files)} file(s)).",
            "tags": ["graphify", "code-module"],
            "body": "\n".join(lines).rstrip() + "\n",
        }

    @staticmethod
    def _render_code(p: dict[str, Any]) -> dict[str, Any]:
        lines = [
            f"Code file **{p['title']}** (module `{p.get('module')}`) — symbols and "
            f"call dependencies from the graphify graph.",
            "",
            f"graphify node: `{p.get('graphify_node_id')}`",
        ]
        symbols = p.get("symbols") or []
        if symbols:
            lines += ["", "# Symbols"]
            for label, loc in symbols:
                suffix = f" ({loc})" if loc else ""
                lines.append(f"- `{label}`{suffix}")
        deps = p.get("depends_on") or []
        if deps:
            lines += ["", "# Dependencies"]
            for cid in deps:
                lines.append(f"- [{cid}](/{cid}.md \"depends-on\")")
        return {
            "title": p["title"],
            "description": f"Code file {p['title']} ({len(symbols)} symbol(s)).",
            "tags": ["graphify", "code"],
            "body": "\n".join(lines).rstrip() + "\n",
        }


# --------------------------------------------------------------------------- #
# Graph generation (deterministic, no LLM) — generate a missing graph on demand
# --------------------------------------------------------------------------- #
def ensure_graph(project_path: Path, *, generate: bool = True, force: bool = False) -> tuple[bool, str]:
    """Ensure ``graphify-out/graph.json`` exists for a repo.

    When the graph is missing and ``generate`` is True, run ``graphify update``
    (AST-only, no API cost) to produce it. This is the no-LLM ingestion path the
    domain workflow uses so every linked repo contributes to the OKF bundle.

    Returns ``(available, status)`` where ``status`` is one of:
    ``existing`` | ``generated`` | ``missing`` | ``no-cli`` | ``failed:<msg>``.
    """
    repo = Path(project_path)
    if not force and GraphifyCodeSource.available(repo):
        return True, "existing"
    if not generate:
        return False, "missing"
    if shutil.which("graphify") is None:
        return False, "no-cli"
    try:
        cmd = ["graphify", "update", ".", "--force"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo))
    except Exception as e:  # noqa: BLE001
        return False, f"failed:{e}"
    if proc.returncode != 0:
        return False, f"failed:{(proc.stderr or proc.stdout or 'graphify update error')[:200]}"
    if GraphifyCodeSource.available(repo):
        return True, "generated"
    return False, "failed:graph.json not produced"


# --------------------------------------------------------------------------- #
# MultiGraphifyCodeSource — aggregate every repo of a domain into one bundle
# --------------------------------------------------------------------------- #
class MultiGraphifyCodeSource(Source):
    """Aggregate the graphify graphs of several repos into one OKF concept set.

    Each repo becomes a namespaced :class:`GraphifyCodeSource` (``namespace`` =
    the repo directory slug) so module/code concept IDs never collide across
    repos. Concepts are simply the union of every child source's concepts; the
    runner reads/renders each via its owning source.
    """

    name = "graphify-multi"

    def __init__(self, project_paths: list[Path], max_code_files: int = _MAX_CODE_FILES):
        self.children: list[GraphifyCodeSource] = []
        seen: set[str] = set()
        for p in project_paths:
            root = Path(p).resolve()
            ns = slugify(root.name) or "repo"
            base = ns
            i = 2
            while ns in seen:  # guarantee unique namespace per repo
                ns = f"{base}-{i}"
                i += 1
            seen.add(ns)
            self.children.append(
                GraphifyCodeSource(root, max_code_files=max_code_files, namespace=ns)
            )
        self._refs: list[ConceptRef] | None = None
        self._owner: dict[str, GraphifyCodeSource] = {}

    @classmethod
    def available_paths(cls, project_paths: list[Path]) -> list[Path]:
        """Subset of paths that already have a graphify graph."""
        return [Path(p) for p in project_paths if GraphifyCodeSource.available(Path(p))]

    def list_concepts(self) -> list[ConceptRef]:
        if self._refs is not None:
            return self._refs
        refs: list[ConceptRef] = []
        owner: dict[str, GraphifyCodeSource] = {}
        for child in self.children:
            for ref in child.list_concepts():
                refs.append(ref)
                owner[ref.id_str] = child
        self._refs = refs
        self._owner = owner
        return refs

    def read_concept(self, ref: ConceptRef) -> dict[str, Any]:
        self.list_concepts()
        child = self._owner.get(ref.id_str)
        return child.read_concept(ref) if child else {}

    def render_concept(self, ref: ConceptRef, raw: dict[str, Any]) -> dict[str, Any] | None:
        self.list_concepts()
        child = self._owner.get(ref.id_str)
        return child.render_concept(ref, raw) if child else None
