"""Hugging Face and Kaggle — credentials by reference, and refs through the seam.

Two integrations that behave differently from the ones already here, in a way
worth stating rather than smoothing over.

**Credentials are referenced, never copied.** ``keel init anthropic`` stores the
API key, and that is right there: Keel is the only consumer, so the key has one
home. Kaggle and Hugging Face are not like that — both ship official tooling
that already owns a credential file (``~/.kaggle/kaggle.json``,
``~/.cache/huggingface/token``) which the user's own scripts and CLIs read.
Copying the secret into Keel's config would create a second place to rotate, a
second place to leak, and a silent divergence the first time someone rotates one
and not the other. So these commands *detect* a credential and record where it
came from. The value is never read, and `configured` here means "the official
tooling has one", which is the fact that actually predicts whether a fetch works.

**Both SDKs are optional.** The desktop app redistributes its dependency tree and
their licenses bind the artifacts (see NOTICE), so neither `kaggle` nor
`huggingface_hub` is a core dependency. Without them a fetch returns
``UNAVAILABLE`` — *we could not ask* — which is exactly the distinction the
retrieval seam exists to keep, and never ``MISSING``, which would say the model
or competition does not exist.

**What Kaggle's API does not give you.** It exposes competition *metadata* —
title, deadline, evaluation metric, category — and file listings. It does not
expose the competition description, the rules, or the data dictionary as text.
Those are the documents a domain actually wants, and they arrive the way every
other external document does: tracked with ``domain add-docs``. Pretending the
API returns them would produce a fetcher that silently yields metadata where a
caller expected rules.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

KAGGLE = "kaggle"
HUGGINGFACE = "huggingface"

#: Ref kinds each hub serves, so an unknown one fails loudly rather than being
#: guessed into the wrong API call.
HF_KINDS = ("model", "dataset", "space")
KAGGLE_KINDS = ("competition", "dataset")


@dataclass(frozen=True)
class Credential:
    """Where a hub's credential lives — never what it is."""

    hub: str
    available: bool = False
    source: str = ""
    account: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return {"hub": self.hub, "available": self.available,
                "source": self.source, "account": self.account,
                "detail": self.detail}


def kaggle_credential() -> Credential:
    """Find Kaggle's credential without reading the key.

    Order matches the official client's own: environment first, then
    ``$KAGGLE_CONFIG_DIR`` or ``~/.kaggle/kaggle.json``. The username is read
    because it is an identifier rather than a secret and naming the account is
    what makes "configured" verifiable; the key is not touched.
    """
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return Credential(hub=KAGGLE, available=True, source="environment",
                          account=os.environ["KAGGLE_USERNAME"],
                          detail="KAGGLE_USERNAME / KAGGLE_KEY")

    config_dir = os.environ.get("KAGGLE_CONFIG_DIR") or str(Path.home() / ".kaggle")
    path = Path(config_dir).expanduser() / "kaggle.json"
    if path.is_file():
        account = ""
        try:
            import json

            # Only the username. The key sits in this same object and is
            # deliberately not bound to a name here.
            account = str(json.loads(path.read_text(encoding="utf-8"))
                          .get("username") or "")
        except Exception as exc:  # noqa: BLE001 - unreadable is still present
            logger.debug("kaggle.json unreadable: %s", exc)
        return Credential(hub=KAGGLE, available=True, source=str(path),
                          account=account, detail="kaggle.json")

    return Credential(hub=KAGGLE, detail="no KAGGLE_USERNAME/KAGGLE_KEY and no "
                                         "kaggle.json")


def huggingface_credential() -> Credential:
    """Find the Hugging Face token's location without reading it."""
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        if os.environ.get(name):
            return Credential(hub=HUGGINGFACE, available=True,
                              source="environment", detail=name)

    home = os.environ.get("HF_HOME") or str(Path.home() / ".cache" / "huggingface")
    path = Path(home).expanduser() / "token"
    if path.is_file():
        return Credential(hub=HUGGINGFACE, available=True, source=str(path),
                          detail="huggingface-cli login")

    return Credential(hub=HUGGINGFACE,
                      detail="no HF_TOKEN and no cached login token")


def sdk_available(hub: str) -> bool:
    """Whether the hub's official client is importable."""
    module = {KAGGLE: "kaggle", HUGGINGFACE: "huggingface_hub"}.get(hub, "")
    if not module:
        return False
    try:
        __import__(module)
        return True
    except Exception:  # noqa: BLE001 - not installed, or broken; same answer
        return False


# ── fetchers ────────────────────────────────────────────────────────────────

def fetch_huggingface(ref):
    """``hf://{model|dataset|space}/<org>/<name>`` — the hub card and its sha.

    The card is the useful text: a model card states intended use and known
    limitations, a dataset card states provenance and licence. The commit sha
    is the version, which makes a card drift-checkable exactly like a repo file.
    """
    from agentic_cli.retrieval import MISSING, RESOLVED, UNAVAILABLE, Fetched

    kind, _, repo_id = ref.path.partition("/")
    if kind not in HF_KINDS or not repo_id:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail=f"Expected hf://<{'|'.join(HF_KINDS)}>/<org>/<name>.")
    if not sdk_available(HUGGINGFACE):
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail="huggingface_hub is not installed "
                              "(pip install 'agentic-cli[hubs]').")

    try:
        from huggingface_hub import DatasetCard, HfApi, ModelCard

        api = HfApi()
        if kind == "dataset":
            info = api.dataset_info(repo_id)
            text = DatasetCard.load(repo_id).text
        elif kind == "space":
            info = api.space_info(repo_id)
            text = ""
        else:
            info = api.model_info(repo_id)
            text = ModelCard.load(repo_id).text
    except Exception as exc:  # noqa: BLE001
        # Not MISSING: a network failure, a private repo and a rate limit are
        # all "we could not ask", and only a definite answer may say the thing
        # is not there.
        logger.debug("hugging face fetch failed for %s: %s", ref, exc)
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail=f"{type(exc).__name__} asking the hub.")

    return Fetched(ref=str(ref), scheme=ref.scheme, status=RESOLVED,
                   text=text or "", version=str(getattr(info, "sha", "") or ""),
                   title=repo_id, origin=f"huggingface/{kind}")


def fetch_kaggle(ref):
    """``kaggle://{competition|dataset}/<slug>`` — what the API actually exposes.

    Metadata, not prose. Kaggle's API does not serve a competition's description,
    rules or data dictionary, so this returns the fields it does serve and says
    so; the documents themselves are tracked with ``domain add-docs`` like any
    other external source. A fetcher that quietly returned metadata where the
    caller wanted rules would be worse than one that declines.
    """
    from agentic_cli.retrieval import MISSING, RESOLVED, UNAVAILABLE, Fetched

    kind, _, slug = ref.path.partition("/")
    if kind not in KAGGLE_KINDS or not slug:
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail=f"Expected kaggle://<{'|'.join(KAGGLE_KINDS)}>/<slug>.")
    if not sdk_available(KAGGLE):
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail="kaggle is not installed "
                              "(pip install 'agentic-cli[hubs]').")
    if not kaggle_credential().available:
        # The kaggle client raises on import when unauthenticated, so this is
        # checked before touching it.
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail="No Kaggle credential found — `keel init kaggle`.")

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        found = (api.competitions_list(search=slug) if kind == "competition"
                 else api.dataset_list(search=slug))
        match = _first_matching(found, slug)
    except Exception as exc:  # noqa: BLE001
        logger.debug("kaggle fetch failed for %s: %s", ref, exc)
        return Fetched(ref=str(ref), scheme=ref.scheme, status=UNAVAILABLE,
                       detail=f"{type(exc).__name__} asking Kaggle.")

    if match is None:
        # A definite answer this time: Kaggle replied and had nothing matching.
        return Fetched(ref=str(ref), scheme=ref.scheme, status=MISSING,
                       detail=f"Kaggle has no {kind} matching '{slug}'.")

    return Fetched(ref=str(ref), scheme=ref.scheme, status=RESOLVED,
                   text=_describe(match), version=str(getattr(match, "ref", slug)),
                   title=slug, origin=f"kaggle/{kind}",
                   detail="Metadata only — Kaggle's API does not serve rules or "
                          "the data dictionary; track those with `domain add-docs`.")


def _first_matching(found, slug: str):
    """The entry whose ref matches the slug, or None. Search is fuzzy; this is not."""
    for item in found or []:
        ref = str(getattr(item, "ref", "") or "")
        if ref == slug or ref.rsplit("/", 1)[-1] == slug.rsplit("/", 1)[-1]:
            return item
    return None


def _describe(item) -> str:
    """The fields worth putting in front of an agent, as plain text."""
    fields = ("title", "subtitle", "description", "evaluationMetric",
              "category", "deadline", "licenseName", "totalBytes")
    lines = []
    for field in fields:
        value = getattr(item, field, None)
        if value not in (None, "", 0):
            lines.append(f"{field}: {value}")
    return "\n".join(lines)


__all__ = ["KAGGLE", "HUGGINGFACE", "HF_KINDS", "KAGGLE_KINDS", "Credential",
           "kaggle_credential", "huggingface_credential", "sdk_available",
           "fetch_huggingface", "fetch_kaggle"]
