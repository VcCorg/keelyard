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

import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentic_cli.onboarding.extract import Citation

#: Bodies are truncated before extraction. A page longer than this is a manual
#: worth its own page, and the tail is almost always appendices.
MAX_BODY_CHARS = 40_000

#: Filenames and directories that hold onboarding intent in a repository.
REPO_DOC_NAMES = ("CONTRIBUTING.md", "README.md", "ONBOARDING.md", "DEVELOPMENT.md")
REPO_DOC_DIRS = ("docs", "doc", "adr", "adrs", "runbooks", "runbook", ".github")

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


def head_sha(repo_root: Path) -> str:
    """Short HEAD sha, or empty when the path is not a git checkout."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def repo_documents(repo_root: Path, slug: str = "") -> list[Document]:
    """Read a repository's onboarding docs, citing each by path and sha."""
    repo_root = Path(repo_root)
    if not repo_root.is_dir():
        return []

    sha = head_sha(repo_root)
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
        documents.append(Document(
            text=text[:MAX_BODY_CHARS],
            citation=Citation("repo", f"{prefix}{rel}", sha),
            title=path.name,
        ))
        if len(documents) >= _MAX_REPO_DOCS:
            break
    return documents


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
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path not in found:
                found.append(path)

    return found


__all__ = [
    "MAX_BODY_CHARS", "REPO_DOC_NAMES", "REPO_DOC_DIRS", "Document",
    "fetch_confluence", "head_sha", "repo_documents",
]
