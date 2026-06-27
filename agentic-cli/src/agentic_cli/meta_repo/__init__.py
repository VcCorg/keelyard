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
)
from .scaffold import scaffold_domain_meta_repo
from .product_scaffold import (
    scaffold_product_meta_repo,
    add_exception,
    list_exceptions,
)
from .git_utils import add_submodule, detect_default_branch, detect_git_host

__all__ = [
    "detect_domain_meta_repo",
    "MetaRepoConfig",
    "GovernanceConfig",
    "ProductConfig",
    "ExceptionEntry",
    "scaffold_domain_meta_repo",
    "scaffold_product_meta_repo",
    "add_exception",
    "list_exceptions",
    "add_submodule",
    "detect_default_branch",
    "detect_git_host",
]
