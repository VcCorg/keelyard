"""The writable layer of the domain meta-repo template.

The template's defaults live as Python string literals in :mod:`scaffold`, which
makes them impossible to *write back* to programmatically. Rather than rewrite
1400 lines of literals, this adds an **overlay**: a directory of real files that
are rendered over the generated defaults at the very end of scaffolding.

That single indirection is what turns the template from read-only into a
two-way artifact:

- ``keel domain template status``  — is my repo behind the template?      (P1)
- ``keel domain template upgrade`` — pull template changes down.          (P2)
- ``keel domain template promote`` — push a local improvement UP, here.   (P3b)

Because :func:`~agentic_cli.meta_repo.template_drift.render_reference` renders
through the same scaffold path, an overlay file participates in drift detection
automatically: promoting a file makes every *other* domain's next
``template status`` report ``template-updated`` and fast-forward it.

Tokenization
------------
A promoted file is domain-specific ("cwow-apoc", "CWOW", an owner email). To
become a template it must be turned back into placeholders — the inverse of
rendering. That is a lossy, heuristic operation, so this module never promotes
silently: :func:`plan_promotion` reports every substitution it made *and* every
residual domain-specific string it could not tokenize, for a human to review.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

#: Directory name of the in-tree overlay, alongside this module. Deliberately
#: not "template_overlay": a directory of that name would sit next to
#: ``template_overlay.py`` inside an importable package.
OVERLAY_DIRNAME = "overlay"

#: Environment override, so an org can host the overlay outside the package.
OVERLAY_ENV = "KEEL_TEMPLATE_OVERLAY"

#: Render inputs that become placeholders. Order matters only for display;
#: substitution is always longest-value-first (see :func:`tokenize`).
PLACEHOLDERS = ("domain", "product", "description", "owner")

#: ``{{name}}`` rather than ``{name}``: template bodies contain literal braces
#: (JSON, shell parameter expansion, code samples), and single braces would make
#: rendering ambiguous and fragile.
_TOKEN_FMT = "{{%s}}"
_TOKEN_RE = re.compile(r"\{\{(" + "|".join(PLACEHOLDERS) + r")\}\}")

#: A value shorter than this is too collision-prone to blind-replace
#: (e.g. product "MT" would corrupt the word "MTTR").
MIN_TOKENIZABLE = 3

#: Patterns that usually mean "this content is still domain-specific" and needs
#: human eyes even after tokenization.
_RESIDUAL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b[A-Z][A-Z0-9]{1,9}-\d+\b", "Jira-style issue key"),
    (r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", "email address"),
    (r"https?://[^\s\"'>)]+", "absolute URL"),
    (r"\b\d{4}-\d{2}-\d{2}\b", "date (would be frozen into the template)"),
)

#: Directories inside the overlay root that are never template content. The
#: overlay is normally a directory *inside a git repo* (that's how a promotion
#: gets branched and reviewed), so without this every git object would be
#: rendered into new meta-repos and corrupt their own ``.git``.
_OVERLAY_PRUNE_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".idea", ".vscode",
})

#: Overlay files that are bookkeeping for the overlay itself, not template content.
_OVERLAY_IGNORED_NAMES = frozenset({".DS_Store", ".gitkeep", ".keep", "README.md"})

#: Files that must never be promoted: they are per-domain data or derived, so a
#: template copy would be actively wrong for every other domain.
_NEVER_PROMOTE = {
    ".platform/config/domain.yaml",
    ".platform/config/repos.yaml",
    ".platform/template.json",
    ".platform/skills-manifest.json",
}


# ── Overlay location ────────────────────────────────────────────────────────

def overlay_root(create: bool = False) -> Path:
    """Resolve the overlay directory.

    Honours ``$KEEL_TEMPLATE_OVERLAY`` so an org can keep the overlay in its own
    governance repo; otherwise uses the in-tree directory shipped with the
    package (the same "in-repo default" model as the skills registry).
    """
    override = os.environ.get(OVERLAY_ENV, "").strip()
    root = Path(override).expanduser() if override else Path(__file__).parent / OVERLAY_DIRNAME
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def list_overlay(root: Optional[Path] = None) -> list[str]:
    """Relative paths currently provided by the overlay (sorted).

    Skips VCS/tooling directories and the overlay's own bookkeeping files, so
    hosting the overlay inside a git repo never leaks repository internals into
    generated meta-repos.
    """
    root = Path(root) if root is not None else overlay_root()
    if not root.is_dir():
        return []

    out: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if _OVERLAY_PRUNE_DIRS.intersection(rel.parts[:-1]):
            continue
        # Top-level bookkeeping only: docs/README.md IS legitimate template content.
        if len(rel.parts) == 1 and rel.name in _OVERLAY_IGNORED_NAMES:
            continue
        if rel.name == ".DS_Store":
            continue
        out.append(rel.as_posix())
    return sorted(out)


# ── Render (overlay → meta-repo) ────────────────────────────────────────────

def render(content: str, **inputs: str) -> str:
    """Substitute ``{{placeholder}}`` tokens with the render inputs."""
    def sub(m: re.Match) -> str:
        return str(inputs.get(m.group(1), "") or "")

    return _TOKEN_RE.sub(sub, content)


def apply_overlay(
    meta_repo_path: Path,
    domain: str = "",
    product: str = "",
    description: str = "",
    owner: str = "",
    root: Optional[Path] = None,
) -> list[str]:
    """Render every overlay file into a freshly-scaffolded meta-repo.

    Called at the end of scaffolding, *before* the template manifest is written,
    so overlay content is part of the recorded baseline. A missing or empty
    overlay is a no-op — which is exactly the state of a fresh install, so this
    changes nothing until someone promotes a file.

    Returns the relative paths written.
    """
    root = Path(root) if root is not None else overlay_root()
    rels = list_overlay(root)
    if not rels:
        return []

    inputs = {"domain": domain, "product": product,
              "description": description, "owner": owner}
    written: list[str] = []
    for rel in rels:
        src, dest = root / rel, Path(meta_repo_path) / rel
        try:
            body = src.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            logger.warning("Skipping unreadable overlay file %s: %s", rel, e)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render(body, **inputs), encoding="utf-8")
        written.append(rel)

    logger.debug("Applied %d overlay file(s) to %s", len(written), meta_repo_path)
    return written


# ── Tokenize (meta-repo → overlay) ──────────────────────────────────────────

@dataclass
class Substitution:
    """One placeholder substitution made while tokenizing."""

    placeholder: str
    value: str
    count: int

    def to_dict(self) -> dict:
        return {"placeholder": self.placeholder, "value": self.value,
                "count": self.count}


@dataclass
class Residual:
    """A domain-specific-looking string that tokenization could not remove."""

    kind: str
    sample: str
    count: int

    def to_dict(self) -> dict:
        return {"kind": self.kind, "sample": self.sample, "count": self.count}


def tokenize(content: str, **inputs: str) -> tuple[str, list[Substitution], list[str]]:
    """Replace concrete render inputs with ``{{placeholder}}`` tokens.

    The inverse of :func:`render`, and necessarily heuristic. Values are
    substituted longest-first so that a value which contains another (product
    "CWOW" inside domain "cwow-apoc") cannot corrupt it, and matching is
    case-sensitive with word boundaries.

    Returns ``(tokenized, substitutions, skipped_values)`` where
    ``skipped_values`` names inputs too short to substitute safely.
    """
    subs: list[Substitution] = []
    skipped: list[str] = []

    candidates = [(name, str(inputs.get(name) or "")) for name in PLACEHOLDERS]
    # Longest value first: prevents a shorter value from eating part of a longer.
    candidates.sort(key=lambda kv: len(kv[1]), reverse=True)

    for name, value in candidates:
        if not value:
            continue
        if len(value) < MIN_TOKENIZABLE:
            skipped.append(name)
            continue
        pattern = re.compile(rf"(?<![\w-]){re.escape(value)}(?![\w-])")
        content, n = pattern.subn(_TOKEN_FMT % name, content)
        if n:
            subs.append(Substitution(name, value, n))

    return content, subs, skipped


def find_residuals(content: str, domain: str = "") -> list[Residual]:
    """Flag content that still looks domain-specific after tokenization.

    Tokenization only knows about the four render inputs. Real governance docs
    also name repos, tickets, people and dates — none of which belong in a shared
    template. These are reported, not removed, because only a human can judge
    them.
    """
    out: list[Residual] = []
    for pattern, kind in _RESIDUAL_PATTERNS:
        hits = re.findall(pattern, content)
        if hits:
            out.append(Residual(kind, str(hits[0])[:80], len(hits)))

    # Individual words of the domain slug (e.g. "apoc" from "cwow-apoc") are too
    # short/ambiguous to tokenize but are a strong leak signal.
    for part in {p for p in re.split(r"[-_]", domain or "") if len(p) >= MIN_TOKENIZABLE}:
        hits = re.findall(rf"(?<![\w-]){re.escape(part)}(?![\w-])", content)
        if hits:
            out.append(Residual("domain fragment", part, len(hits)))
    return out


# ── Promotion plan ──────────────────────────────────────────────────────────

@dataclass
class PromotionPlan:
    """What promoting one file to the template overlay would do."""

    path: str
    status: str                       # the drift status that made it eligible
    overlay_path: Path
    content: str = ""
    substitutions: list[Substitution] = field(default_factory=list)
    skipped_values: list[str] = field(default_factory=list)
    residuals: list[Residual] = field(default_factory=list)
    replaces_existing: bool = False

    @property
    def needs_review(self) -> bool:
        """True when a human should read the tokenized body before publishing."""
        return bool(self.residuals or self.skipped_values or not self.substitutions)

    def to_dict(self) -> dict:
        return {
            "path": self.path, "status": self.status,
            "overlay_path": str(self.overlay_path),
            "substitutions": [s.to_dict() for s in self.substitutions],
            "skipped_values": self.skipped_values,
            "residuals": [r.to_dict() for r in self.residuals],
            "replaces_existing": self.replaces_existing,
            "needs_review": self.needs_review,
        }


class PromotionError(RuntimeError):
    """Raised when a file cannot be promoted into the template."""


def plan_promotion(
    meta_repo_path: Path,
    rel: str,
    status: str,
    inputs: dict,
    root: Optional[Path] = None,
) -> PromotionPlan:
    """Build (without writing) the plan for promoting one file upstream."""
    rel = rel.replace("\\", "/").strip("/")
    if rel in _NEVER_PROMOTE:
        raise PromotionError(
            f"'{rel}' is per-domain data — a template copy would be wrong for "
            f"every other domain")
    if ".." in Path(rel).parts:
        raise PromotionError(f"Unsafe path: {rel}")

    src = Path(meta_repo_path) / rel
    if not src.is_file():
        raise PromotionError(f"'{rel}' does not exist in {meta_repo_path}")
    try:
        local = src.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        raise PromotionError(f"'{rel}' is not readable UTF-8 text: {e}") from e

    body, subs, skipped = tokenize(local, **inputs)
    root = Path(root) if root is not None else overlay_root()
    overlay_path = root / rel
    return PromotionPlan(
        path=rel, status=status, overlay_path=overlay_path, content=body,
        substitutions=subs, skipped_values=skipped,
        residuals=find_residuals(body, inputs.get("domain", "")),
        replaces_existing=overlay_path.is_file(),
    )


def write_promotion(plan: PromotionPlan) -> Path:
    """Write a planned promotion into the overlay.

    Callers are expected to have run :func:`verify_round_trip` first — see
    :func:`~agentic_cli.meta_repo.template_promote.promote`, which refuses to
    write a template that would not regenerate the file it came from.
    """
    plan.overlay_path.parent.mkdir(parents=True, exist_ok=True)
    plan.overlay_path.write_text(plan.content, encoding="utf-8")
    return plan.overlay_path


def verify_round_trip(plan: PromotionPlan, inputs: dict, original: str) -> bool:
    """Does rendering the tokenized body reproduce the file it came from?"""
    return render(plan.content, **inputs) == original


__all__ = [
    "OVERLAY_DIRNAME", "OVERLAY_ENV", "PLACEHOLDERS", "MIN_TOKENIZABLE",
    "Substitution", "Residual", "PromotionPlan", "PromotionError",
    "overlay_root", "list_overlay", "render", "apply_overlay",
    "tokenize", "find_residuals", "plan_promotion", "write_promotion",
    "verify_round_trip",
]
