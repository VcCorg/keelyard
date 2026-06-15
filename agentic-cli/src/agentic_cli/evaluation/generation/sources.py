"""Document sources for evaluation dataset generation.

A source loads raw documents and yields text chunks that the question generator
turns into Q&A pairs. The ``local`` source is fully implemented with no extra
dependencies. ``gcs``, ``confluence`` and ``github`` are recognized but require
optional integrations; they raise a clear error until wired in.

Source specs use ``<type>:<location>`` form, e.g. ``local:./docs`` or
``kg:cwow-facility`` (the ``kg`` source is provided by ``domain_eval``).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# File extensions treated as plain-text documents for the local source.
_TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".text"}


@dataclass
class DocumentChunk:
    """A chunk of source text plus provenance metadata."""

    text: str
    source: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


def _chunk_text(text: str, max_chars: int = 1200) -> List[str]:
    """Split text into paragraph-aware chunks no larger than ``max_chars``."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # Flush current, then hard-split the long paragraph.
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            continue
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


class DocumentSource:
    """Base class for document sources."""

    def load_chunks(self, max_chars: int = 1200) -> List[DocumentChunk]:
        """Load and return text chunks from the source."""
        raise NotImplementedError


class LocalSource(DocumentSource):
    """Loads text/markdown documents from a local file or directory."""

    def __init__(self, location: str):
        """Initialize the local source.

        Args:
            location: Path to a file or directory of documents.
        """
        self.path = Path(location).expanduser()

    def load_chunks(self, max_chars: int = 1200) -> List[DocumentChunk]:
        """Read supported files under the path and return chunks."""
        if not self.path.exists():
            raise FileNotFoundError(f"Source path not found: {self.path}")

        files: List[Path] = []
        if self.path.is_file():
            files = [self.path]
        else:
            for ext in _TEXT_EXTENSIONS:
                files.extend(self.path.rglob(f"*{ext}"))

        if not files:
            raise ValueError(
                f"No text documents ({', '.join(sorted(_TEXT_EXTENSIONS))}) found in {self.path}"
            )

        chunks: List[DocumentChunk] = []
        for f in sorted(files):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError as e:  # pragma: no cover - defensive
                logger.warning(f"Could not read {f}: {e}")
                continue
            for chunk in _chunk_text(text, max_chars=max_chars):
                chunks.append(DocumentChunk(text=chunk, source=str(f)))
        return chunks


class _UnsupportedSource(DocumentSource):
    """Placeholder for sources that require optional integrations."""

    def __init__(self, source_type: str, location: str):
        self.source_type = source_type
        self.location = location

    def load_chunks(self, max_chars: int = 1200) -> List[DocumentChunk]:
        raise NotImplementedError(
            f"The '{self.source_type}' source is not yet wired in. "
            f"Supported now: local:<path>, kg:<domain>. Got '{self.source_type}:{self.location}'."
        )


def parse_source_spec(spec: str) -> tuple[str, str]:
    """Split a ``<type>:<location>`` spec into (type, location)."""
    if ":" not in spec:
        raise ValueError(
            f"Invalid source spec '{spec}'. Use '<type>:<location>', e.g. 'local:./docs'."
        )
    source_type, location = spec.split(":", 1)
    return source_type.strip().lower(), location.strip()


def get_source(spec: str) -> DocumentSource:
    """Resolve a source spec to a :class:`DocumentSource`.

    Note: the ``kg`` source is handled by ``domain_eval.get_kg_source`` because
    it depends on the knowledge-graph client; this factory covers file-based
    and placeholder sources.
    """
    source_type, location = parse_source_spec(spec)
    if source_type == "local":
        return LocalSource(location)
    if source_type in {"gcs", "storage", "confluence", "github"}:
        return _UnsupportedSource(source_type, location)
    raise ValueError(f"Unknown source type '{source_type}'. Use local:<path> or kg:<domain>.")
