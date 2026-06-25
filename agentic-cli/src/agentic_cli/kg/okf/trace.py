"""FREQ dev/QA traceability over an OKF bundle.

Transient Jira state (status/assignee/sprint) is NOT stored in the bundle; the
concept holds only the `jira:` anchor. When hydrate=True the value is resolved
live via Jira MCP (mcp0_jira_get_issue) by the caller; this module marks the
hydration point and never persists transient state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agentic_cli.kg.okf.bundle import Bundle


@dataclass
class FreqTrace:
    freq_id: str
    title: str
    jira: str
    part_of: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    implemented_by: list[tuple[str, str]] = field(default_factory=list)  # (title, resource)
    tested_by: list[tuple[str, str]] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)

    @property
    def dev_gap(self) -> bool:
        return not self.implemented_by

    @property
    def qa_gap(self) -> bool:
        return not self.tested_by


@dataclass
class TraceReport:
    freqs: list[FreqTrace] = field(default_factory=list)

    @property
    def gap_count(self) -> int:
        return sum(int(f.dev_gap) + int(f.qa_gap) for f in self.freqs)


def trace_bundle(root: Path, only_freq: str | None = None) -> TraceReport:
    bundle = Bundle.load(root)

    out: dict[str, list[tuple[str, str]]] = {}   # src -> [(role, dst)]
    inn: dict[str, list[tuple[str, str]]] = {}   # dst -> [(role, src)]
    for e in bundle.edges():
        out.setdefault(e.src, []).append((e.role, e.dst))
        inn.setdefault(e.dst, []).append((e.role, e.src))

    def title(rel: str) -> str:
        c = bundle.concepts.get(rel)
        return c.title if c else rel

    def resource(rel: str) -> str:
        c = bundle.concepts.get(rel)
        return c.fm.get("resource", "") if c else ""

    report = TraceReport()
    for c in bundle.freqs():
        if only_freq and c.fm.get("freq_id") != only_freq:
            continue
        rel = c.rel_path
        ft = FreqTrace(
            freq_id=c.fm.get("freq_id", "?"),
            title=c.title,
            jira=c.fm.get("jira", ""),
            part_of=[title(d) for r, d in out.get(rel, []) if r == "part-of"],
            references=[title(d) for r, d in out.get(rel, []) if r == "references"],
            implemented_by=[
                (title(s), resource(s)) for r, s in inn.get(rel, []) if r == "implements"
            ],
            tested_by=[
                (title(d), resource(d)) for r, d in out.get(rel, []) if r == "tested-by"
            ],
            acceptance_criteria=c.acceptance_criteria(),
        )
        report.freqs.append(ft)
    report.freqs.sort(key=lambda f: f.freq_id)
    return report
