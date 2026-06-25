"""OKF concept model: frontmatter + Markdown body, with typed-link parsing."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# [text](/path/to.md "role")  — role optional
LINK_RE = re.compile(r'\[[^\]]+\]\((?P<target>[^)\s]+)(?:\s+"(?P<role>[^"]+)")?\)')
FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
AC_RE = re.compile(r'^\s*-\s*(AC\d+:.*)$', re.MULTILINE)


@dataclass
class Link:
    target: str          # bundle-absolute path, e.g. /concepts/x.md
    role: str | None     # semantic role (the link title) or None for navigational


@dataclass
class Concept:
    """A single OKF concept file (frontmatter + body)."""

    fm: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    rel_path: str = ""   # bundle-absolute path, e.g. /concepts/facility.md

    # convenience accessors
    @property
    def id(self) -> str:
        """Concept ID. Per OKF §2 this is the file path minus the `.md` suffix
        (e.g. `/features/cwow-27901/freq-cwow-27901.md` -> `features/cwow-27901/
        freq-cwow-27901`). A legacy `id` frontmatter key, if present, wins."""
        if self.fm.get("id"):
            return self.fm["id"]
        rel = self.rel_path.lstrip("/")
        return rel[:-3] if rel.endswith(".md") else rel

    @property
    def type(self) -> str:
        return self.fm.get("type", "")

    @property
    def title(self) -> str:
        return self.fm.get("title", self.id or self.rel_path)

    @classmethod
    def parse(cls, text: str, rel_path: str = "") -> "Concept | None":
        m = FRONTMATTER_RE.match(text)
        if not m or yaml is None:
            return None
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            return None
        return cls(fm=fm, body=text[m.end():], rel_path=rel_path)

    @classmethod
    def read(cls, path: Path, root: Path) -> "Concept | None":
        rel = "/" + str(Path(path).relative_to(root))
        return cls.parse(Path(path).read_text(encoding="utf-8"), rel)

    def links(self) -> list[Link]:
        out: list[Link] = []
        for lm in LINK_RE.finditer(self.body):
            target = lm.group("target")
            if target.startswith("/"):
                out.append(Link(target=target, role=lm.group("role")))
        return out

    def acceptance_criteria(self) -> list[str]:
        return AC_RE.findall(self.body)

    def to_markdown(self) -> str:
        if yaml is None:
            raise RuntimeError("PyYAML required to serialize OKF concepts")
        fm_yaml = yaml.safe_dump(self.fm, sort_keys=False, allow_unicode=True).rstrip()
        body = self.body if self.body.startswith("\n") else "\n" + self.body
        return f"---\n{fm_yaml}\n---\n{body}"

    def write(self, root: Path) -> Path:
        path = root / self.rel_path.lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path
