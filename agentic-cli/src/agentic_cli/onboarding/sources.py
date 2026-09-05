"""Where onboarding intent is read from, and how bodies are kept out of memory's way.

Two corpora, deliberately different in character:

**Confluence** carries what teams actually maintain for new joiners — the pages
already tracked by ``domain add-docs``. Fetching a page also observes its current
version, which is the doc half of drift: ``source_version`` has been recorded
since v1 and never compared against anything.

**Repository docs** are the better corpus in one specific way. ``CONTRIBUTING.md``,
``docs/``, ADRs and runbooks are version-controlled and reviewed, so a citation
into them carries a commit sha and every instruction drawn from them is
drift-checkable with machinery that already exists. Confluence is not.

Neither reader retains a body: each returns text to :func:`~agentic_cli.
onboarding.extract.extract`, which reduces it to candidates and drops it.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agentic_cli.onboarding.extract import Citation

#: Bodies are truncated before extraction. A page longer than this is a manual
#: worth its own page, and the tail is almost always appendices.
MAX_BODY_CHARS = 40_000

#: Filenames and directories that hold onboarding intent in a repository.
#:
#: CLAUDE.md and AGENTS.md lead deliberately: they are the files a team writes
#: *for an agent*, which makes them the highest-signal onboarding material in
#: any modern repo. Their absence from the first cut of this list was only
#: visible once it ran against a real repository rather than a fixture.
REPO_DOC_NAMES = (
    "CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md", "README.md",
    "ONBOARDING.md", "DEVELOPMENT.md",
)
REPO_DOC_DIRS = ("docs", "doc", "adr", "adrs", "runbooks", "runbook", ".github")

#: Directories holding *deliberative* writing — what we might do — rather than
#: instructional writing — what you should do. Extracting imperatives from a
#: plan produces instructions for work nobody did, and from a comparison of
#: alternatives it produces instructions for the option that was rejected.
#: Running against this repo, three such directories supplied the top six
#: sources by volume before they were excluded.
DELIBERATIVE_DIRS = frozenset({
    "plans", "plan", "analysis", "analyses", "proposals", "proposal",
    "rfc", "rfcs", "brainstorm", "archive", "drafts", "superpowers",
})

_SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build",
    "target", "site-packages", ".tox", ".mypy_cache", ".pytest_cache",
}

#: Guard against walking a monorepo's entire documentation tree.
_MAX_REPO_DOCS = 60


@dataclass
class Document:
    """One body, on its way to extraction and then to nothing."""

    text: str
    citation: Citation
    title: str = ""
    doc_type: str = ""


def fetch_confluence(page_id: str, title: str = "") -> Document | None:
    """Read one tracked page through the Confluence MCP server.

    Returns ``None`` when the page cannot be read: a source that is temporarily
    unreachable must not look like a source with nothing to say, because the
    difference decides whether an approved instruction is flagged absent.
    """
    from agentic_cli.kg.okf.enrichment.sources.confluence import _html_to_text
    from agentic_cli.mcp_tool_client import MCPToolError, confluence_get_page

    try:
        page = confluence_get_page(str(page_id), include_body=True)
    except MCPToolError:
        return None
    if not isinstance(page, dict):
        return None

    body = page.get("body_html") or page.get("body") or page.get("content") or ""
    if isinstance(body, dict):
        body = body.get("value", "") or body.get("storage", {}).get("value", "")

    return Document(
        text=_html_to_text(str(body))[:MAX_BODY_CHARS],
        citation=Citation("confluence", str(page_id), str(page.get("version") or "")),
        title=str(page.get("title") or title),
    )


def content_version(text: str) -> str:
    """A short digest of the text an instruction was extracted from.

    This is the repo analogue of a Confluence page version, and it is
    deliberately **not** a commit sha. HEAD moves on every commit to the
    repository, so citing it would mark every repo-sourced instruction stale
    the moment anyone touched an unrelated file — the check would be useless on
    the day it shipped. A digest of the file's own content changes exactly when
    the thing we read changed, needs no subprocess, and works outside a git
    checkout.
    """
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]


def is_repo_citation_stale(repo_root: Path, rel_path: str, cited: str) -> Optional[bool]:
    """Has the file behind a repo citation changed since we read it?

    ``None`` means *unknown* — the file could not be read, or the citation
    carried no version. Unknown is never reported as fresh and never as stale:
    an unreadable source is a gap in our knowledge, not a verdict about it.
    """
    if not cited:
        return None
    path = Path(repo_root) / rel_path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return content_version(text[:MAX_BODY_CHARS]) != cited


def repo_documents(repo_root: Path, slug: str = "") -> list[Document]:
    """Read a repository's onboarding docs, citing each by path and sha."""
    repo_root = Path(repo_root)
    if not repo_root.is_dir():
        return []

    prefix = f"{slug}/" if slug else ""
    documents: list[Document] = []

    for path in _repo_doc_paths(repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            continue
        rel = path.relative_to(repo_root).as_posix()
        body = text[:MAX_BODY_CHARS]
        documents.append(Document(
            text=body,
            citation=Citation("repo", f"{prefix}{rel}", content_version(body)),
            title=path.name,
        ))
        if len(documents) >= _MAX_REPO_DOCS:
            break
    return documents


_DELIBERATIVE_NAME = re.compile(
    r"(^|[_\-])(plan|roadmap|proposal|analysis|comparison|alternatives|"
    r"brainstorm|ideas|backlog|draft|notes|summary|index)([_\-]|$)",
    re.IGNORECASE,
)


def _is_deliberative(stem: str) -> bool:
    """True for a filename that names a plan or an analysis rather than guidance.

    Directory placement catches most of it; this catches the ones that sit
    loose in ``docs/`` — ``EVALUATION_FRAMEWORK_PLAN.md`` and friends.
    """
    return bool(_DELIBERATIVE_NAME.search(stem))


def _repo_doc_paths(repo_root: Path) -> list[Path]:
    """Top-level onboarding files first, then the documentation directories."""
    found: list[Path] = []

    for name in REPO_DOC_NAMES:
        candidate = repo_root / name
        if candidate.is_file():
            found.append(candidate)

    for dirname in REPO_DOC_DIRS:
        directory = repo_root / dirname
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.md")):
            parts = set(path.parts)
            if parts & _SKIP_DIRS or parts & DELIBERATIVE_DIRS:
                continue
            if _is_deliberative(path.stem):
                continue
            if path not in found:
                found.append(path)

    return found


__all__ = [
    "MAX_BODY_CHARS", "REPO_DOC_NAMES", "REPO_DOC_DIRS", "Document",
    "DELIBERATIVE_DIRS", "fetch_confluence", "content_version",
    "is_repo_citation_stale", "repo_documents",
]
