#!/usr/bin/env python3
"""OKF FREQ traceability viewer (prototype / seed for `dva kg okf trace`).

Walks the typed cross-links of an OKF bundle and prints, per FREQ, the
dev->code and QA->test traceability that engineers consult before implementation:

  FREQ  ->  Requirement / Feature  (part-of)
        ->  domain entities         (references)
        <-  Code that implements it (implements)
        ->  Tests that verify it    (tested-by)
        +   acceptance criteria      (parsed from body)

Usage:
  python scripts/okf_trace.py [BUNDLE_DIR] [--freq CWOW-NNNNNN] [--gaps] [--hydrate]

Default BUNDLE_DIR: skills/domains/cwow-facility/knowledge

Transient state (Jira status/assignee/sprint) is NOT stored in the bundle. The
concept stores only the `jira:` anchor; with --hydrate the real `dva kg okf trace`
resolves live values via Jira MCP. This prototype shows the hydration point.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

LINK_RE = re.compile(r'\[[^\]]+\]\((?P<target>[^)\s]+)(?:\s+"(?P<role>[^"]+)")?\)')
FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
AC_RE = re.compile(r'^\s*-\s*(AC\d+:.*)$', re.MULTILINE)


def load_bundle(root: Path):
    """Return (concepts_by_path, edges) where edges = list of (src, role, dst)."""
    concepts = {}   # rel_path -> {fm, body}
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        rel = "/" + str(path.relative_to(root))
        concepts[rel] = {"fm": fm, "body": text[m.end():]}

    edges = []
    for rel, c in concepts.items():
        for lm in LINK_RE.finditer(c["body"]):
            target, role = lm.group("target"), lm.group("role")
            if role and target.startswith("/"):
                edges.append((rel, role, target))
    return concepts, edges


def title_of(concepts, rel):
    fm = concepts.get(rel, {}).get("fm", {})
    return fm.get("title", rel)


def hydrate_jira_status(jira_anchor: str, enabled: bool) -> str:
    """Resolve transient Jira state live. Not stored in the bundle.

    In `dva kg okf trace --hydrate` this calls Jira MCP:
        mcp0_jira_get_issue(issueIdOrKey=<key from anchor>) -> fields.status.name
    This prototype only marks the hydration point.
    """
    if not jira_anchor:
        return "(no jira anchor)"
    if not enabled:
        return "(live via Jira MCP — run with --hydrate)"
    return "(--hydrate: resolve via mcp0_jira_get_issue at runtime)"


def main() -> int:
    args = [a for a in sys.argv[1:]]
    only_freq = None
    show_gaps = False
    hydrate = False
    if "--hydrate" in args:
        hydrate = True
        args.remove("--hydrate")
    if "--gaps" in args:
        show_gaps = True
        args.remove("--gaps")
    if "--freq" in args:
        i = args.index("--freq")
        only_freq = args[i + 1]
        del args[i:i + 2]
    root = Path(args[0]) if args else (
        Path(__file__).resolve().parent.parent
        / "skills/domains/cwow-facility/knowledge"
    )

    concepts, edges = load_bundle(root)

    # Index edges
    out = {}  # src -> list[(role, dst)]
    inn = {}  # dst -> list[(role, src)]
    for s, role, d in edges:
        out.setdefault(s, []).append((role, d))
        inn.setdefault(d, []).append((role, s))

    freqs = [
        rel for rel, c in concepts.items()
        if c["fm"].get("type") == "FREQ"
        and (only_freq is None or c["fm"].get("freq_id") == only_freq)
    ]
    if not freqs:
        print("No matching FREQ concepts found.")
        return 1

    print(f"FREQ TRACEABILITY — {root.name}\n" + "=" * 60)
    gap_count = 0
    for rel in sorted(freqs, key=lambda r: concepts[r]["fm"].get("freq_id", "")):
        fm = concepts[rel]["fm"]
        body = concepts[rel]["body"]
        fid = fm.get("freq_id", "?")
        jira_anchor = fm.get("jira", "")
        print(f"\n{fid}  {fm.get('title', '')}")
        print(f"  jira: {jira_anchor or '-'}")
        print(f"  status [transient]: {hydrate_jira_status(jira_anchor, hydrate)}")

        parents = [d for r, d in out.get(rel, []) if r == "part-of"]
        refs = [d for r, d in out.get(rel, []) if r == "references"]
        impl = [s for r, s in inn.get(rel, []) if r == "implements"]
        tests = [d for r, d in out.get(rel, []) if r == "tested-by"]

        print("  part-of:     " + (", ".join(title_of(concepts, p) for p in parents) or "-"))
        print("  references:  " + (", ".join(title_of(concepts, p) for p in refs) or "-"))

        # DEV view
        print("  [DEV] implemented by:")
        if impl:
            for s in impl:
                res = concepts[s]["fm"].get("resource", "")
                print(f"     - {title_of(concepts, s)}  ({res})")
        else:
            print("     - (none) <-- DEV GAP: no Code implements this FREQ")
            gap_count += 1

        # QA view
        print("  [QA] verified by:")
        if tests:
            for d in tests:
                res = concepts[d]["fm"].get("resource", "")
                print(f"     - {title_of(concepts, d)}  ({res})")
        else:
            print("     - (none) <-- QA GAP: no Test verifies this FREQ")
            gap_count += 1

        acs = AC_RE.findall(body)
        print(f"  [QA] acceptance criteria ({len(acs)}):")
        for ac in acs:
            print(f"     - {ac}")

    print("\n" + "=" * 60)
    print(f"FREQs: {len(freqs)}   coverage gaps: {gap_count}")
    if show_gaps and gap_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
