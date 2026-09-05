"""How long is this, in the unit the model actually charges for?

Bytes were the ledger's only size unit, and bytes are the wrong question. A
model's window and its bill are both denominated in tokens, and every model
tokenizes differently — so "how much context did this project use" cannot be
answered in bytes without quietly comparing two different things.

The whole design is one rule: **a count always carries how it was reached.**

``MEASURED``   a real tokenizer for that model ran over the text.
``ESTIMATED``  no tokenizer was available, so a documented ratio was applied.

Nothing here ever returns a bare number. A cost or budget readout built on an
estimate presented as a measurement is worse than no readout: it is a figure
someone puts in a slide, and there is no way to tell afterwards which rows were
real. Callers that must not mix the two can filter on the basis.

**Why an estimate is still worth recording.** The dominant use is comparing one
project against another, and a systematic bias cancels between them: if the
ratio runs 12% low it runs 12% low on both, and "this competition cost twice
what the other did" survives intact. What an estimate cannot support is a
statement about money owed, which is why the basis travels with it rather than
being noted once in a docstring nobody reads at the call site.

No tokenizer is bundled. ``tiktoken`` is used when the environment already has
it, because pulling a dependency into the desktop app's redistributed tree for
a telemetry nicety is the wrong trade — see NOTICE.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

MEASURED = "measured"
ESTIMATED = "estimated"

#: Characters per token, for the estimate path.
#:
#: Four is the widely-published rule of thumb for English prose in
#: byte-pair-encoded vocabularies, and it is deliberately *not* tuned per corpus
#: here. A ratio fitted to this repository's markdown would be more accurate on
#: this repository and silently wrong on a domain full of SQL, YAML or Japanese
#: — and being wrong in an unknown direction is worse than being wrong by a
#: known constant, because only one of the two can be corrected later.
CHARS_PER_TOKEN = 4.0

#: Model-name fragments that map to a tokenizer we can actually run. Matched as
#: substrings because callers pass whatever the engine reported, which may carry
#: a date suffix, a region prefix, or a deployment alias.
_TIKTOKEN_FAMILIES = ("gpt-", "o1", "o3", "text-embedding-")

_WORD = re.compile(r"\S+")


@dataclass(frozen=True)
class Count:
    """A token count and the provenance of the number."""

    tokens: int
    basis: str
    model: str = ""

    @property
    def measured(self) -> bool:
        return self.basis == MEASURED

    def to_dict(self) -> dict:
        return {"tokens": self.tokens, "token_basis": self.basis}


def estimate(text: str) -> int:
    """Token estimate from length alone, with a floor at the word count.

    Characters-per-token underestimates text made of many short tokens — a
    bulleted runbook, a table, a list of flags — where almost every whitespace
    run is its own token. Taking the larger of the two keeps the estimate from
    collapsing on exactly the shape onboarding documents tend to have.
    """
    if not text:
        return 0
    by_chars = int(len(text) / CHARS_PER_TOKEN)
    by_words = len(_WORD.findall(text))
    return max(by_chars, by_words)


def _tiktoken_count(text: str, model: str) -> Optional[int]:
    """Real count via tiktoken, or None when it cannot serve this model."""
    if not any(fragment in model.lower() for fragment in _TIKTOKEN_FAMILIES):
        return None
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except Exception:  # noqa: BLE001 - unknown model name, not a failure
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as exc:  # noqa: BLE001 - counting must never break a read
        logger.debug("tiktoken unavailable for %s: %s", model, exc)
        return None


def count(text: str, model: str = "") -> Count:
    """Count the tokens in ``text``, saying how the number was reached.

    Never raises and never returns a bare integer. A model we have no tokenizer
    for — which today is most of them, since no vendor tokenizer is bundled —
    falls back to the estimate and says so.
    """
    if not text:
        return Count(tokens=0, basis=MEASURED, model=model)
    if model:
        exact = _tiktoken_count(text, model)
        if exact is not None:
            return Count(tokens=exact, basis=MEASURED, model=model)
    return Count(tokens=estimate(text), basis=ESTIMATED, model=model)


def summarise(basis_counts: dict[str, int]) -> str:
    """One phrase describing a mixed set of bases, for a report footer.

    A total drawn from both measured and estimated rows is neither, and saying
    so in the footer is what stops the number being quoted as a bill.
    """
    measured = basis_counts.get(MEASURED, 0)
    estimated = basis_counts.get(ESTIMATED, 0)
    if measured and estimated:
        return (f"{measured} measured, {estimated} estimated — the total is "
                f"part estimate, not a bill")
    if estimated:
        return f"all {estimated} estimated at ~{CHARS_PER_TOKEN:.0f} chars/token"
    if measured:
        return f"all {measured} measured"
    return "nothing counted"


__all__ = ["MEASURED", "ESTIMATED", "CHARS_PER_TOKEN", "Count", "count",
           "estimate", "summarise"]
