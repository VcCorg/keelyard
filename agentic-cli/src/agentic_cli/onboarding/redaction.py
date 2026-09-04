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


# ── masking ─────────────────────────────────────────────────────────────────
#
# A second action for the same detection. Onboarding *holds* a risky candidate,
# because a held instruction costs a reviewer one click. A retrieval payload
# cannot be held the same way: dropping it means no eval score at all, so the
# text is kept with identifying spans replaced.
#
# Masking must be **span-preserving and semantically neutral**. Deleting "the
# SLA is 100ms" would make an agent's correct claim about 100ms score as
# unfaithful to the stored context, so a marker takes the span's place rather
# than the span being removed. Every metric computed over a masked payload is
# computed over something the agent did not literally see, which is why
# :class:`MaskResult` reports what it changed — a caller that does not record
# that is producing scores nobody can later account for.

#: Replaced with a typed marker. Losing the exact value costs nothing a metric
#: depends on: no claim worth scoring rests on which address was quoted.
MASKABLE = (SECRET, EMAIL, PERSON, INTERNAL_HOST, IP_ADDRESS, GUARD_TERM)

#: Marker written in place of a masked span.
_MARKERS = {
    GUARD_TERM: "<term>",
    SECRET: "<secret>",
    EMAIL: "<email>",
    PERSON: "<person>",
    INTERNAL_HOST: "<host>",
    IP_ADDRESS: "<ip>",
}


@dataclass(frozen=True)
class MaskResult:
    """Masked text, and an account of what was changed."""

    text: str
    masked: tuple[str, ...] = ()

    @property
    def lossy(self) -> bool:
        """True when the stored text is not what the agent saw."""
        return bool(self.masked)


def mask(text: str) -> MaskResult:
    """Replace identifying spans with typed markers, keeping everything else.

    Applied in a fixed order, most specific first: a credential inside a URL
    should read as ``<secret>`` rather than being half-consumed by the host
    pattern.
    """
    if not text:
        return MaskResult(text=text or "")

    masked: list[str] = []

    def note(kind: str) -> str:
        if kind not in masked:
            masked.append(kind)
        return _MARKERS[kind]

    out = text
    for pattern in _SECRET_RES:
        out = pattern.sub(
            lambda m: m.group(0) if _PLACEHOLDER_RE.search(m.group(0)) else note(SECRET),
            out,
        )

    for term in guard_terms():
        if term:
            out = re.sub(rf"\b{re.escape(term)}\b", lambda m: note(GUARD_TERM),
                         out, flags=re.IGNORECASE)

    out = _EMAIL_RE.sub(lambda m: note(EMAIL), out)
    # Keep the addressing verb, replace only the name it points at.
    out = _PERSON_RE.sub(lambda m: m.group(0).replace(m.group(1), note(PERSON)), out)
    out = _IP_RE.sub(lambda m: note(IP_ADDRESS), out)
    out = _URL_RE.sub(
        lambda m: m.group(0) if _is_public_host(m.group(1))
        else m.group(0).replace(m.group(1), note(INTERNAL_HOST)),
        out,
    )

    return MaskResult(text=out, masked=tuple(masked))


__all__ = [
    "GUARD_TERM", "SECRET", "EMAIL", "PERSON", "INTERNAL_HOST", "IP_ADDRESS",
    "RISK_ORDER", "MASKABLE", "Risk", "MaskResult", "guard_terms", "scan",
    "is_safe", "mask",
]
