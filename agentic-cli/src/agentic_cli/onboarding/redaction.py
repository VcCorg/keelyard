"""Residual-risk scanning for extracted onboarding intent.

Onboarding docs are written for humans, so they carry the things humans need
and machines must not keep: names, email addresses, internal hostnames, and
credentials-adjacent strings. We capture the *intent* of an instruction and
discard the source body, which means the only place risk can leak is a
candidate's own text.

Two rules make that safe, and both are enforced here rather than by convention:

1. **A risky candidate is held, and held text is never written.** :class:`Risk`
   deliberately carries no matched span — only a kind. Callers show the reviewer
   *what kind* of identifier was found and the citation pointing back at the
   source; the reviewer reads the original. Nothing else would be safe, because
   the review file is committed to the meta-repo.
2. **Guard terms are checked before anything is written**, never after. The
   review file is git-visible, so writing first and scanning later would make it
   the very disclosure vector ``scripts/check-no-company-data.sh`` exists to
   prevent.

Patterns are kept deliberately close to that script's, so the two agree about
what counts as dangerous. Terms themselves are never hardcoded — they arrive via
``$KEEL_GUARD_TERMS`` or a git-ignored ``.guardterms``, because a guard list in
the repository would disclose exactly what it is meant to protect.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# ── Risk kinds ──────────────────────────────────────────────────────────────

#: A term supplied via $KEEL_GUARD_TERMS / .guardterms — site-specific.
GUARD_TERM = "guard-term"
#: Something shaped like a credential.
SECRET = "secret"
#: An email address.
EMAIL = "email"
#: A personal name, inferred from an addressing phrase ("ask Jane Doe").
PERSON = "person"
#: A host or URL that is not obviously public documentation.
INTERNAL_HOST = "internal-host"
#: A bare IP address.
IP_ADDRESS = "ip-address"

#: Ordered for display: most severe first.
RISK_ORDER = (GUARD_TERM, SECRET, EMAIL, PERSON, INTERNAL_HOST, IP_ADDRESS)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_URL_RE = re.compile(r"\bhttps?://([A-Za-z0-9.-]+)")

# "ask Jane Doe", "owned by Jane Doe", "contact Jane" — an addressing verb
# followed by capitalised words. Bare capitalised words are far too common in
# prose ("Use Docker Compose") to treat as names on their own.
_PERSON_RE = re.compile(
    r"\b(?:ask|contact|owner\s+is|owned\s+by|maintained\s+by|reach\s+out\s+to|"
    r"speak\s+to|ping|assigned\s+to|dm)\s+"
    r"(?!the\b|your\b|a\b|an\b|our\b|team\b|#)"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    re.IGNORECASE | re.MULTILINE,
)

_SECRET_RES = (
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(
        r"(secret|token|passwd|password|api[_-]?key)[\"' ]*[:=][\"' ]*[A-Za-z0-9/_+-]{20,}",
        re.IGNORECASE,
    ),
)

#: Values that look like credentials but are documentation placeholders. Mirrors
#: the guard script's PLACEHOLDER so `.env.example`-style text does not trip us.
_PLACEHOLDER_RE = re.compile(
    r"your[_-]?|[_-]here|<[a-z]|\$\{|xxx|changeme|placeholder|dummy|redacted|"
    r"example|todo|fixme|actual-key",
    re.IGNORECASE,
)

#: Hosts that are public documentation, not somebody's internal estate.
_PUBLIC_HOSTS = frozenset({
    "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
    "docs.python.org", "docs.docker.com", "kubernetes.io", "www.python.org",
    "developer.mozilla.org", "readthedocs.io", "pypi.org", "npmjs.com",
    "example.com", "localhost",
})


@dataclass(frozen=True)
class Risk:
    """One kind of identifier found in a candidate.

    Carries **no matched text**, by design. A review file naming what it found
    would relocate the disclosure rather than prevent it, so the reviewer gets
    the kind and a count and follows the citation to the source.
    """

    kind: str
    count: int = 1

    def describe(self) -> str:
        plural = "s" if self.count != 1 else ""
        return {
            GUARD_TERM: f"{self.count} site-specific term{plural}",
            SECRET: f"{self.count} credential-shaped string{plural}",
            EMAIL: f"{self.count} email address{'es' if self.count != 1 else ''}",
            PERSON: f"{self.count} personal name{plural}",
            INTERNAL_HOST: f"{self.count} non-public host{plural}",
            IP_ADDRESS: f"{self.count} IP address{'es' if self.count != 1 else ''}",
        }.get(self.kind, f"{self.count} {self.kind}")


@lru_cache(maxsize=1)
def guard_terms() -> tuple[str, ...]:
    """Site-specific terms, from ``$KEEL_GUARD_TERMS`` or a ``.guardterms`` file.

    Same resolution order as ``scripts/check-no-company-data.sh``. Never
    hardcoded: the list is the secret.
    """
    env = os.environ.get("KEEL_GUARD_TERMS", "").strip()
    if env:
        return tuple(t.strip().lower() for t in env.split(",") if t.strip())

    root = _repo_root()
    if root is None:
        return ()
    path = root / ".guardterms"
    if not path.is_file():
        return ()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    return tuple(
        line.strip().lower()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    )


def _repo_root() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = out.stdout.strip()
    return Path(top) if out.returncode == 0 and top else None


def scan(text: str) -> tuple[Risk, ...]:
    """Report every kind of identifier present in ``text``.

    An empty result means the text is safe to write to a git-visible review
    file. Anything else means the candidate is held.
    """
    if not text:
        return ()

    found: dict[str, int] = {}

    def add(kind: str, n: int = 1) -> None:
        if n:
            found[kind] = found.get(kind, 0) + n

    lowered = text.lower()
    add(GUARD_TERM, sum(
        1 for term in guard_terms()
        if term and re.search(rf"\b{re.escape(term)}\b", lowered)
    ))

    add(SECRET, sum(
        len([m for m in pattern.findall(text) if not _PLACEHOLDER_RE.search(str(m))])
        for pattern in _SECRET_RES
    ))
    add(EMAIL, len(_EMAIL_RE.findall(text)))
    add(PERSON, len(_PERSON_RE.findall(text)))
    add(IP_ADDRESS, len(_IP_RE.findall(text)))
    add(INTERNAL_HOST, sum(
        1 for host in _URL_RE.findall(text)
        if not _is_public_host(host)
    ))

    return tuple(
        Risk(kind, found[kind]) for kind in RISK_ORDER if found.get(kind)
    )


def _is_public_host(host: str) -> bool:
    """True for hosts that are public documentation rather than internal estate."""
    host = host.lower().strip(".")
    if host in _PUBLIC_HOSTS:
        return True
    # Any subdomain of a known-public registrable domain.
    return any(host.endswith(f".{public}") for public in _PUBLIC_HOSTS)


def is_safe(text: str) -> bool:
    """True when ``text`` may be written to a git-visible file."""
    return not scan(text)


__all__ = [
    "GUARD_TERM", "SECRET", "EMAIL", "PERSON", "INTERNAL_HOST", "IP_ADDRESS",
    "RISK_ORDER", "Risk", "guard_terms", "scan", "is_safe",
]
