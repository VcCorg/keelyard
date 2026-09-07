"""Every helper a shell script sources must be in the repository.

scripts/lib/require-node.sh was written, validated by running the scripts that
source it, committed with `git add -A`, and shipped missing: an unanchored
`lib/` rule in .gitignore silently excluded it. `git add -A` reported nothing,
the file existed locally so every check passed, and macOS users got

    package-mac.sh: line 56: .../scripts/lib/require-node.sh:
    No such file or directory

Nothing caught it because the tests never look at shell scripts and CI never
runs them. This does — it is cheap, and it is the exact failure that escaped.

It is a regex, not a shell parser: it can match a `source ...` that only appears
inside an echoed help string, and it skips anything whose path stays variable
after the common expansions. A cheap net with known holes beats no net, but do
not read a pass here as proof that every script resolves.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]

#: `source X` or `. X`, capturing the path argument.
SOURCE_RE = re.compile(r'^\s*(?:source|\.)\s+(?P<path>"[^"]+"|\S+)', re.M)

#: Paths resolved at runtime from the environment (nvm, user profiles) rather
#: than shipped in the repo. Not ours to guarantee.
EXTERNAL = ("$HOME", "${HOME}", "$NVM_DIR", "${NVM_DIR}", "/dev/null", "~/")

#: Directories holding things a tool creates, not things we ship. Excluded by
#: path component rather than by "is it gitignored", deliberately: the file this
#: test exists for was gitignored too, so that rule would have skipped the very
#: bug being guarded against.
GENERATED_DIRS = frozenset({
    ".venv", "venv", "node_modules", "dist", "site-packages", ".git",
})


def _shell_scripts() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.sh"], cwd=REPO,
                         capture_output=True, text=True, check=True)
    return [REPO / line for line in out.stdout.split("\n") if line.strip()]


def _tracked(path: Path) -> bool:
    rel = path.relative_to(REPO).as_posix()
    out = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO,
                         capture_output=True, text=True)
    return out.returncode == 0


def _sourced_paths(script: Path) -> list[str]:
    text = script.read_text(encoding="utf-8", errors="replace")
    found = []
    for m in SOURCE_RE.finditer(text):
        raw = m.group("path").strip('"')
        if raw.startswith(EXTERNAL) or any(e in raw for e in EXTERNAL):
            continue
        found.append(raw)
    return found


def _resolve(script: Path, raw: str) -> Path | None:
    """Resolve the common in-repo spellings; skip anything still variable."""
    expanded = (raw
                .replace("$SCRIPT_DIR", str(script.parent))
                .replace("${SCRIPT_DIR}", str(script.parent))
                .replace("$ROOT_DIR", str(REPO))
                .replace("${ROOT_DIR}", str(REPO))
                .replace('$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)',
                         str(script.parent))
                .replace('$(cd "$(dirname "$0")" && pwd)', str(script.parent)))
    if "$" in expanded:
        return None          # still dynamic — cannot judge it here
    resolved = Path(expanded)
    if GENERATED_DIRS & set(resolved.parts):
        return None          # created by a tool at runtime, never committed
    return resolved.resolve()


@pytest.mark.parametrize("script", _shell_scripts(), ids=lambda p: p.name)
def test_sourced_helpers_exist_and_are_tracked(script):
    for raw in _sourced_paths(script):
        resolved = _resolve(script, raw)
        if resolved is None:
            continue
        rel = script.relative_to(REPO)
        assert resolved.exists(), f"{rel} sources a missing file: {raw}"
        assert _tracked(resolved), (
            f"{rel} sources {resolved.relative_to(REPO)}, which exists locally "
            f"but is NOT in the repository — it will be missing for everyone "
            f"who clones. Check .gitignore."
        )


def test_the_node_gate_itself_is_tracked():
    """Named directly: this is the file that shipped missing."""
    gate = REPO / "scripts" / "lib" / "require-node.sh"
    assert gate.exists()
    assert _tracked(gate), "scripts/lib/require-node.sh is not tracked"
