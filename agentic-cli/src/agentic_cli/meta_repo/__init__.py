"""Domain meta-repo management for code onboarding.

This module provides functionality to create, detect, and integrate domain meta-repos
that follow the meta-repo standards (submodules, .platform configs, governance rules).
"""

__version__ = "0.1.0"

from .detector import detect_domain_meta_repo
from .config import (
    MetaRepoConfig,
    GovernanceConfig,
    ProductConfig,
    ExceptionEntry,
    PersonaSpec,
    PersonaSection,
    PersonasConfig,
    BUILTIN_PERSONA_IDS,
)
from .scaffold import scaffold_domain_meta_repo
from .product_scaffold import (
    scaffold_product_meta_repo,
    add_exception,
    list_exceptions,
)
from .git_utils import add_submodule, detect_default_branch, detect_git_host
from .template_manifest import TEMPLATE_VERSION, read_manifest, write_manifest
from .template_drift import DriftReport, FileDrift, classify, classify_domain
from .template_upgrade import UpgradeReport, upgrade, upgrade_domain
from .template_overlay import apply_overlay, list_overlay, overlay_root
from .template_promote import PromotionResult, promotable, promote, promote_domain

__all__ = [
    "detect_domain_meta_repo",
    "MetaRepoConfig",
    "GovernanceConfig",
    "ProductConfig",
    "ExceptionEntry",
    "PersonaSpec",
    "PersonaSection",
    "PersonasConfig",
    "BUILTIN_PERSONA_IDS",
    "scaffold_domain_meta_repo",
    "scaffold_product_meta_repo",
    "add_exception",
    "list_exceptions",
    "add_submodule",
    "detect_default_branch",
    "detect_git_host",
    "TEMPLATE_VERSION",
    "read_manifest",
    "write_manifest",
    "DriftReport",
    "FileDrift",
    "classify",
    "classify_domain",
    "UpgradeReport",
    "upgrade",
    "upgrade_domain",
    "apply_overlay",
    "list_overlay",
    "overlay_root",
    "PromotionResult",
    "promotable",
    "promote",
    "promote_domain",
]
