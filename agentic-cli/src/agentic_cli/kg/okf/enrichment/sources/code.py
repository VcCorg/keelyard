"""CodebaseSource — advertises a repository's structure as OKF concepts.

This is the KEEL analog of the GCP agent's BigQuerySource: instead of datasets and
tables, it surfaces the code knowledge a repo carries:

  CodeModule   - a top-level source package/directory
  Component    - the repository as a whole (overview / architecture anchor)
  APIEndpoint  - present when the analyzer detects an API surface

`read_concept` returns structured metadata (languages, frameworks, key files,
file inventory, README excerpt) that the LLM turns into an OKF document body.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic_cli.kg.okf.enrichment.source import ConceptRef, Source
from agentic_cli.kg.okf.schema import slugify

# Directories we never treat as source modules.
_IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build",
    "target", ".idea", ".vscode", ".pytest_cache", ".mypy_cache", "coverage",
    ".gradle", "out", "bin", "obj",
}
_SOURCE_DIRS = ("src", "lib", "app", "internal", "pkg", "cmd")
_README_NAMES = ("README.md", "README.rst", "README.txt", "readme.md")
_CODE_EXTS = {".py", ".java", ".ts", ".tsx", ".js", ".go", ".rb", ".kt", ".cs", ".scala"}
_MAX_MODULES = 40
_EXCERPT_CHARS = 1500


class CodebaseSource(Source):
    name = "code"

    def __init__(self, project_path: Path, analysis: Any | None = None):
        self.root = Path(project_path).resolve()
        if not self.root.exists():
            raise ValueError(f"project path does not exist: {self.root}")
        self._analysis = analysis
        self._refs: list[ConceptRef] | None = None

    # -- analysis (lazy) --------------------------------------------------
    @property
    def analysis(self) -> Any:
        if self._analysis is None:
            from agentic_cli.analyzer.detector import analyze_project
            self._analysis = analyze_project(self.root)
        return self._analysis

    # -- module discovery -------------------------------------------------
    def _module_dirs(self) -> list[Path]:
        """Find candidate source-module directories (one or two levels deep)."""
        roots: list[Path] = []
        # Prefer conventional source roots; fall back to repo root.
        bases = [self.root / d for d in _SOURCE_DIRS if (self.root / d).is_dir()]
        if not bases:
            bases = [self.root]

        dirs: list[Path] = []
        for base in bases:
            for child in sorted(base.iterdir()):
                if not child.is_dir() or child.name in _IGNORE_DIRS or child.name.startswith("."):
                    continue
                if self._has_code(child):
                    dirs.append(child)
        # De-dup and cap.
        seen: set[Path] = set()
        for d in dirs:
            if d not in seen:
                seen.add(d)
                roots.append(d)
            if len(roots) >= _MAX_MODULES:
                break
        return roots

    def _has_code(self, d: Path, limit: int = 200) -> bool:
        count = 0
        for p in d.rglob("*"):
            if count >= limit:
                break
            if p.is_file() and p.suffix in _CODE_EXTS:
                return True
            count += 1
        return False

    # -- Source interface -------------------------------------------------
    def list_concepts(self) -> list[ConceptRef]:
        if self._refs is not None:
            return self._refs
        refs: list[ConceptRef] = []

        # 1) Repository-level Component (architecture anchor).
        repo_slug = slugify(self.root.name)
        refs.append(
            ConceptRef(
                id=("components", repo_slug),
                type="Component",
                resource=str(self.root),
                hint={"repo_root": True},
            )
        )

        # 2) One CodeModule per discovered source directory.
        for d in self._module_dirs():
            refs.append(
                ConceptRef(
                    id=("modules", slugify(d.name)),
                    type="CodeModule",
                    resource=str(d),
                    hint={"path": str(d)},
                )
            )

        # 3) APIEndpoint anchor if the analyzer detected an API surface.
        api_types = list(getattr(self.analysis, "api_types", []) or [])
        if api_types:
            refs.append(
                ConceptRef(
                    id=("apis", f"{repo_slug}-api"),
                    type="APIEndpoint",
                    resource=str(self.root),
                    hint={"api_types": api_types},
                )
            )

        self._refs = refs
        return refs

    def read_concept(self, ref: ConceptRef) -> dict[str, Any]:
        a = self.analysis
        common = {
            "repository": self.root.name,
            "languages": list(getattr(a, "languages", []) or []),
            "frameworks": list(getattr(a, "frameworks", []) or []),
        }

        if ref.type == "Component" and ref.hint.get("repo_root"):
            return {
                **common,
                "kind": "repository-overview",
                "build_tools": list(getattr(a, "build_tools", []) or []),
                "test_frameworks": list(getattr(a, "test_frameworks", []) or []),
                "databases": list(getattr(a, "databases", []) or []),
                "api_types": list(getattr(a, "api_types", []) or []),
                "entry_points": list(getattr(a, "entry_points", []) or []),
                "module_structure": list(getattr(a, "module_structure", []) or []),
                "has_docker": bool(getattr(a, "has_docker", False)),
                "readme_excerpt": self._readme_excerpt(self.root),
                "top_dependencies": list(getattr(a, "dependencies", []) or [])[:30],
            }

        if ref.type == "CodeModule":
            mod = Path(ref.hint["path"])
            return {
                **common,
                "kind": "code-module",
                "module": mod.name,
                "relative_path": str(mod.relative_to(self.root)),
                "files": self._file_inventory(mod),
                "readme_excerpt": self._readme_excerpt(mod),
            }

        if ref.type == "APIEndpoint":
            return {
                **common,
                "kind": "api-surface",
                "api_types": ref.hint.get("api_types", []),
                "source_patterns": list(getattr(a, "source_patterns", []) or []),
            }

        return common

    # -- helpers ----------------------------------------------------------
    def _readme_excerpt(self, d: Path) -> str:
        for name in _README_NAMES:
            p = d / name
            if p.is_file():
                try:
                    return p.read_text(errors="ignore")[:_EXCERPT_CHARS]
                except OSError:
                    return ""
        return ""

    def _file_inventory(self, d: Path, limit: int = 60) -> list[str]:
        out: list[str] = []
        for p in sorted(d.rglob("*")):
            if len(out) >= limit:
                break
            if p.is_file() and p.suffix in _CODE_EXTS:
                try:
                    out.append(str(p.relative_to(self.root)))
                except ValueError:
                    out.append(p.name)
        return out
