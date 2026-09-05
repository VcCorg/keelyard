"""What the recorded tokens cost, when someone has said what tokens cost.

Keel ships **no prices**. A rate card is loaded from configuration or the feature
stays off, and the reason is not squeamishness — it is that a wrong price is
worse than no price. Rates change; a number baked into a release keeps being
produced long after it stopped being true, and nothing about a confident dollar
figure invites the reader to check it. An operator supplying their own card
knows what they supplied.

That is also the vendor-neutral position the rest of the platform takes. Keel
does not bundle a tokenizer, does not commit guard terms, and does not hardcode
an engine; a price list for one vendor's models would be all three mistakes at
once.

``rates.example.yaml`` in this package is data, not a default. It carries an
``as_of`` date and its source, an operator copies it deliberately, and
:func:`load` warns once the card is older than :data:`STALE_AFTER_DAYS` — which
is the only real defence against the failure that matters here, a card that was
right when it was written and silently is not any more.

**Only generated work is priced.** Retrieval rows carry tokens and no cost,
because nobody bills for reading a file off disk. Context becomes money when a
model reads it, and that is the generation row — which is why the cost column is
blank on the retrieval meters rather than zero. The distinction is the useful
half of the report: a project can build a large context for nothing and then pay
for it repeatedly, or build a small one and never send it.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

#: Environment override for the rate card path.
ENV_RATE_CARD = "KEEL_RATE_CARD"

#: Where a rate card lives when the environment does not name one.
DEFAULT_REL = "rates.yaml"

#: A card older than this is reported as stale. Model prices have moved more
#: than once a quarter in practice, so a card nobody has looked at in six months
#: is a number to distrust rather than one to quote.
STALE_AFTER_DAYS = 180

#: Fallbacks when a model names no explicit cache rate. Published multipliers
#: for cache reads and writes, and deliberately only fallbacks: they do not hold
#: everywhere — a model can price cache reads well below a tenth of its input
#: rate — so an explicit per-model figure always wins.
DEFAULT_CACHE_READ_MULTIPLIER = 0.1
DEFAULT_CACHE_WRITE_MULTIPLIER = 1.25


@dataclass(frozen=True)
class ModelRate:
    """What one model charges, per million tokens."""

    model: str
    input_per_mtok: float = 0.0
    output_per_mtok: float = 0.0
    cache_read_per_mtok: Optional[float] = None
    cache_write_per_mtok: Optional[float] = None

    @property
    def cache_read(self) -> float:
        if self.cache_read_per_mtok is not None:
            return self.cache_read_per_mtok
        return self.input_per_mtok * DEFAULT_CACHE_READ_MULTIPLIER

    @property
    def cache_write(self) -> float:
        if self.cache_write_per_mtok is not None:
            return self.cache_write_per_mtok
        return self.input_per_mtok * DEFAULT_CACHE_WRITE_MULTIPLIER

    def cost(self, *, input_tokens: int = 0, output_tokens: int = 0,
             cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> float:
        """Dollars for one call's token counts."""
        return (
            input_tokens * self.input_per_mtok
            + output_tokens * self.output_per_mtok
            + cache_read_tokens * self.cache_read
            + cache_write_tokens * self.cache_write
        ) / 1_000_000.0


@dataclass
class RateCard:
    """Every rate an operator has supplied, and when they supplied it."""

    models: dict[str, ModelRate] = field(default_factory=dict)
    as_of: Optional[date] = None
    currency: str = "USD"
    source: str = ""
    path: Optional[Path] = None

    @property
    def configured(self) -> bool:
        return bool(self.models)

    @property
    def age_days(self) -> Optional[int]:
        if self.as_of is None:
            return None
        return (date.today() - self.as_of).days

    @property
    def stale(self) -> bool:
        """True when the card is old enough to distrust.

        A card with no ``as_of`` counts as stale. Undated is not fresh: it is a
        card nobody can reason about, and the whole point of the field is that
        someone has to look at the number and vouch for a date.
        """
        age = self.age_days
        return age is None or age > STALE_AFTER_DAYS

    def rate_for(self, model: str) -> Optional[ModelRate]:
        """The rate for a model name, tolerating how providers name things.

        ``get_name`` returns whatever the provider calls itself — a bare id, a
        ``vendor/model`` pair, a deployment alias, sometimes a date suffix. An
        exact-match-only lookup would silently price almost nothing, and a
        silently unpriced call looks identical to a free one.

        Matched most specific first: exact, then the last path segment, then the
        longest configured id the name starts with. Longest-first matters — with
        both ``claude-opus-5`` and ``claude-opus`` configured, a call on
        ``claude-opus-5`` must not be priced by the shorter entry.
        """
        if not model:
            return None
        name = model.strip()
        if name in self.models:
            return self.models[name]
        tail = name.rsplit("/", 1)[-1]
        if tail in self.models:
            return self.models[tail]
        candidates = [key for key in self.models
                      if tail.startswith(key) or name.startswith(key)]
        if not candidates:
            return None
        return self.models[max(candidates, key=len)]

    def to_dict(self) -> dict:
        return {
            "configured": self.configured,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "age_days": self.age_days,
            "stale": self.stale,
            "currency": self.currency,
            "source": self.source,
            "path": str(self.path) if self.path else None,
            "models": sorted(self.models),
        }


def card_path() -> Path:
    """Where the rate card is read from."""
    override = os.environ.get(ENV_RATE_CARD)
    if override:
        return Path(override).expanduser()
    from agentic_cli.tracker import DB_DIR

    return Path(DB_DIR) / DEFAULT_REL


def example_path() -> Path:
    """The dated example shipped alongside this module."""
    return Path(__file__).parent / "rates.example.yaml"


def load(path: Optional[Path] = None) -> RateCard:
    """Read the rate card, or an empty one when none is configured.

    An empty card is the normal state, not an error: costing is off until
    somebody says what things cost. Every failure — a missing file, unreadable
    YAML, a malformed entry — yields an empty card rather than a partial one,
    because a card that silently dropped the model you care about prices that
    model at nothing.
    """
    target = Path(path) if path else card_path()
    if not target.is_file():
        return RateCard()
    try:
        import yaml

        data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("rate card unreadable at %s: %s", target, exc)
        return RateCard()
    if not isinstance(data, dict):
        return RateCard()

    models: dict[str, ModelRate] = {}
    for name, entry in (data.get("models") or {}).items():
        if not isinstance(entry, dict):
            continue
        try:
            models[str(name)] = ModelRate(
                model=str(name),
                input_per_mtok=float(entry.get("input_per_mtok") or 0.0),
                output_per_mtok=float(entry.get("output_per_mtok") or 0.0),
                cache_read_per_mtok=(
                    float(entry["cache_read_per_mtok"])
                    if entry.get("cache_read_per_mtok") is not None else None),
                cache_write_per_mtok=(
                    float(entry["cache_write_per_mtok"])
                    if entry.get("cache_write_per_mtok") is not None else None),
            )
        except (TypeError, ValueError):
            # One bad entry does not invalidate the card, but it must not be
            # priced at zero either — leaving it out means it reports unpriced.
            logger.debug("skipping malformed rate for %s in %s", name, target)
            continue

    return RateCard(
        models=models,
        as_of=_as_date(data.get("as_of")),
        currency=str(data.get("currency") or "USD"),
        source=str(data.get("source") or ""),
        path=target,
    )


def _as_date(value) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@dataclass
class Priced:
    """A cost, and how much of the work it actually covers."""

    cost: float = 0.0
    priced_calls: int = 0
    unpriced_calls: int = 0
    unpriced_models: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.unpriced_calls == 0

    @property
    def partial(self) -> bool:
        return bool(self.priced_calls and self.unpriced_calls)

    def to_dict(self) -> dict:
        return {"cost": round(self.cost, 4), "priced_calls": self.priced_calls,
                "unpriced_calls": self.unpriced_calls,
                "unpriced_models": list(self.unpriced_models),
                "complete": self.complete}


def price(rows: list[dict], card: Optional[RateCard] = None) -> Priced:
    """Cost a set of generation rows against a rate card.

    ``rows`` carry ``model``, ``calls`` and the token breakdown. A model the
    card does not name is counted as unpriced rather than costed at zero: a
    total that silently omits a model reads as a cheaper project, which is the
    error nobody goes looking for.
    """
    card = card if card is not None else load()
    out = Priced()
    unpriced: set[str] = set()
    for row in rows:
        model = str(row.get("model") or "")
        calls = int(row.get("calls") or 0)
        rate = card.rate_for(model)
        if rate is None:
            out.unpriced_calls += calls
            if model:
                unpriced.add(model)
            continue
        out.priced_calls += calls
        out.cost += rate.cost(
            input_tokens=int(row.get("input_tokens") or 0),
            output_tokens=int(row.get("output_tokens") or 0),
            cache_read_tokens=int(row.get("cache_read_tokens") or 0),
            cache_write_tokens=int(row.get("cache_write_tokens") or 0),
        )
    out.unpriced_models = tuple(sorted(unpriced))
    return out


def money(amount: float, currency: str = "USD") -> str:
    """Format a cost without implying more precision than it has."""
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency.upper(), "")
    if amount and amount < 0.01:
        return f"{symbol}{amount:.4f}"
    return f"{symbol}{amount:,.2f}"


__all__ = ["ENV_RATE_CARD", "STALE_AFTER_DAYS", "ModelRate", "RateCard",
           "Priced", "card_path", "example_path", "load", "price", "money"]
