"""Load an OKF bundle from disk: schema + concepts + resolved edges."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agentic_cli.kg.okf.model import Concept
from agentic_cli.kg.okf.schema import OKFSchema


@dataclass
class Edge:
    src: str          # source concept rel_path
    role: str
    dst: str          # target rel_path (may be unresolved)


@dataclass
class Bundle:
    root: Path
    schema: OKFSchema
    concepts: dict[str, Concept] = field(default_factory=dict)  # rel_path -> Concept

    @classmethod
    def load(cls, root: Path) -> "Bundle":
        root = Path(root)
        schema_path = root / "okf.schema.yaml"
        if not schema_path.exists():
            raise FileNotFoundError(f"No okf.schema.yaml in {root}")
        schema = OKFSchema.load(schema_path)
        concepts: dict[str, Concept] = {}
        for path in sorted(root.rglob("*.md")):
            # `index.md` files are reserved directory listings (OKF §6), not
            # concepts — skip them regardless of any frontmatter they carry.
            if path.name == "index.md":
                continue
            c = Concept.read(path, root)
            if c is not None:
                concepts[c.rel_path] = c
        return cls(root=root, schema=schema, concepts=concepts)

    def type_of(self, rel_path: str) -> str | None:
        c = self.concepts.get(rel_path)
        return c.type if c else None

    def edges(self) -> list[Edge]:
        out: list[Edge] = []
        for rel, c in self.concepts.items():
            for link in c.links():
                if link.role:
                    out.append(Edge(src=rel, role=link.role, dst=link.target))
        return out

    def freqs(self) -> list[Concept]:
        return [c for c in self.concepts.values() if c.type == "FREQ"]
