"""Domain-aware evaluation: KG-sourced datasets and meta-repo config storage.

This module ties the evaluation feature into the domain knowledge graph and the
domain meta-repo:

- ``kg:<domain>`` becomes a dataset source — domain context aspects (SLAs,
  integrations, security, architecture, ...) are pulled from the KG and turned
  into Q&A pairs by the question generator.
- Evaluation configs can be persisted into a domain meta-repo under
  ``.platform/config/eval/<name>.yaml`` so they are versioned and shared with
  the team alongside other domain configuration.
"""

import logging
from pathlib import Path
from typing import List, Optional

import yaml

from agentic_cli.evaluation.eval_config import EvaluationConfig
from agentic_cli.evaluation.generation.sources import DocumentChunk, DocumentSource

logger = logging.getLogger(__name__)

#: Subdirectory (under .platform/config) where eval configs are stored.
META_EVAL_SUBDIR = "eval"


class KgDomainSource(DocumentSource):
    """Document source backed by the domain knowledge graph."""

    def __init__(self, domain: str, aspects: Optional[List[str]] = None):
        """Initialize the KG source.

        Args:
            domain: Domain slug (e.g. "cwow-facility").
            aspects: Optional subset of aspects to query (default: all).
        """
        self.domain = domain
        self.aspects = aspects

    def load_chunks(self, max_chars: int = 1200) -> List[DocumentChunk]:
        """Query the KG for domain aspects and return non-empty chunks."""
        from agentic_cli.kg.domain_context import query_domain_kg

        results = query_domain_kg(self.domain, aspects=self.aspects)
        chunks: List[DocumentChunk] = []
        for aspect, text in results.items():
            text = (text or "").strip()
            if not text:
                continue
            chunks.append(
                DocumentChunk(
                    text=text,
                    source=f"kg:{self.domain}",
                    metadata={"aspect": aspect, "domain": self.domain},
                )
            )
        if not chunks:
            raise ValueError(
                f"No domain context returned from the KG for '{self.domain}'. "
                "Ensure the KG is configured and ingested (dva kg ...)."
            )
        return chunks


def get_kg_source(spec: str) -> KgDomainSource:
    """Resolve a ``kg:<domain>`` spec to a :class:`KgDomainSource`.

    Args:
        spec: A source spec of the form ``kg:<domain>``.
    """
    if ":" not in spec:
        raise ValueError(f"Invalid KG source spec '{spec}'. Use 'kg:<domain>'.")
    prefix, domain = spec.split(":", 1)
    if prefix.strip().lower() != "kg":
        raise ValueError(f"Not a KG source spec: '{spec}'.")
    domain = domain.strip()
    if not domain:
        raise ValueError("KG source requires a domain slug, e.g. 'kg:cwow-facility'.")
    return KgDomainSource(domain)


def resolve_source(spec: str) -> DocumentSource:
    """Resolve any source spec, including ``kg:`` (delegates to file sources otherwise)."""
    source_type = spec.split(":", 1)[0].strip().lower() if ":" in spec else ""
    if source_type == "kg":
        return get_kg_source(spec)
    # Defer to the file/placeholder source factory.
    from agentic_cli.evaluation.generation.sources import get_source

    return get_source(spec)


# ---------------------------------------------------------------------------
# Meta-repo config persistence
# ---------------------------------------------------------------------------

def _meta_eval_dir(meta_repo_path: Path) -> Path:
    """Return (and create) the eval config dir inside a meta-repo."""
    eval_dir = Path(meta_repo_path) / ".platform" / "config" / META_EVAL_SUBDIR
    eval_dir.mkdir(parents=True, exist_ok=True)
    return eval_dir


def save_config_to_meta_repo(
    config: EvaluationConfig,
    domain_slug: str,
    search_paths: Optional[List[Path]] = None,
) -> Optional[Path]:
    """Persist an eval config into the domain meta-repo, if one is found.

    Args:
        config: The evaluation config to store.
        domain_slug: Domain slug used to locate the meta-repo.
        search_paths: Optional override search paths for detection.

    Returns:
        The written path, or None if no meta-repo was found.
    """
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    meta_repo_path = detect_domain_meta_repo(domain_slug, search_paths=search_paths)
    if not meta_repo_path:
        logger.info(f"No domain meta-repo found for '{domain_slug}'; skipping meta-repo save.")
        return None

    eval_dir = _meta_eval_dir(meta_repo_path)
    out_path = eval_dir / f"{config.name}.yaml"
    out_path.write_text(yaml.safe_dump(config.to_dict(), sort_keys=False))
    logger.debug(f"Saved eval config '{config.name}' to {out_path}")
    return out_path


def load_configs_from_meta_repo(
    domain_slug: str,
    search_paths: Optional[List[Path]] = None,
) -> List[EvaluationConfig]:
    """Load all eval configs stored in a domain meta-repo (if present)."""
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    meta_repo_path = detect_domain_meta_repo(domain_slug, search_paths=search_paths)
    if not meta_repo_path:
        return []

    eval_dir = Path(meta_repo_path) / ".platform" / "config" / META_EVAL_SUBDIR
    if not eval_dir.exists():
        return []

    configs: List[EvaluationConfig] = []
    for path in sorted(eval_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text()) or {}
            configs.append(EvaluationConfig.from_dict(data))
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Skipping invalid eval config {path}: {e}")
    return configs
