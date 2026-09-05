"""One place that turns a reference into the content behind it.

Three answers to "fetch what this ref points at" had grown independently, and
none of them could see the others:

- :mod:`agentic_cli.context.resolve` walked an ``if okf:… elif domain:…``
  chain to build a session's context bundle. It traced, and it returned bodies
  but never versions.
- :mod:`agentic_cli.onboarding.sources` read Confluence pages and repository
  docs during extraction. It returned versions but traced nothing, so
  ``keel domain extract`` read from upstream without leaving a ledger row.
- ``stale_repo_entries`` re-read repository files a third time, for the single
  purpose of comparing a digest.

They are one operation — *ref in, current content and current version out* — so
they belong behind one interface. Fetchers are **registered against a scheme**,
not branched on: adding ``jira`` is a :func:`register_fetcher` call, in keeping
with the registry rule the engines and watcher triggers already follow.

Why this exists before the semantic differ rather than alongside it: the differ
asks exactly this question — *what does this source say now, versus what it said
when we drew an instruction from it* — and without a seam it would have grown a
fourth fetcher of its own.

**Not to be confused with** :mod:`agentic_cli.retrievers`, which registers named
search indexes (FAISS, FTS, KG) that an agent binds to and queries. A retriever
answers "what is relevant to this question" and returns many hits; a fetcher
here answers "what is at this address" and returns one document.

:func:`search` is the recording half of that other seam, and lives here because
both operations put text in front of an agent and both must reach the ledger —
not because a query is a ref. It does not pretend to be one: it takes a question
and a callable, never an address.

Five outcomes, because collapsing them loses the distinction the rest of the
platform is built on. ``fetch_confluence`` already carried the comment that a
temporarily unreachable source must not look like a source with nothing to
say — returning ``None`` for both made that impossible to honour. Now:

``RESOLVED``     we asked and got content.
``MISSING``      we asked; there is nothing at that ref.
``REFUSED``      we found content and declined to serve it (scaffold filler, a
                 path escaping its root). Not absence — a decision.
``UNAVAILABLE``  we could not ask. Unknown, never reported as empty.
``UNSUPPORTED``  no fetcher is registered for that scheme.

A fetch records one ledger row, here, once — with one deliberate exception:
:func:`current_version` and :func:`is_stale` do not, because a staleness check
reads bytes but serves none, and the drift pollers behind it run on every
dashboard page load. See the note on :func:`current_version`.

A fetcher that raises becomes ``UNAVAILABLE`` rather than an exception: the
callers are context assembly, a drift poll and a dashboard page, and none of
them should fail because one source is misconfigured.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

logger = logging.getLogger(__name__)

RESOLVED = "resolved"
MISSING = "missing"
REFUSED = "refused"
UNAVAILABLE = "unavailable"
UNSUPPORTED = "unsupported"

#: How each outcome lands in the KeelTrace ledger. ``UNAVAILABLE`` is the only
#: one that counts as an error, and it should: the session-level error tally is
#: meant to answer "how much of this run's context failed to load", and a source
#: we could not reach is precisely that. A refusal is not an error — we made it
#: on purpose — and neither is a ref that simply has nothing behind it.
_LEDGER_STATUS = {
    RESOLVED: "success",
    MISSING: "empty",
    REFUSED: "empty",
    UNSUPPORTED: "empty",
    UNAVAILABLE: "error",
}

#: Default ledger source family. Callers reading for a purpose other than
#: assembling agent context should name their own, so the eval feed and the
#: context-budget readout keep answering "what did Keel put in front of this
#: session" rather than "what did Keel read, ever".
CONTEXT_SOURCE = "context"
ONBOARDING_SOURCE = "onboarding"


@dataclass(frozen=True)
class Ref:
    """A parsed reference: scheme, address within that scheme, and version.

    Two spellings are accepted because two already exist in the codebase and
    both are load-bearing: ``domain://acme/setup.md`` is what a context bundle
    carries, and ``repo:acme/CONTRIBUTING.md@9f2c1a`` is what a
    :class:`~agentic_cli.onboarding.extract.Citation` serialises to. They are
    the same address written two ways.
    """

    scheme: str
    path: str
    version: str = ""
    raw: str = ""

    def __str__(self) -> str:
        return self.raw or (f"{self.scheme}:{self.path}"
                            + (f"@{self.version}" if self.version else ""))


def parse_ref(raw: str) -> Ref:
    """Parse either spelling. An unrecognisable ref parses to an empty scheme.

    A ref with no scheme is not an error here — it is a ref for a source Keel
    does not mediate, and recording that it was asked for is the whole point of
    :data:`UNSUPPORTED`.
    """
    text = (raw or "").strip()
    if not text:
        return Ref(scheme="", path="", raw=text)
    body, _, version = text.partition("@")
    scheme, sep, path = body.partition(":")
    if not sep:
        return Ref(scheme="", path=text, raw=text)
    return Ref(scheme=scheme.strip().lower(),
               path=path.lstrip("/"), version=version, raw=text)


@dataclass
class Fetched:
    """What one source said when we asked it, and when it last changed."""

    ref: str
    scheme: str
    status: str
    text: str = ""
    version: str = ""
    title: str = ""
    origin: str = ""          # where it came from, for display
    detail: str = ""          # why, when the status is not RESOLVED

    @property
    def resolved(self) -> bool:
        return self.status == RESOLVED

    @property
    def known(self) -> bool:
        """True when the source answered — including answering "nothing here".

        The negative case is the one that matters: an unknown source must never
        be scored, diffed or flagged absent, because we did not learn anything
        about it.
        """
        return self.status in (RESOLVED, MISSING, REFUSED)

    def to_dict(self) -> dict:
        return {
            "ref": self.ref, "scheme": self.scheme, "status": self.status,
            "version": self.version, "title": self.title,
            "bytes": len(self.text.encode("utf-8")),
            "origin": self.origin, "detail": self.detail,
        }


#: A fetcher takes a parsed ref and returns what its source said.
Fetcher = Callable[[Ref], Fetched]

_FETCHERS: dict[str, Fetcher] = {}


def register_fetcher(scheme: str, fetcher: Fetcher) -> None:
    """Register (or replace) the fetcher for one scheme. Idempotent."""
    _FETCHERS[scheme.strip().lower()] = fetcher


def schemes() -> list[str]:
    return sorted(_FETCHERS)


def fetch(raw_ref: str, *, source: str = CONTEXT_SOURCE,
          operation_prefix: str = "resolve", trace: bool = True) -> Fetched:
    """Resolve one ref through its registered fetcher, recording the read.

    ``source`` names the ledger family. It defaults to ``context`` because the
    dominant caller is context assembly, but extraction passes ``onboarding``:
    both reads deserve a row, and only one of them is context served to an
    agent. Conflating them would put every extraction read into the eval feed's
    idea of what a coding session was given.

    Never raises.
    """
    ref = parse_ref(raw_ref)
    fetcher = _FETCHERS.get(ref.scheme)

    if fetcher is None:
        result = Fetched(
            ref=str(ref), scheme=ref.scheme, status=UNSUPPORTED,
            detail=(f"No fetcher registered for scheme '{ref.scheme}'."
                    if ref.scheme else "Ref carries no scheme."))
    else:
        try:
            result = fetcher(ref)
        except Exception as exc:  # noqa: BLE001 - see module docstring
            logger.debug("fetcher %s failed on %s: %s", ref.scheme, raw_ref, exc)
            result = Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                             detail=f"{type(exc).__name__} while reading the source.")

    if trace:
        _record(result, source=source, operation_prefix=operation_prefix)
    return result


def fetch_many(refs: Iterable[str], *, source: str = CONTEXT_SOURCE,
               operation_prefix: str = "resolve") -> list[Fetched]:
    return [fetch(r, source=source, operation_prefix=operation_prefix)
            for r in refs if (r or "").strip()]


def _record(result: Fetched, *, source: str, operation_prefix: str) -> None:
    """One ledger row per fetch. Telemetry is never load-bearing.

    ``record_context_read`` guards itself, but the guard has to be here too:
    sizing the payload and importing the tracer both happen on this side of it,
    and a fetch that fails because the ledger did would invert the rule the
    ledger exists under.
    """
    try:
        from agentic_cli import tracing

        # An unsupported scheme records as ``external``: it is a source outside
        # anything Keel mediates, and the operation name has been that since the
        # sensor was added.
        family = result.scheme or "external"
        tracing.record_context_read(
            source=source,
            operation=f"{operation_prefix}/{family}",
            entity_id=result.ref,
            size_bytes=tracing.measure(result.text),
            status=_LEDGER_STATUS.get(result.status, "empty"),
            payload=result.text or None,
            extra={"outcome": result.status} if result.status != RESOLVED else None,
        )
    except Exception as exc:  # noqa: BLE001 - see docstring
        logger.debug("fetch of %s not recorded: %s", result.ref, exc)


def current_version(raw_ref: str, *, trace: bool = False,
                    source: str = CONTEXT_SOURCE) -> Optional[str]:
    """The version a source reports for a ref now, or None when unknown.

    Does not trace by default. A staleness check reads bytes but serves none —
    it is Keel auditing its own bookkeeping, not context put in front of an
    agent — and the drift detectors behind it run on every dashboard page load
    and every watcher poll. Recording those would bury the reads that answer
    "what was this session given" under an order of magnitude more rows that
    answer nothing.
    """
    result = fetch(raw_ref, source=source, operation_prefix="version", trace=trace)
    if not result.known or not result.version:
        return None
    return result.version


def is_stale(raw_ref: str, cited: str = "", *, trace: bool = False,
             source: str = CONTEXT_SOURCE) -> Optional[bool]:
    """Has the source moved past the version an instruction was drawn from?

    ``None`` means *unknown* — no cited version, an unreachable source, or a
    scheme whose source has no version to report. Unknown is never reported as
    fresh and never as stale: not knowing whether a claim still holds is a gap
    in our knowledge, not a verdict about it.

    This generalises the repo-only digest comparison that ``stale_repo_entries``
    open-coded. Every scheme with a version answers the same question here, so
    extending staleness to Confluence, or to a new source, no longer means
    writing the comparison again.
    """
    ref = parse_ref(raw_ref)
    cited = cited or ref.version
    if not cited:
        return None
    now = current_version(raw_ref, trace=trace, source=source)
    if now is None:
        return None
    return now != cited


# ── searching ───────────────────────────────────────────────────────────────

#: Ledger source family for search-shaped reads.
RETRIEVER_SOURCE = "retriever"


def search(retriever: str, operation: str, run: Callable[[], Any], *,
           query: str = "", source: str = RETRIEVER_SOURCE,
           domain: Optional[str] = None,
           text_of: Optional[Callable[[Any], str]] = None) -> Any:
    """Run one search and record it, returning whatever ``run`` returns.

    A *fetch* resolves an address to one document; a *search* answers a question
    with many hits. They are different operations — that is the fetcher/retriever
    distinction the glossary draws — so forcing a KG query through
    :func:`fetch` would have meant inventing an address for a question. What
    they share is that both put text in front of an agent and both must land in
    the ledger, which is what this provides: the recording half of the retriever
    seam, without pretending a query is a ref.

    Before this, the KG, LightRAG, Neo4j and Glean clients recorded nothing at
    all. A session answered entirely from the knowledge graph showed as having
    read nothing — the ledger's central claim, "this is what Keel put in front
    of the agent", was simply false for those paths.

    The query text is fingerprinted, never stored: a search string carries the
    same disclosure profile as tool arguments, which ``digest_args`` already
    refuses to keep. The *result* is counted in tokens and offered to the
    tier-two store, which is off unless an operator turns it on.

    An exception is recorded as an error row and then re-raised. A search that
    failed still consumed a round trip, and losing the row would make an
    unreliable source look like an unused one.

    ``text_of`` renders the result into the text an agent actually receives, for
    callers whose return value is not that text. A client returning parsed
    objects would otherwise be counted on their repr, which is neither what was
    sent to a model nor a stable number — it would move when a field was added.
    """
    from agentic_cli import tracing

    session_id = tracing.current_session_id()
    if domain is None:
        # Read on this thread, before any hop the callee may make — the same
        # reason the MCP client reads it here rather than at record time.
        domain = tracing.current_domain()
    started = time.perf_counter()

    def _record(status: str, result: Any) -> None:
        try:
            text = ""
            if result is not None:
                try:
                    text = (text_of(result) if text_of
                            else tracing.as_text(result))
                except Exception:  # noqa: BLE001 - a renderer must not break the read
                    text = tracing.as_text(result)
            tracing.record_context_read(
                source=source,
                operation=f"{retriever}/{operation}",
                session_id=session_id,
                domain=domain,
                entity_id=tracing.digest_args({"q": query})[:64] if query else "",
                size_bytes=tracing.measure(result),
                duration_ms=int((time.perf_counter() - started) * 1000),
                status=status,
                payload=text or None,
                extra={"hits": _hit_count(result)} if result is not None else None,
            )
        except Exception as exc:  # noqa: BLE001 - telemetry is never load-bearing
            logger.debug("search of %s not recorded: %s", retriever, exc)

    try:
        result = run()
    except Exception:
        _record("error", None)
        raise
    _record("success" if result else "empty", result)
    return result


def _hit_count(result: Any) -> int:
    """How many results came back, best-effort.

    Bytes say how much a search cost; hits say whether it found anything, and a
    retriever returning nothing repeatedly is a different problem from one
    returning too much. Zero for a shape we do not recognise — a wrong count
    would be worse than an absent one.
    """
    if isinstance(result, list):
        return len(result)
    if isinstance(result, dict):
        for key in ("results", "hits", "documents", "chunks", "data", "matches"):
            value = result.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


# ── Built-in fetchers ───────────────────────────────────────────────────────

def _domain_meta(slug: str):
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    return detect_domain_meta_repo(slug)


def _strip_frontmatter(text: str) -> str:
    """Drop the provenance/reviewed header — it is metadata, not context.

    Feeding it to a model spends tokens on bookkeeping and invites the model to
    quote our own stamps back as domain facts.
    """
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


def domain_fetcher(ref: Ref) -> Fetched:
    """``domain://<slug>/<file>`` — one finalized file from a meta-repo."""
    from agentic_cli.onboarding import provenance, sources

    slug, _, name = ref.path.partition("/")
    out = Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING)
    if not slug or not name:
        out.detail = "Expected domain://<slug>/<file>."
        return out

    meta = _domain_meta(slug)
    if meta is None:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail=f"No meta-repo found for domain '{slug}'.")

    # Resolve under .domain/ and refuse anything that escapes it: a ref is
    # caller-supplied, and "../../.ssh/id_rsa" is a context ref too.
    root = (meta / ".domain").resolve()
    try:
        path = (root / name).resolve()
        path.relative_to(root)
    except ValueError:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=REFUSED,
                       detail="Ref resolves outside the domain directory.")
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        out.detail = "No such file in .domain/."
        return out

    # Filler must never be served as context. `domain init` writes "will be
    # populated from the Knowledge Graph" when the KG query returns nothing, and
    # an agent handed that reads it as a statement about the domain. Refusing
    # here is the point of stamping provenance at all: a refused ref shows up as
    # a gap in the ledger and in the score, where a confident-sounding
    # placeholder would not.
    #
    # Only *filler* is refused, not merely-unattributed content. A pre-stamping
    # `.domain/` file reads as UNKNOWN provenance, and dropping those would
    # silently empty out every legacy domain — a worse failure than serving real
    # text whose origin we cannot name.
    if provenance.read(path).provenance == provenance.PLACEHOLDER:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=REFUSED,
                       title=name, origin=str(path),
                       detail="Scaffold placeholder — not real domain content.")

    text = _strip_frontmatter(body).strip()
    return Fetched(ref=str(ref), scheme=ref.scheme, status=RESOLVED,
                   text=text, version=sources.content_version(text),
                   title=name, origin=str(path))


def locate_bundle_dir(domain: str) -> Optional[Path]:
    """Find a domain's OKF bundle dir, preferring the generated export."""
    if not domain:
        return None
    root = Path.cwd()
    for candidate in (root / "knowledge-export" / domain,
                      root / "skills" / "domains" / domain / "knowledge"):
        if (candidate / "okf.schema.yaml").exists():
            return candidate
    return None


def okf_fetcher(ref: Ref) -> Fetched:
    """``okf://<domain>/<concept_id>`` — one concept from an OKF bundle."""
    domain, _, concept_id = ref.path.partition("/")
    if not domain or not concept_id:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail="Expected okf://<domain>/<concept_id>.")
    try:
        from agentic_cli.kg.okf.bundle import Bundle  # optional deps
    except Exception:  # noqa: BLE001
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail="OKF support is not installed.")

    bundle_dir = locate_bundle_dir(domain)
    if not bundle_dir:
        # No bundle on disk means we could not ask, not that the concept is
        # absent. An unexported domain and a domain missing one concept are
        # different problems and only one of them is the author's to fix.
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail=f"No OKF bundle exported for '{domain}'.")
    try:
        bundle = Bundle.load(bundle_dir)
    except Exception:  # noqa: BLE001
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail="OKF bundle could not be read.")

    for concept in bundle.concepts.values():
        if getattr(concept, "id", "") == concept_id:
            body = getattr(concept, "body", "") or ""
            return Fetched(
                ref=str(ref), scheme=ref.scheme, status=RESOLVED, text=body,
                version=str(getattr(concept, "version", "") or ""),
                title=getattr(concept, "title", "") or concept_id,
                origin=str(bundle_dir))
    return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                   origin=str(bundle_dir),
                   detail=f"Bundle has no concept '{concept_id}'.")


def repo_fetcher(ref: Ref) -> Fetched:
    """``repo:<slug>/<path>`` — a file in a repository's canonical clone."""
    from agentic_cli import persona_workspace as pw
    from agentic_cli.onboarding import sources

    slug, _, rel = ref.path.partition("/")
    if not slug or not rel:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail="Expected repo:<slug>/<path>.")
    root = pw.store_repo_path(slug)
    if not root.is_dir():
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail=f"Repository '{slug}' is not in the store.")
    try:
        path = (root / rel).resolve()
        path.relative_to(root.resolve())
    except ValueError:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=REFUSED,
                       detail="Ref resolves outside the repository.")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail="No such file in the repository.")

    # Truncate to the same bound extraction used, so a version computed here
    # compares against a version computed there. Digesting the whole file while
    # extraction digested the first 40k would report every long document stale
    # forever.
    body = text[:sources.MAX_BODY_CHARS]
    return Fetched(ref=str(ref), scheme=ref.scheme, status=RESOLVED, text=body,
                   version=sources.content_version(body),
                   title=path.name, origin=str(path))


def confluence_fetcher(ref: Ref) -> Fetched:
    """``confluence:<page_id>`` — one page through the Confluence MCP server."""
    from agentic_cli.kg.okf.enrichment.sources.confluence import _html_to_text
    from agentic_cli.mcp_tool_client import MCPToolError, confluence_get_page
    from agentic_cli.onboarding import sources

    page_id = ref.path
    if not page_id:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail="Expected confluence:<page_id>.")
    try:
        page = confluence_get_page(page_id, include_body=True)
    except MCPToolError as exc:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail=f"Confluence could not be reached ({exc}).")
    if not isinstance(page, dict):
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail="Confluence returned no page.")

    body = page.get("body_html") or page.get("body") or page.get("content") or ""
    if isinstance(body, dict):
        body = body.get("value", "") or body.get("storage", {}).get("value", "")
    return Fetched(
        ref=str(ref), scheme=ref.scheme, status=RESOLVED,
        text=_html_to_text(str(body))[:sources.MAX_BODY_CHARS],
        version=str(page.get("version") or ""),
        title=str(page.get("title") or ""), origin="confluence")


def governance_fetcher(ref: Ref) -> Fetched:
    """``governance://<domain>`` — the domain's governance preamble text."""
    from pathlib import Path

    from agentic_cli.onboarding import sources

    domain = ref.path.strip("/")
    if not domain:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail="Expected governance://<domain>.")
    root = Path.cwd()
    for candidate in (root / "skills" / "domains" / domain / "GOVERNANCE.md",
                      root / "skills" / "domains" / domain / "governance.md",
                      root / "knowledge-export" / domain / "GOVERNANCE.md"):
        try:
            if candidate.is_file():
                text = candidate.read_text(encoding="utf-8").strip()
                return Fetched(ref=str(ref), scheme=ref.scheme, status=RESOLVED,
                               text=text, version=sources.content_version(text),
                               title="GOVERNANCE.md", origin=str(candidate))
        except OSError:
            continue
    return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                   detail=f"No governance document for '{domain}'.")


for _scheme, _fetcher in (
    ("domain", domain_fetcher),
    ("okf", okf_fetcher),
    ("repo", repo_fetcher),
    ("confluence", confluence_fetcher),
    ("governance", governance_fetcher),
):
    register_fetcher(_scheme, _fetcher)


__all__ = [
    "RESOLVED", "MISSING", "REFUSED", "UNAVAILABLE", "UNSUPPORTED",
    "CONTEXT_SOURCE", "ONBOARDING_SOURCE", "Ref", "Fetched", "Fetcher",
    "parse_ref", "register_fetcher", "schemes", "fetch", "fetch_many",
    "current_version", "is_stale", "locate_bundle_dir",
    "RETRIEVER_SOURCE", "search",
]
