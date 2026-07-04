"""Portable, engine-neutral context bundles projected from the org knowledge layer."""

from agentic_cli.context.portable import (
    ContextBundle,
    ContextItem,
    PortableContextSpec,
    build_manifest,
    bundle_id_for,
    render_context_markdown,
    write_bundle,
)
from agentic_cli.context.resolve import load_governance, resolve_refs

__all__ = [
    "ContextBundle",
    "ContextItem",
    "PortableContextSpec",
    "build_manifest",
    "bundle_id_for",
    "render_context_markdown",
    "write_bundle",
    "load_governance",
    "resolve_refs",
]
