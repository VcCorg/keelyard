"""Registry of onboarding-IDE targets — vendor-neutral seam for skill placement.

The platform used to hardcode `if code_assist_tool == "windsurf"` (etc.) at
~16 different call sites. Adding a new IDE meant editing every one, and
migrating away from an IDE meant grep-and-hope. This module replaces that
model with a Protocol-based registry that each tool implements.

## Two independent concepts — don't confuse them

| Concept | Owner | Registry |
|---------|-------|----------|
| Build execution engine (who runs the code — Devin cloud, Devin CLI, VS Code + Copilot) | `agentic_cli/execution/` | `execution.registry` |
| Code-assist onboarding IDE (where SKILL.md lands on disk so the IDE reads it) | `agentic_cli/code_assist/` | this module |

Historically both used the same `code_assist_tool` string, which is why some
tools (Devin, VS Code+Copilot) show up in both. They're aligned by name but
not conflated — each concept has its own registry.

## Adding a new IDE

```python
from agentic_cli.code_assist import CodeAssistTool, register_tool
from pathlib import Path

def _my_ide_skills_dir(project_path: Path) -> Path:
    return project_path / ".my-ide" / "skills"

register_tool(CodeAssistTool(
    name="my-ide",
    label="MyIDE",
    description="Where MyIDE reads skill files from.",
    skills_dir=_my_ide_skills_dir,
    graphify_layout=lambda p: (
        p / ".my-ide" / "skills" / "graphify" / "SKILL.md",
        "name",  # {"name", "description-only"} — which frontmatter shape
    ),
    detect=lambda: (Path.home() / ".my-ide").exists(),
))
```

That's the *only* change needed — dispatch sites already delegate through
the registry.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


class ToolNotFoundError(KeyError):
    """Raised when a code-assist tool name is not registered."""


# ── Types ────────────────────────────────────────────────────────────────────


# Shape of a per-doc skill file for graphify (and the generic name/description
# frontmatter shape). "name" = both `name:` and `description:`; "description-only"
# = just `description:` (Cursor rules format).
_FRONTMATTER_SHAPES = ("name", "description-only")


@dataclass
class CodeAssistTool:
    """A code-assist onboarding IDE the platform can place skills into.

    Each strategy is a callable so that a tool with unusual layout rules can
    embed them without polluting the dispatch layer. Fields marked *optional*
    let a tool opt into a feature (e.g. Windsurf's user-level bridge) without
    every dispatch site having to know about it.
    """

    #: Stable identifier — used in configs, CLI options, and admin settings.
    name: str

    #: Short display label for UI/help text.
    label: str

    #: One-line description — surfaced in `keel code onboard --help` and admin UI.
    description: str = ""

    #: True when this IDE is legacy and shouldn't be a fresh install's default.
    #: Kept registered so existing repos onboarded against it keep working.
    deprecated: bool = False

    #: True when this IDE ships zero on-disk skills of its own (Devin embeds
    #: skills via the DRS snapshot, not the working tree). Registry-driven
    #: install steps skip the placement pass entirely for such tools.
    ephemeral: bool = False

    # ── Placement strategies ────────────────────────────────────────────────

    #: Repo-local skills directory for domain / project-context / etc. install.
    #: Called as ``skills_dir(project_path)``. Default is generic `.skills/`.
    skills_dir: Callable[[Path], Path] = field(
        default=lambda p: p / ".skills"
    )

    #: How the graphify per-repo skill file is laid out. Returns
    #: ``(dest_path, frontmatter_shape)`` where shape is one of
    #: ``_FRONTMATTER_SHAPES``. Default is generic `.skills/graphify/SKILL.md`.
    graphify_layout: Callable[[Path], tuple[Path, str]] = field(
        default=lambda p: (p / ".skills" / "graphify" / "SKILL.md", "name")
    )

    #: Persona context file — used by `persona_workspace.assemble_persona_skill`.
    #: Called as ``persona_context_path(root, persona_name)``.
    persona_context_path: Callable[[Path, str], Path] = field(
        default=lambda root, name: root / ".skills" / name / "SKILL.md"
    )

    #: Domain-context ``README.md`` layout description — inline snippet the
    #: docs use to render the on-disk structure. Falls back to a generic tree.
    domain_readme_structure: Optional[Callable[[str], str]] = None

    # ── Optional post-placement bridge ──────────────────────────────────────

    #: Bridge repo-local `.skills/` into a per-user directory the IDE actually
    #: scans (e.g. Windsurf → ``~/.codeium/windsurf/skills/<domain>__<name>``).
    #: Signature: ``bridge_to_user_dir(repo_skills_dir, domain)`` returning a
    #: list of dicts describing what was bridged (for logs / manifests). If
    #: the IDE reads directly from the repo, leave this None.
    bridge_to_user_dir: Optional[Callable[[Path, str], list[dict[str, Any]]]] = None

    # ── Auto-detection ──────────────────────────────────────────────────────

    #: True iff this IDE is installed on the current machine. Order in the
    #: registry decides tie-breaking during `detect_tool()` — non-deprecated
    #: tools are tried first.
    detect: Callable[[], bool] = field(default=lambda: False)


# ── Registry ─────────────────────────────────────────────────────────────────


_REGISTRY: dict[str, CodeAssistTool] = {}


def register_tool(tool: CodeAssistTool) -> None:
    """Register (or replace) a code-assist tool by name."""
    _REGISTRY[tool.name] = tool


def list_tools(include_deprecated: bool = True) -> list[CodeAssistTool]:
    """Return every registered tool. Non-deprecated first, deprecated last."""
    active = [t for t in _REGISTRY.values() if not t.deprecated]
    if not include_deprecated:
        return active
    deprecated = [t for t in _REGISTRY.values() if t.deprecated]
    return active + deprecated


def get_tool(name: str) -> CodeAssistTool:
    """Return the tool by name, or raise ``ToolNotFoundError``."""
    tool = _REGISTRY.get(name)
    if tool is None:
        raise ToolNotFoundError(
            f"Unknown code-assist tool '{name}'. "
            f"Known: {sorted(_REGISTRY.keys())}."
        )
    return tool


def resolve_tool_name(
    name: Optional[str],
    default: str = "generic",
    admin_default: Optional[str] = None,
    enabled: Optional[list[str]] = None,
) -> str:
    """Resolve a caller-supplied name into a registered tool name.

    ``None`` or ``"auto"`` triggers detection (env override → each tool's
    ``detect()``). An unknown explicit name falls back to the admin's own
    default (if any), then ``default`` — never raises, so a stale config
    doesn't brick onboard.

    ``admin_default`` — the platform admin's chosen default onboarding IDE
    (from ``AppSettings.onboarding_ide.default``). Consulted after live
    detection but before the hardcoded ``default`` fallback, so a tenant
    that picked "cursor" gets Cursor when no IDE was auto-detected.

    ``enabled`` — restrict detection to the admin's allow-list. A tool that
    isn't in this list is skipped by ``detect_tool`` and refused by an
    explicit name (falls through to admin_default / default).
    """
    allow = _admin_allowlist(enabled)

    if name and name != "auto":
        if name in _REGISTRY and (allow is None or name in allow):
            return name
        # Not permitted by admin (or unknown). Fall through so we still return
        # SOMETHING sensible instead of raising inside onboard.
        return _fallback(admin_default, default, allow)

    return detect_tool(default, admin_default=admin_default, enabled=allow)


def detect_tool(
    default: str = "generic",
    admin_default: Optional[str] = None,
    enabled: Optional[list[str]] = None,
) -> str:
    """Best-effort detection of the active code-assist tool.

    Order: explicit ``KEEL_CODE_ASSIST_TOOL`` env override → each registered
    tool's ``detect()`` predicate (non-deprecated first, deprecated last) →
    ``admin_default`` (if valid) → ``default``. Tools not in ``enabled``
    (when supplied) are skipped so a disabled IDE never wins auto-detection.
    """
    allow = _admin_allowlist(enabled)
    override = os.environ.get("KEEL_CODE_ASSIST_TOOL", "").strip().lower()
    if override and override in _REGISTRY and (allow is None or override in allow):
        return override
    for tool in list_tools():
        if allow is not None and tool.name not in allow:
            continue
        try:
            if tool.detect():
                return tool.name
        except Exception:  # noqa: BLE001 — a broken detector must never crash callers
            continue
    return _fallback(admin_default, default, allow)


def _admin_allowlist(enabled: Optional[list[str]]) -> Optional[set[str]]:
    """Normalize an admin ``enabled`` list into a set, or None for no filter."""
    if enabled is None:
        return None
    return {str(n).strip().lower() for n in enabled if str(n).strip()}


def _fallback(
    admin_default: Optional[str],
    default: str,
    allow: Optional[set[str]],
) -> str:
    """Resolve terminal fallback: admin_default > default > 'generic'."""
    for candidate in (admin_default, default, "generic"):
        if not candidate:
            continue
        if candidate not in _REGISTRY:
            continue
        if allow is not None and candidate not in allow:
            continue
        return candidate
    # Nothing usable — return the caller's default even if not registered, so
    # error surfaces at the caller (get_tool()) with a clear message.
    return default


# ── Built-in tools ───────────────────────────────────────────────────────────


def _cursor_skills_dir(p: Path) -> Path:
    return p / ".cursorrules"


def _cursor_graphify(p: Path) -> tuple[Path, str]:
    return (p / ".cursor" / "rules" / "graphify.md", "description-only")


def _cursor_persona_path(root: Path, name: str) -> Path:
    return root / ".cursor" / "rules" / f"{name}.md"


def _devin_skills_dir(p: Path) -> Path:
    return p / ".devin" / "skills"


def _devin_graphify(p: Path) -> tuple[Path, str]:
    return (p / ".devin" / "skills" / "graphify" / "SKILL.md", "name")


def _devin_persona_path(root: Path, name: str) -> Path:
    return root / ".devin" / "skills" / name / "SKILL.md"


def _generic_persona_path(root: Path, name: str) -> Path:
    return root / ".skills" / name / "SKILL.md"


def _windsurf_persona_path(root: Path, name: str) -> Path:
    # Windsurf's persona-context file was historically the flat workflow
    # file — kept as-is so migration doesn't move an existing user's files.
    return root / ".windsurf" / "workflows" / f"{name}.md"


def _windsurf_bridge(repo_skills_dir: Path, domain: str) -> list[dict[str, Any]]:
    """Lazy-import the Windsurf bridge so importing the registry stays cheap."""
    from agentic_cli.kg.domain_skills import install_skills_to_windsurf

    return install_skills_to_windsurf(repo_skills_dir, domain)


def _detect_devin() -> bool:
    return bool(os.environ.get("DEVIN_API_KEY") or os.environ.get("DEVIN_SESSION_ID"))


def _detect_cursor() -> bool:
    return (Path.home() / ".cursor").exists()


def _detect_windsurf() -> bool:
    return (Path.home() / ".codeium" / "windsurf").exists()


def _windsurf_domain_readme_structure(domain: str) -> str:
    return f"""```
.domain/
├── kg-context.md          # Shared business context from Knowledge Graph
├── domain-metadata.json   # Domain metadata and configuration
└── architecture.md        # Domain architecture patterns

.windsurf/
└── workflows/
    ├── {domain}-domain-skill.md  # Domain context skill for AI assistants
    └── <superpowers-skills>.md  # Superpowers skills (if bootstrapped)
```"""


# Order below decides `detect_tool()` tie-breaking: Devin first (that's the
# platform's primary post-migration), then Cursor, then generic, and Windsurf
# last as deprecated. Any custom tool `register_tool()`'d later slots in where
# it was registered.

register_tool(CodeAssistTool(
    name="devin",
    label="Devin",
    description="Devin's project-skill layout at .devin/skills/<name>/SKILL.md.",
    skills_dir=_devin_skills_dir,
    graphify_layout=_devin_graphify,
    persona_context_path=_devin_persona_path,
    ephemeral=False,
    detect=_detect_devin,
))

register_tool(CodeAssistTool(
    name="cursor",
    label="Cursor",
    description="Cursor rules under .cursorrules/ and conditional rules under .cursor/rules/.",
    skills_dir=_cursor_skills_dir,
    graphify_layout=_cursor_graphify,
    persona_context_path=_cursor_persona_path,
    detect=_detect_cursor,
))

register_tool(CodeAssistTool(
    name="generic",
    label="Generic",
    description="Portable .skills/<name>/SKILL.md layout — safe default for any IDE.",
    # `detect` intentionally returns False: generic never wins auto-detection
    # when a real IDE is installed. It's only reached as the terminal fallback
    # in `detect_tool()` (via its `default` argument) when no other tool
    # matches — which is the correct semantics for a portable, IDE-agnostic
    # layout.
))

register_tool(CodeAssistTool(
    name="windsurf",
    label="Windsurf (deprecated)",
    description=(
        "Windsurf/Cascade: portable .skills/<name>/ layout, bridged into "
        "~/.codeium/windsurf/skills/<domain>__<name>. Kept for existing "
        "installs after the migration to Devin."
    ),
    deprecated=True,
    # Windsurf uses the generic .skills layout — the difference is the bridge.
    graphify_layout=lambda p: (
        p / ".skills" / "graphify" / "SKILL.md", "name"
    ),
    persona_context_path=_windsurf_persona_path,
    bridge_to_user_dir=_windsurf_bridge,
    domain_readme_structure=_windsurf_domain_readme_structure,
    detect=_detect_windsurf,
))
