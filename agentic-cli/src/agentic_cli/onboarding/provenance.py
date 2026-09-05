"""Where a piece of domain context came from, and whether a human stood behind it.

``domain init`` writes ``.domain/`` files whether or not the KG had anything to
say. When the query times out or returns nothing, the scaffold writes *"will be
populated from the Knowledge Graph"* and the command proceeds to a green success
panel — so a domain can be fully "onboarded", green, and empty, and every agent
downstream builds on it.

Two frontmatter keys fix that, and everything else in the readiness work depends
on them: each score is a share of real content over total, and today those are
indistinguishable.

    ---
    provenance: doc:12345      # kg | doc:<page-id> | repo:<path> | placeholder
    reviewed: yes              # a human finalized this
    ---

Legacy files carry no frontmatter, so :func:`read` falls back to recognising the
scaffold's own placeholder sentences. That keeps existing meta-repos scorable
without a migration — an unstamped file that reads like a placeholder *is* one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: Content came from the knowledge graph.
KG = "kg"
#: Content came from a tracked document; ``doc:<page-id>``.
DOC = "doc"
#: Content came from a linked repository; ``repo:<path>``.
REPO = "repo"
#: The scaffold wrote filler because it had nothing.
PLACEHOLDER = "placeholder"
#: No frontmatter and no recognisable filler — provenance is genuinely unknown.
UNKNOWN = "unknown"

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", re.MULTILINE)

#: Sentences the scaffold emits when it has nothing. Matching one is decisive:
#: no real domain context describes itself as pending.
_PLACEHOLDER_RE = re.compile(
    r"will be populated from the knowledge graph|"
    r"_?architecture details will be populated|"
    r"^\s*_?(tbd|todo|to be (defined|determined|documented))_?\s*$|"
    r"no domain context found",
    re.IGNORECASE | re.MULTILINE,
)

_TRUTHY = frozenset({"yes", "true", "1", "y"})


@dataclass(frozen=True)
class Stamp:
    """What one context file claims about itself."""

    path: Path
    provenance: str = UNKNOWN
    reviewed: bool = False
    source: str = ""          # the ``<page-id>`` / ``<path>`` half, when present

    @property
    def real(self) -> bool:
        """True when the file carries content rather than filler."""
        return self.provenance not in (PLACEHOLDER, UNKNOWN)

    @property
    def grounded(self) -> bool:
        """True when the content traces to a named source, not just 'the KG'."""
        return self.provenance in (DOC, REPO) and bool(self.source)

    def to_dict(self) -> dict:
        return {
            "path": self.path.name,
            "provenance": self.provenance,
            "source": self.source,
            "reviewed": self.reviewed,
            "real": self.real,
        }


def parse_value(raw: str) -> tuple[str, str]:
    """Split ``doc:12345`` into ``("doc", "12345")``; bare values keep no source."""
    kind, _, source = (raw or "").strip().partition(":")
    kind = kind.strip().lower()
    if kind not in (KG, DOC, REPO, PLACEHOLDER):
        return UNKNOWN, ""
    return kind, source.strip()


def read(path: Path) -> Stamp:
    """Read one context file's stamp, falling back to placeholder detection."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return Stamp(path=path)

    match = _FRONTMATTER_RE.match(text)
    if match:
        keys = dict(_KEY_RE.findall(match.group(1)))
        if "provenance" in keys:
            kind, source = parse_value(keys["provenance"])
            reviewed = keys.get("reviewed", "").strip().lower() in _TRUTHY
            return Stamp(path=path, provenance=kind, reviewed=reviewed, source=source)
        body = text[match.end():]
    else:
        body = text

    # Unstamped: decide from the body. Filler is filler whether or not anyone
    # labelled it, and an empty file is the most obvious filler of all.
    if not body.strip() or _PLACEHOLDER_RE.search(body):
        return Stamp(path=path, provenance=PLACEHOLDER)
    return Stamp(path=path)


def stamp(path: Path, provenance: str, reviewed: bool = False) -> Path:
    """Write or replace the frontmatter on a context file, preserving its body."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""

    match = _FRONTMATTER_RE.match(text)
    body = text[match.end():] if match else text

    header = f"---\nprovenance: {provenance}\nreviewed: {'yes' if reviewed else 'no'}\n---\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body, encoding="utf-8")
    return path


def scan(domain_dir: Path, pattern: str = "*.md") -> list[Stamp]:
    """Stamp every context file under ``.domain/``, sorted by name."""
    domain_dir = Path(domain_dir)
    if not domain_dir.is_dir():
        return []
    return [read(p) for p in sorted(domain_dir.glob(pattern))]


def summarize(stamps: list[Stamp]) -> dict:
    """Aggregate counts a scorecard can turn into a share."""
    total = len(stamps)
    real = sum(1 for s in stamps if s.real)
    return {
        "total": total,
        "real": real,
        "placeholder": sum(1 for s in stamps if s.provenance == PLACEHOLDER),
        "unknown": sum(1 for s in stamps if s.provenance == UNKNOWN),
        "reviewed": sum(1 for s in stamps if s.reviewed),
        "grounded": sum(1 for s in stamps if s.grounded),
    }


__all__ = [
    "KG", "DOC", "REPO", "PLACEHOLDER", "UNKNOWN", "Stamp", "parse_value",
    "read", "stamp", "scan", "summarize",
]
