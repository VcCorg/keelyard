"""Persona catalog resolution.

Resolves the *effective* set of personas to generate for a domain by combining:

1. Built-in defaults shipped with the platform (``domain/dev/qa/sm/ba``).
2. A product-tier catalog (``product-<slug>-meta/.platform/config/personas.yaml``)
   that toggles built-ins via ``defaults_enabled`` and adds product-specific
   personas (e.g. tech-lead, product-owner).

Resolution rules:
- If no product catalog is present, all built-in defaults are returned.
- ``defaults_enabled`` filters which built-ins are included (order preserved).
- Custom personas are appended after the enabled built-ins. A custom persona
  whose ``id`` matches a built-in overrides that built-in (custom content wins).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from agentic_cli.meta_repo.config import PersonasConfig, PersonaSpec
from agentic_cli.skill_generator import builtin_persona_specs

logger = logging.getLogger(__name__)

PERSONAS_FILENAME = "personas.yaml"


def builtin_catalog() -> list[PersonaSpec]:
    """Return the built-in default persona specs."""
    return builtin_persona_specs()


def product_personas_path(product_meta_path: Path) -> Path:
    """Path to a product meta-repo's personas.yaml."""
    return product_meta_path / ".platform" / "config" / PERSONAS_FILENAME


def load_product_personas(product_meta_path: Optional[Path]) -> Optional[PersonasConfig]:
    """Load a product's personas.yaml if present, else None."""
    if not product_meta_path:
        return None
    config_file = product_personas_path(Path(product_meta_path))
    if not config_file.exists():
        logger.debug("No product personas.yaml at %s", config_file)
        return None
    try:
        with open(config_file) as f:
            data = yaml.safe_load(f) or {}
        return PersonasConfig.from_dict(data)
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Failed to load %s: %s", config_file, e)
        return None


def resolve_personas(
    product_meta_path: Optional[Path] = None,
    config: Optional[PersonasConfig] = None,
) -> list[PersonaSpec]:
    """Resolve the effective persona list.

    Args:
        product_meta_path: Path to the product meta-repo (to read personas.yaml).
        config: Pre-loaded PersonasConfig (takes precedence over the path).

    Returns:
        Ordered list of PersonaSpec to generate.
    """
    if config is None:
        config = load_product_personas(product_meta_path)

    builtins = builtin_catalog()

    # No product catalog → all built-in defaults.
    if config is None:
        return builtins

    enabled = set(config.defaults_enabled or [])
    builtin_by_id = {b.id: b for b in builtins}

    # Custom personas may override a built-in of the same id.
    custom_ids = {p.id for p in config.personas}

    resolved: list[PersonaSpec] = [
        b for b in builtins if b.id in enabled and b.id not in custom_ids
    ]
    resolved.extend(config.personas)

    # Preserve built-in entries that were overridden so order stays intuitive:
    # built-in order first (using override content), then net-new customs.
    if custom_ids & set(builtin_by_id):
        ordered: list[PersonaSpec] = []
        custom_by_id = {p.id: p for p in config.personas}
        for b in builtins:
            if b.id in custom_ids:
                ordered.append(custom_by_id[b.id])
            elif b.id in enabled:
                ordered.append(b)
        for p in config.personas:
            if p.id not in builtin_by_id:
                ordered.append(p)
        return ordered

    return resolved


def default_personas_config() -> PersonasConfig:
    """A starter PersonasConfig (all built-ins enabled, no customs).

    Written into a product meta-repo at scaffold time so teams have a file to
    edit when adding product-specific personas.
    """
    return PersonasConfig()


# ── Mutations (used by `dva product persona` commands) ───────────────────────

def save_product_personas(product_meta_path: Path, config: PersonasConfig) -> Path:
    """Write a PersonasConfig to the product meta-repo's personas.yaml."""
    config_file = product_personas_path(Path(product_meta_path))
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        yaml.safe_dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
    return config_file


def add_product_persona(product_meta_path: Path, spec: PersonaSpec) -> PersonasConfig:
    """Add (or replace by id) a custom persona in the product catalog.

    Loads the existing catalog (or a default one), upserts ``spec`` by ``id``,
    and persists. Returns the updated config.
    """
    config = load_product_personas(product_meta_path) or default_personas_config()
    config.personas = [p for p in config.personas if p.id != spec.id]
    config.personas.append(spec)
    save_product_personas(product_meta_path, config)
    return config


def remove_product_persona(product_meta_path: Path, persona_id: str) -> bool:
    """Remove a custom persona by id. Returns True if one was removed."""
    config = load_product_personas(product_meta_path)
    if config is None:
        return False
    before = len(config.personas)
    config.personas = [p for p in config.personas if p.id != persona_id]
    if len(config.personas) == before:
        return False
    save_product_personas(product_meta_path, config)
    return True
