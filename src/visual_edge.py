"""Visual Edge foundation.

This module deliberately separates *image availability / review priority* from
claims about what the pixels contain. FlipFynd v0.9.0 can ingest and surface
listing images, and can use image metadata as weak evidence, but it must never
invent a parallel, serial number, autograph, relic or rookie marker merely
because an image exists.
"""
from __future__ import annotations

import re
from typing import Iterable

_VISUAL_TERMS = {
    "auto": ("auto", "autograph", "signerad", "signature"),
    "patch": ("patch", "relic", "jersey", "memorabilia", "material"),
    "rookie": ("rookie", " rc ", "young guns", "future watch", "rated rookie"),
    "numbered": ("numbered", "numrerad", "serial", "/10", "/25", "/50", "/99", "/100", "/199", "/249"),
    "parallel": ("refractor", "outburst", "high gloss", "exclusive", "clear cut", "prizm", "sapphire", "mojo", "shimmer", "pulsar", "x-fractor", "atomic", "pmg"),
}


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _terms(text: str) -> set[str]:
    padded = f" {text} "
    found: set[str] = set()
    for label, variants in _VISUAL_TERMS.items():
        if any(v in padded for v in variants):
            found.add(label)
    return found


def build_visual_edge(item: dict, *, listing_quality_score: float = 50, hidden_find_score: float = 0,
                      market_edge_score: float = 0, identity_confidence_score: float = 0,
                      knowledge_signals: Iterable[dict] | None = None) -> dict:
    """Return image-review priority without making pixel-level claims.

    `image_alt` / image metadata is only weak listing evidence. The returned
    structure contains no value/profit/max-bid fields by design.
    """
    urls = [str(x) for x in (item.get("image_urls") or []) if x]
    alts = [_norm(x) for x in (item.get("image_alts") or []) if x]
    title = _norm(item.get("titel"))
    raw = _norm(item.get("raw_text"))
    alt_text = " ".join(alts)

    title_terms = _terms(title)
    metadata_terms = _terms(alt_text)
    extra_metadata_terms = sorted(metadata_terms - title_terms)

    score = 0.0
    reasons: list[str] = []
    if urls:
        score += 24
        reasons.append(f"{len(urls)} annonsbild(er) tillgängliga för kontroll")
    else:
        return {
            "score": 0,
            "label": "Ingen bilddata",
            "reasons": ["Crawlern har inte fångat någon annonsbild"],
            "image_count": 0,
            "image_urls": [],
            "metadata_only": True,
            "requires_visual_verification": False,
            "metadata_terms": [],
        }

    if float(listing_quality_score or 0) < 55:
        score += 18
        reasons.append("svag annonskvalitet gör bilden extra viktig")
    if float(hidden_find_score or 0) >= 55:
        score += 16
        reasons.append("annonsen är redan markerad som möjlig dold kandidat")
    if float(market_edge_score or 0) >= 55:
        score += 14
        reasons.append("Edge Engine ser en möjlig informationsfördel")
    if float(identity_confidence_score or 0) < 70:
        score += 12
        reasons.append("kortidentiteten är inte tillräckligt säker från texten")
    if knowledge_signals:
        score += min(12, 4 * len(list(knowledge_signals)))
        reasons.append("kortstrukturen innehåller chase-/raritetssignaler som bör verifieras visuellt")
    if extra_metadata_terms:
        score += min(16, 5 * len(extra_metadata_terms))
        reasons.append("bildmetadata innehåller kortdetaljer som rubriken saknar: " + ", ".join(extra_metadata_terms[:3]))

    # Raw listing text may already contain details missing in title; images are a
    # natural next verification source but do not prove the details by themselves.
    if _terms(raw) - title_terms:
        score += 8
        reasons.append("annonsinformationen antyder mer än rubriken – kontrollera bilden")

    score = round(max(0, min(100, score)), 1)
    if score >= 75:
        label = "Mycket hög bildprioritet"
    elif score >= 55:
        label = "Hög bildprioritet"
    elif score >= 35:
        label = "Bildkontroll värd att göra"
    else:
        label = "Låg bildprioritet"

    return {
        "score": score,
        "label": label,
        "reasons": reasons[:5],
        "image_count": len(urls),
        "image_urls": urls[:6],
        "metadata_only": True,
        "requires_visual_verification": score >= 35,
        "metadata_terms": extra_metadata_terms,
    }
