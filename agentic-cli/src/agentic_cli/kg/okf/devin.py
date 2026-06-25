"""Push an OKF bundle to Devin Cloud Knowledge.

Maps OKF concepts -> Devin Knowledge entries via the Knowledge REST API
(https://api.devin.ai/v1/knowledge). Only STABLE knowledge is pushed; transient
state (Jira status / assignee / sprint) is never sent — concepts carry only the
`jira:` anchor, which Devin can hydrate live.

Idempotent: a sync map (``.devin-sync.json`` in the bundle root) records
``concept_id -> knowledge_id`` so re-runs PUT-update existing entries instead of
creating duplicates.

API contract (verified against docs.devin.ai, Devin API v1):
  GET    /v1/knowledge                -> {knowledge: [...], folders: [...]}
  POST   /v1/knowledge                 (name, body, trigger_description,
                                         pinned_repo?, parent_folder_id?, macro?)
  PUT    /v1/knowledge/{note_id}       (same params)
  DELETE /v1/knowledge/{note_id}
  Auth: Authorization: Bearer <DEVIN_API_KEY>  (apk_user_* or apk_*)
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_cli.kg.okf.bundle import Bundle
# Transport, auth, TLS, and generic Knowledge CRUD now live in the reusable
# agentic_cli.devin package. Re-exported here for backward compatibility.
from agentic_cli.devin.client import DevinClient, get_client
from agentic_cli.devin.config import (
    DEVIN_API_BASE, DEVIN_API_KEY_ENV, DEVIN_CA_BUNDLE_ENV, DEVIN_VERIFY_SSL_ENV,
    resolve_api_key, resolve_verify,
)
from agentic_cli.devin.errors import DevinError
from agentic_cli.devin.knowledge import (
    delete_entries, list_entries, move_entry, update_entry,
)

SYNC_FILE = ".devin-sync.json"
DRY_RUN_DIR = "devin"
# Concept types pushed by default: the highest-value, curated guidance.
DEFAULT_PUSH_TYPES = ("FREQ", "Requirement")
# Marker that delimits the auto-generated version footer in a knowledge body.
SYNC_FOOTER_MARKER = "<!-- okf-sync -->"

# [label](target "role")  — role optional; captures label + target.
_MD_LINK = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<target>[^)\s]+)(?:\s+\"(?P<role>[^\"]*)\")?\)")


def _content_hash(name: str, body_core: str, trigger: str, pinned_repo: str | None) -> str:
    """Stable short hash over the semantic content (excludes the version footer)."""
    h = hashlib.sha256()
    for part in (name, body_core, trigger, pinned_repo or ""):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


# ── Knowledge entry model ────────────────────────────────────────────────────

@dataclass
class KnowledgeEntry:
    concept_id: str
    name: str
    body: str  # CORE markdown body — never includes the version footer
    trigger_description: str
    pinned_repo: str | None = None
    feature: str = ""                # OKF feature group (e.g. "cwow-27901"), "" = shared
    okf_path: str = ""               # bundle concept id/path (e.g. features/cwow-27901/...)
    knowledge_id: str | None = None  # populated from the sync map / API response
    version: int = 1                 # bumped when content changes
    folder_name: str = ""            # resolved per-entry target folder name
    folder_id: str | None = None     # resolved per-entry target folder id

    def content_hash(self) -> str:
        return _content_hash(self.name, self.body, self.trigger_description, self.pinned_repo)

    def render_body(self, version: int, release: str = "") -> str:
        """Core body + an auto-generated version/provenance footer."""
        stamp = f"OKF v{version}"
        if release:
            stamp += f" · release {release}"
        stamp += (f" · hash {self.content_hash()}"
                  f" · synced {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        return f"{self.body.rstrip()}\n\n{SYNC_FOOTER_MARKER}\n_{stamp}_\n"

    def to_payload(self, version: int = 1, parent_folder_id: str | None = None,
                   release: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "body": self.render_body(version, release),
            "trigger_description": self.trigger_description,
        }
        if self.pinned_repo:
            payload["pinned_repo"] = self.pinned_repo
        if parent_folder_id:
            payload["parent_folder_id"] = parent_folder_id
        return payload


@dataclass
class PushResult:
    dry_run: bool = False
    created: list[str] = field(default_factory=list)   # concept ids
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # unchanged, not re-sent
    failed: list[tuple[str, str]] = field(default_factory=list)  # (concept id, error)
    entries: list[KnowledgeEntry] = field(default_factory=list)
    out_dir: Path | None = None        # where dry-run payloads were written
    folder_id: str | None = None       # resolved Devin folder id
    folder_name: str | None = None     # requested folder name


# ── Rendering: OKF concept -> Devin Knowledge body/trigger ───────────────────

def _clean_links(text: str) -> str:
    """Strip bundle-internal markdown links to plain text; keep external links."""
    def repl(m: re.Match) -> str:
        target, label = m.group("target"), m.group("label")
        if target.startswith(("http://", "https://")):
            return f"[{label}]({target})"
        return label
    return _MD_LINK.sub(repl, text)


def _repo_slug(resource: str) -> str:
    """Derive a repo identifier from a git URL, e.g.
    https://bitbucket.example.com/scm/cgf/cwow-facility-watercheck.git
    -> cwow-facility-watercheck
    """
    if not resource:
        return ""
    tail = resource.rstrip("/").rsplit("/", 1)[-1]
    return tail[:-4] if tail.endswith(".git") else tail


def _feature_of(rel_path: str) -> str:
    """`/features/cwow-27901/x.md` -> `cwow-27901`; `/shared/..` or other -> ''."""
    parts = rel_path.lstrip("/").split("/")
    return parts[1] if len(parts) >= 3 and parts[0] == "features" else ""


def _trigger_for(concept_type: str, title: str, domain: str,
                 freq_id: str = "", okf_path: str = "", feature: str = "") -> str:
    """Build the Devin `trigger_description`.

    Devin retrieval keys off this text (and the body), NOT off folders or the
    note name — so we encode the OKF group/path here for precise routing.
    """
    area = title.split("—")[-1].strip() if "—" in title else title
    ref = f" (FREQ {freq_id})" if freq_id else ""
    if concept_type == "FREQ":
        base = (f"When implementing, modifying, or writing tests for {area} in the "
                f"{domain} domain{ref}.")
    elif concept_type == "Requirement":
        base = (f"When implementing or validating the '{area}' requirement in the "
                f"{domain} domain.")
    else:
        base = f"When working with {area} in the {domain} domain."
    tail = ""
    if feature:
        tail += f" Feature: {feature}."
    if okf_path:
        tail += f" OKF: {okf_path}."
    return base + tail


def _render_body(bundle: Bundle, rel_path: str,
                 out_edges: dict, in_edges: dict) -> tuple[str, str | None]:
    """Return (markdown_body, pinned_repo) for the concept at rel_path."""
    c = bundle.concepts[rel_path]

    def title(rel: str) -> str:
        t = bundle.concepts.get(rel)
        return t.title if t else rel.rsplit("/", 1)[-1]

    def ctype(rel: str) -> str:
        t = bundle.concepts.get(rel)
        return t.type if t else "?"

    def resource(rel: str) -> str:
        t = bundle.concepts.get(rel)
        return t.fm.get("resource", "") if t else ""

    lines: list[str] = [_clean_links(c.body).rstrip()]

    rels: list[str] = []
    for role, dst in out_edges.get(rel_path, []):
        rels.append(f"- this **{role}** {title(dst)} ({ctype(dst)})")
    for role, src in in_edges.get(rel_path, []):
        rels.append(f"- {title(src)} ({ctype(src)}) **{role}** this")
    if rels:
        lines += ["", "## Knowledge graph relationships", *sorted(set(rels))]

    # pinned repo: first repo of a Code concept that `implements` this concept.
    pinned: str | None = None
    repos: list[str] = []
    for role, src in in_edges.get(rel_path, []):
        if role == "implements":
            slug = _repo_slug(resource(src))
            if slug and slug not in repos:
                repos.append(slug)
    if repos:
        pinned = repos[0]

    anchors: list[str] = []
    if c.fm.get("freq_id"):
        anchors.append(f"- Jira: {c.fm.get('freq_id')}")
    if c.fm.get("jira"):
        anchors.append(f"- Jira link: {c.fm['jira']}")
    if repos:
        anchors.append(f"- Repos: {', '.join(repos)}")
    if anchors:
        lines += ["", "## Anchors (stable references)", *anchors,
                  "", "_Transient state (status, assignee, sprint) is hydrated live "
                  "via Jira — not stored here._"]

    return "\n".join(lines).strip() + "\n", pinned


def build_knowledge_entries(bundle: Bundle,
                            types: tuple[str, ...] = DEFAULT_PUSH_TYPES) -> list[KnowledgeEntry]:
    """Render the selected concept types into Devin Knowledge entries."""
    out_edges: dict[str, list[tuple[str, str]]] = {}
    in_edges: dict[str, list[tuple[str, str]]] = {}
    for e in bundle.edges():
        out_edges.setdefault(e.src, []).append((e.role, e.dst))
        in_edges.setdefault(e.dst, []).append((e.role, e.src))

    entries: list[KnowledgeEntry] = []
    domain = ""
    for c in bundle.concepts.values():
        domain = domain or c.fm.get("domain", "")
        if types and c.type not in types:
            continue
        if not c.id:
            continue
        body, pinned = _render_body(bundle, c.rel_path, out_edges, in_edges)
        feature = _feature_of(c.rel_path)
        entries.append(KnowledgeEntry(
            concept_id=c.id,
            name=c.title,
            body=body,
            trigger_description=_trigger_for(
                c.type, c.title, c.fm.get("domain", domain), c.fm.get("freq_id", ""),
                okf_path=c.id, feature=feature),
            pinned_repo=pinned,
            feature=feature,
            okf_path=c.id,
        ))
    entries.sort(key=lambda e: e.concept_id)
    return entries


# ── Sync map (idempotency) ───────────────────────────────────────────────────

def _sync_path(root: Path) -> Path:
    return Path(root) / SYNC_FILE


def load_sync(root: Path) -> dict[str, dict[str, Any]]:
    """Return ``{concept_id: {id, version, hash, folder_id, synced_at}}``.

    Backward compatible with the legacy ``{concept_id: knowledge_id}`` shape.
    """
    p = _sync_path(root)
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    entries = raw.get("entries", {})
    out: dict[str, dict[str, Any]] = {}
    for cid, v in entries.items():
        if isinstance(v, str):  # legacy: just the knowledge id
            out[cid] = {"id": v, "version": 1, "hash": "", "folder_id": None, "synced_at": ""}
        elif isinstance(v, dict) and v.get("id"):
            out[cid] = v
    return out


def save_sync(root: Path, mapping: dict[str, dict[str, Any]],
              folder_id: str | None = None, folder_name: str | None = None) -> None:
    payload = {
        "folder_id": folder_id,
        "folder_name": folder_name,
        "entries": mapping,
    }
    _sync_path(root).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ── Orchestration ────────────────────────────────────────────────────────────

def bundle_domain(bundle: Bundle) -> str:
    for c in bundle.concepts.values():
        if c.fm.get("domain"):
            return c.fm["domain"]
    return ""


def default_folder_name(domain: str) -> str:
    return f"{domain}-okf" if domain else ""


def feature_folder_name(domain: str, feature: str) -> str:
    """Per-feature Devin folder, e.g. ('cwow-facility','cwow-27901') ->
    'cwow-facility-cwow-27901'. Shared (no feature) -> '<domain>-shared'."""
    if not domain:
        return ""
    return f"{domain}-{feature.lower()}" if feature else f"{domain}-shared"


def push_bundle(
    root: Path,
    api_key: str | None = None,
    types: tuple[str, ...] = DEFAULT_PUSH_TYPES,
    dry_run: bool = False,
    parent_folder_id: str | None = None,
    folder_name: str | None = None,
    folder_by_feature: bool = False,
    release: str = "",
    skip_unchanged: bool = True,
    validate_first: bool = True,
    base_url: str = DEVIN_API_BASE,
) -> PushResult:
    """Build entries from the bundle and push (or dry-run) to Devin Knowledge.

    Idempotent and versioned: each concept tracks a content hash + integer
    version in ``.devin-sync.json``. Unchanged entries are skipped; changed
    entries bump their version. Entries are placed in the folder named
    ``folder_name`` (resolved to an id; the Devin API cannot create folders, so
    it must already exist in the Devin UI) or under ``parent_folder_id``.

    Raises ``FileNotFoundError`` if the bundle is missing, ``ValueError`` on
    validation failure / missing key / unknown folder, ``DevinError`` on API
    errors (per-entry errors are collected in ``result.failed``).
    """
    root = Path(root)
    bundle = Bundle.load(root)

    if validate_first:
        from agentic_cli.kg.okf.validate import validate_bundle

        rep = validate_bundle(root)
        if rep.errors:
            raise ValueError(
                f"Bundle failed validation ({len(rep.errors)} errors); refusing to push. "
                f"Run `dva kg okf validate {root}` and fix violations first."
            )

    entries = build_knowledge_entries(bundle, types)
    sync = load_sync(root)
    domain = bundle_domain(bundle)
    result = PushResult(dry_run=dry_run, entries=entries, folder_name=folder_name)

    # Per-entry target folder name: one folder per feature when requested,
    # otherwise the single shared folder_name for every entry.
    for e in entries:
        e.folder_name = feature_folder_name(domain, e.feature) if folder_by_feature else (folder_name or "")

    # ── Dry run: write payloads, no network ──────────────────────────────────
    if dry_run:
        out_dir = root / DRY_RUN_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = []
        for e in entries:
            rec = sync.get(e.concept_id)
            changed = (not rec) or rec.get("hash") != e.content_hash()
            version = (rec.get("version", 1) + 1) if (rec and changed) else (rec.get("version", 1) if rec else 1)
            action = "create" if not rec else ("update" if changed else "skip")
            payload = e.to_payload(version, parent_folder_id, release)
            payload["_concept_id"] = e.concept_id
            payload["_action"] = action
            payload["_version"] = version
            payload["_feature"] = e.feature
            payload["_folder_name"] = e.folder_name or folder_name
            safe_name = e.concept_id.replace("/", "__")
            (out_dir / f"{safe_name}.json").write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            manifest.append({"concept_id": e.concept_id, "name": e.name, "feature": e.feature,
                             "folder_name": e.folder_name or folder_name,
                             "action": action, "version": version, "pinned_repo": e.pinned_repo})
            if action == "skip":
                result.skipped.append(e.concept_id)
            elif action == "create":
                result.created.append(e.concept_id)
            else:
                result.updated.append(e.concept_id)
        (out_dir / "_manifest.json").write_text(
            json.dumps({"folder_name": folder_name, "entries": manifest}, indent=2) + "\n",
            encoding="utf-8")
        result.out_dir = out_dir
        return result

    # ── Live push ────────────────────────────────────────────────────────────
    with get_client(api_key, base_url=base_url) as client:
        server = client.list_knowledge()
        folders = server.get("folders", [])
        existing = server.get("knowledge", [])

        # Resolve target folder(s). The Devin API cannot create folders, so any
        # required folder must already exist in the Devin UI.
        existing_folder_ids = {f.get("name"): f.get("id") for f in folders if f.get("name")}
        folder_id = parent_folder_id

        if folder_by_feature:
            needed = sorted({e.folder_name for e in entries if e.folder_name})
            missing = [n for n in needed if n not in existing_folder_ids]
            if missing:
                have = ", ".join(existing_folder_ids) or "(none)"
                raise ValueError(
                    f"{len(missing)} Devin folder(s) needed but missing: {', '.join(missing)}. "
                    f"The Devin API cannot create folders — create them in the Devin UI "
                    f"(Knowledge), then re-run. Existing folders: {have}"
                )
            for e in entries:
                e.folder_id = existing_folder_ids.get(e.folder_name)
        elif folder_name:
            folder_id = client.resolve_folder_id(folder_name, folders)
            if not folder_id:
                names = [f.get("name") for f in folders] or ["(none)"]
                raise ValueError(
                    f"Devin folder '{folder_name}' not found. The Devin API cannot create "
                    f"folders — create it in the Devin UI (Knowledge), then re-run. "
                    f"Existing folders: {', '.join(names)}"
                )
            for e in entries:
                e.folder_id = folder_id
        else:
            for e in entries:
                e.folder_id = folder_id
        result.folder_id = folder_id

        # Reconcile: backfill sync map from server by matching entry name, so we
        # update pre-existing root entries instead of creating duplicates.
        name_to_id: dict[str, str] = {}
        for k in existing:
            name_to_id.setdefault(k.get("name", ""), k.get("id", ""))
        for e in entries:
            if e.concept_id not in sync and e.name in name_to_id:
                sync[e.concept_id] = {"id": name_to_id[e.name], "version": 1,
                                      "hash": "", "folder_id": None, "synced_at": ""}

        now = datetime.now(timezone.utc).isoformat()
        for e in entries:
            rec = sync.get(e.concept_id)
            new_hash = e.content_hash()
            target_fid = e.folder_id  # per-entry (feature) or single shared folder
            try:
                if rec and rec.get("id"):
                    content_changed = rec.get("hash") != new_hash
                    folder_changed = (target_fid or None) != (rec.get("folder_id") or None)
                    if skip_unchanged and not content_changed and not folder_changed:
                        e.knowledge_id, e.version = rec["id"], rec.get("version", 1)
                        result.skipped.append(e.concept_id)
                        continue
                    version = rec.get("version", 1) + (1 if content_changed else 0)
                    client.update(rec["id"], e.to_payload(version, target_fid, release))
                    sync[e.concept_id] = {"id": rec["id"], "version": version, "hash": new_hash,
                                          "folder_id": target_fid, "synced_at": now}
                    e.knowledge_id, e.version = rec["id"], version
                    result.updated.append(e.concept_id)
                else:
                    resp = client.create(e.to_payload(1, target_fid, release))
                    new_id = resp.get("id")
                    sync[e.concept_id] = {"id": new_id, "version": 1, "hash": new_hash,
                                          "folder_id": target_fid, "synced_at": now}
                    e.knowledge_id, e.version = new_id, 1
                    result.created.append(e.concept_id)
            except Exception as exc:  # noqa: BLE001 — collect per-entry failures
                result.failed.append((e.concept_id, str(exc)))

        save_sync(root, sync, folder_id=folder_id, folder_name=folder_name)
    return result


# ── Management: list / prune / delete / move ─────────────────────────────────

@dataclass
class PruneResult:
    dry_run: bool = False
    orphans: list[dict[str, Any]] = field(default_factory=list)  # {concept_id,id,name}
    deleted: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def prune_bundle(
    root: Path,
    api_key: str | None = None,
    types: tuple[str, ...] = DEFAULT_PUSH_TYPES,
    dry_run: bool = False,
    base_url: str = DEVIN_API_BASE,
) -> PruneResult:
    """Delete tracked Devin entries whose concept no longer exists in the bundle."""
    root = Path(root)
    bundle = Bundle.load(root)
    current = {e.concept_id for e in build_knowledge_entries(bundle, types)}
    sync = load_sync(root)
    meta = {}
    p = _sync_path(root)
    if p.exists():
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    orphan_ids = {cid: rec for cid, rec in sync.items() if cid not in current}
    result = PruneResult(dry_run=dry_run)
    result.orphans = [{"concept_id": cid, "id": rec.get("id"), "name": cid}
                      for cid, rec in orphan_ids.items()]
    if dry_run or not orphan_ids:
        return result

    with get_client(api_key, base_url=base_url) as client:
        for cid, rec in orphan_ids.items():
            try:
                client.delete(rec["id"])
                result.deleted.append(cid)
                sync.pop(cid, None)
            except Exception as exc:  # noqa: BLE001
                result.failed.append((cid, str(exc)))
    save_sync(root, sync, folder_id=meta.get("folder_id"), folder_name=meta.get("folder_name"))
    return result
