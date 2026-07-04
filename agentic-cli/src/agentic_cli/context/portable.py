"""Portable context bundle — the org's canonical context, engine-neutral.

The knowledge layer projects into Devin (see ``kg.okf.devin``). This projects
the *same* canonical context into a **portable, self-contained bundle** any
coding agent can consume — Claude Code, Codex, a local script — with no vendor
API and no lock-in. It is the second projection target that makes the
``ExecutionEngine`` seam demonstrably multi-engine.

A bundle is a directory:

  <out>/
    CONTEXT.md      assembled agent preamble (domain + governance + knowledge)
    prompt.md       the task prompt
    manifest.json   provenance: source refs, content digest, generated_at

Everything here is stdlib-only and pure/deterministic (a fixed ``generated_at``
can be injected) so it is trivially testable and never depends on a vendor.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

MANIFEST_VERSION = 1


@dataclass
class ContextItem:
    """One resolved piece of canonical context."""
    ref: str                 # canonical ref, e.g. okf://payments/features/x
    title: str = ""
    body: str = ""           # resolved content (may be empty if unresolved)
    source: str = ""         # provenance detail (bundle path, etc.)

    @property
    def resolved(self) -> bool:
        return bool(self.body.strip())


@dataclass
class PortableContextSpec:
    """Engine-neutral description of a context bundle to render."""
    prompt: str
    title: str = ""
    jira: str = ""
    domain: str = ""
    tags: list[str] = field(default_factory=list)
    items: list[ContextItem] = field(default_factory=list)
    governance: str = ""


@dataclass
class ContextBundle:
    bundle_id: str
    path: Path
    files: list[str]
    digest: str
    item_count: int
    resolved_count: int


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:60] or "context"


def bundle_id_for(spec: PortableContextSpec) -> str:
    """Stable, human-legible id for a bundle: jira key wins, else slugged title."""
    if spec.jira:
        return slugify(spec.jira)
    return slugify(spec.title or spec.prompt[:40])


def content_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def render_context_markdown(spec: PortableContextSpec) -> str:
    """Assemble the engine-neutral CONTEXT.md preamble.

    Deterministic: identical input → identical output (no timestamps here).
    """
    lines: list[str] = []
    heading = spec.title or (f"{spec.jira} context" if spec.jira else "Task context")
    lines.append(f"# {heading}")
    lines.append("")

    meta: list[str] = []
    if spec.jira:
        meta.append(f"- **Jira:** {spec.jira}")
    if spec.domain:
        meta.append(f"- **Domain:** {spec.domain}")
    if spec.tags:
        meta.append(f"- **Tags:** {', '.join(spec.tags)}")
    if meta:
        lines += meta + [""]

    lines.append(
        "> Portable context assembled from the org's canonical knowledge layer. "
        "This bundle is engine-neutral — usable by any coding agent, with no vendor dependency."
    )
    lines.append("")

    if spec.governance.strip():
        lines += ["## Governance", "", spec.governance.strip(), ""]

    if spec.items:
        lines += ["## Domain knowledge", ""]
        for it in spec.items:
            title = it.title or it.ref
            lines.append(f"### {title}")
            lines.append(f"_source: `{it.ref}`_")
            lines.append("")
            if it.resolved:
                lines.append(it.body.strip())
            else:
                lines.append(f"_(reference only — resolve from `{it.ref}`)_")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_manifest(spec: PortableContextSpec, rendered: str, files: list[str],
                   *, generated_at: Optional[str] = None) -> dict:
    """Provenance manifest for the bundle (engine-neutral)."""
    ts = generated_at or datetime.now(timezone.utc).isoformat()
    return {
        "manifest_version": MANIFEST_VERSION,
        "engine": "portable",
        "bundle_id": bundle_id_for(spec),
        "generated_at": ts,
        "jira": spec.jira,
        "domain": spec.domain,
        "tags": list(spec.tags),
        "title": spec.title,
        "context_digest": content_digest(rendered),
        "files": sorted(files),
        "items": [
            {"ref": it.ref, "title": it.title, "resolved": it.resolved, "source": it.source}
            for it in spec.items
        ],
    }


def write_bundle(spec: PortableContextSpec, out_dir: Path,
                 *, generated_at: Optional[str] = None) -> ContextBundle:
    """Render and write CONTEXT.md, prompt.md, manifest.json to ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered = render_context_markdown(spec)
    (out_dir / "CONTEXT.md").write_text(rendered, encoding="utf-8")
    (out_dir / "prompt.md").write_text((spec.prompt.rstrip() + "\n"), encoding="utf-8")

    files = ["CONTEXT.md", "prompt.md", "manifest.json"]
    manifest = build_manifest(spec, rendered, files, generated_at=generated_at)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return ContextBundle(
        bundle_id=manifest["bundle_id"],
        path=out_dir,
        files=files,
        digest=manifest["context_digest"],
        item_count=len(spec.items),
        resolved_count=sum(1 for it in spec.items if it.resolved),
    )
