"""Research-only identity recovery from marketplace titles.

This module deliberately improves recall only for comp *research*. Recovered
fields are never decision-grade identity and must not unlock valuation, exact
SOLD classification, max price or BUY decisions by themselves.
"""
from __future__ import annotations

import re
from typing import Any

from src.card_parser import (
    extract_card_number,
    extract_player_name,
    extract_season,
    extract_set_name,
    normalize_text,
    CARD_STOPWORDS,
)


def _txt(v: Any) -> str:
    return " ".join(str(v or "").strip().split())



_RESEARCH_PLAYER_NOISE = {
    "pris", "price", "kop", "köp", "nu", "sluttid", "slut", "avslutad", "auction",
    "new", "york", "los", "angeles", "washington", "capitals", "rangers", "kings",
    "edmonton", "oilers", "pittsburgh", "penguins", "toronto", "maple", "leafs",
    "canadiens", "montreal", "chicago", "blackhawks", "boston", "bruins",
    "vancouver", "canucks", "detroit", "wings", "colorado", "avalanche",
    "arsenal", "chelsea", "liverpool", "barcelona", "madrid", "united", "city",
    "fc", "cf", "afc", "nhl", "ucl", "uefa", "rookie", "rc", "insert",
    "uncommon", "common", "rare", "parallel", "silver", "script", "green",
    "red", "blue", "gold", "black", "white", "purple", "orange", "pink",
}


def _research_player_candidate(title: str, *, set_name: str | None, season: str | None, card_number: str | None) -> str | None:
    """Recover a two-token player candidate from a structured marketplace title.

    This is deliberately research-only. It prefers the two lexical tokens immediately
    after an explicit checklist number because that is a common Tradera/eBay title
    convention. If that fails, it tries the title prefix before the season/set.
    Team names, colours, listing boilerplate and product words are rejected.
    """
    raw = str(title or "")
    if not raw.strip():
        return None

    def clean_pair(segment: str) -> str | None:
        toks = re.findall(r"[A-Za-zÅÄÖåäöÀ-ÿ'’-]+", segment)
        kept=[]
        noise = set(CARD_STOPWORDS) | _RESEARCH_PLAYER_NOISE
        for tok in toks:
            folded = normalize_text(tok)
            if not folded or folded in noise or len(folded) <= 1:
                continue
            kept.append(tok.strip("-'’"))
            if len(kept) == 2:
                break
        if len(kept) != 2:
            return None
        # Avoid product/variant leftovers that slipped through token normalization.
        if any(normalize_text(x) in noise for x in kept):
            return None
        return " ".join(x[:1].upper()+x[1:] for x in kept)

    # Strongest research pattern: checklist number followed by player name.
    if card_number:
        cn = re.escape(str(card_number))
        patterns = [
            rf"(?:#|card\s*#?|kort\s*#?|no\.?\s*|nr\.?\s*){cn}\b(?P<tail>.+)$",
            rf"(?<![A-Za-z0-9]){cn}(?![A-Za-z0-9/])(?P<tail>.+)$",
        ]
        for pat in patterns:
            m=re.search(pat, raw, flags=re.I)
            if m:
                cand=clean_pair(m.group('tail'))
                if cand:
                    return cand

    # Player-first titles are also common. Limit the prefix before a recognized
    # season or set; this avoids pulling team/description words from the tail.
    cut=len(raw)
    if season:
        sm=re.search(r"\b(?:19|20)\d{2}\s*[-/]\s*(?:(?:19|20)?\d{2})\b", raw)
        if sm:
            cut=min(cut, sm.start())
    if set_name:
        # Match a forgiving tokenized version of the normalized set display name.
        parts=[re.escape(x) for x in normalize_text(set_name).split() if x]
        if parts:
            sm=re.search(r"\b"+r"[\s'’-]+".join(parts)+r"\b", raw, flags=re.I)
            if sm:
                cut=min(cut, sm.start())
    prefix=raw[:cut]
    cand=clean_pair(prefix)
    return cand


_RESEARCH_SET_MAKERS = {
    "topps", "panini", "upper", "deck", "ud", "fleer", "skybox", "pinnacle",
    "pacific", "score", "donruss", "bowman", "parkhurst", "opc", "o-pee-chee",
    "leaf", "sage", "press", "pass", "playoff", "in", "the", "game",
}

_RESEARCH_SET_NOISE = {
    "hockey", "football", "soccer", "card", "cards", "trading", "samlarbild",
    "rookie", "rc", "insert", "parallel", "rare", "common", "uncommon",
    "silver", "gold", "green", "red", "blue", "black", "white", "purple",
    "orange", "pink", "auto", "autograph", "signature", "script", "patch", "jersey",
    "pris", "price", "auction", "sluttid", "slut", "köp", "kop", "nu",
}


def _research_set_candidate(title: str, *, season: str | None, card_number: str | None) -> str | None:
    """Recover an unknown product/set span for research-only searches.

    The strongest marketplace pattern is ``season + product + card number``.
    We only accept a recovered span when it contains a recognizable manufacturer
    or card-brand anchor. This intentionally trades recall for safety.
    """
    raw = str(title or "")
    if not raw.strip() or not (season and card_number):
        return None

    # Locate season in common full/short forms.
    season_match = re.search(r"\b(?:19|20)\d{2}\s*[-/]\s*(?:(?:19|20)?\d{2})\b", raw)
    if not season_match:
        season_match = re.search(r"(?<!\d)\d{2}\s*[-/]\s*\d{2}(?!\d)", raw)
    if not season_match:
        return None

    cn = re.escape(str(card_number))
    num_patterns = [
        rf"(?:#|card\s*#?|kort\s*#?|no\.?\s*|nr\.?\s*){cn}\b",
        rf"(?<![A-Za-z0-9/]){cn}(?![A-Za-z0-9/])",
    ]
    number_match = None
    for pat in num_patterns:
        for m in re.finditer(pat, raw, flags=re.I):
            if m.start() > season_match.end():
                number_match = m
                break
        if number_match:
            break
    if not number_match:
        return None

    segment = raw[season_match.end():number_match.start()]
    tokens = re.findall(r"[A-Za-zÅÄÖåäöÀ-ÿ0-9'’-]+", segment)
    if not tokens or len(tokens) > 7:
        return None

    normalized = [normalize_text(t) for t in tokens]
    # Drop leading/trailing generic listing words, but keep internal league/program
    # tokens such as UCL, Series 1, Premier League, Chrome, Mosaic, etc.
    while normalized and normalized[0] in _RESEARCH_SET_NOISE:
        normalized.pop(0); tokens.pop(0)
    while normalized and normalized[-1] in _RESEARCH_SET_NOISE:
        normalized.pop(); tokens.pop()
    if not tokens:
        return None

    has_maker = any(t in _RESEARCH_SET_MAKERS for t in normalized)
    has_known_brand = any(t in {
        "prizm", "select", "mosaic", "optic", "chrome", "finest", "merlin",
        "mvp", "artifacts", "trilogy", "stature", "allure", "credentials",
        "immaculate", "obsidian", "premier", "dominion", "metal", "universe",
    } for t in normalized)
    if not (has_maker or has_known_brand):
        return None

    # Reject spans dominated by generic/card-condition language.
    meaningful = [t for t in normalized if t not in _RESEARCH_SET_NOISE]
    if len(meaningful) < 1:
        return None

    display = " ".join(tokens).strip(" -–—")
    # Normalize a few common manufacturer spellings for cleaner searches.
    display = re.sub(r"^UD\b", "Upper Deck", display, flags=re.I)
    display = re.sub(r"\s+", " ", display).strip()
    return display or None


def _bare_card_number(title: str, *, set_name: str | None, season: str | None, player_name: str | None) -> str | None:
    """Infer a bare checklist number only in a tightly structured title.

    Marketplace sellers often omit '#', e.g. ``1995-96 Pinnacle 101 Wayne
    Gretzky``. For research we may use that number when the title already has
    set + season + player and exactly one plausible non-year integer remains.
    This is intentionally not decision-grade evidence.
    """
    if not (set_name and season and player_name):
        return None

    raw = str(title or "")
    # Remove serial fractions, times, years/seasons and common price fragments.
    work = re.sub(r"\b\d{1,4}\s*/\s*\d{1,4}\b", " ", raw)
    work = re.sub(r"\b(?:19|20)\d{2}\s*[-/]\s*(?:(?:19|20)?\d{2})\b", " ", work)
    work = re.sub(r"(?<!\d)\d{2}\s*[-/]\s*\d{2}(?!\d)", " ", work)
    work = re.sub(r"\b(?:pris|price|buy\s*now|köp\s*nu|utropspris)\s*[:=]?\s*\d+(?:[.,]\d+)?\s*(?:kr|sek|usd|eur|\$|€)?\b", " ", work, flags=re.I)
    work = re.sub(r"\b\d{1,2}:\d{2}\b", " ", work)

    # Remove explicit checklist forms; the strict parser already handles them.
    work = re.sub(r"(?<![\w/])#\s*[A-Za-z]{0,5}[- ]?\d{1,4}\b", " ", work)
    work = re.sub(r"\b(?:card|kort|no\.?|nr\.?)\s*(?:#\s*)?[A-Za-z]{0,5}[- ]?\d{1,4}\b", " ", work, flags=re.I)

    candidates = []
    for m in re.finditer(r"(?<![A-Za-z0-9/])(\d{1,3})(?![A-Za-z0-9/])", work):
        value = int(m.group(1))
        if value <= 0:
            continue
        candidates.append(str(value))
    return candidates[0] if len(candidates) == 1 else None


def build_research_title_identity(title: str, base_features: dict | None = None) -> dict:
    """Return conservative title-derived fields usable only for research search."""
    base = dict(base_features or {})
    base_player = _txt(base.get("player_name"))
    parsed_player = _txt(extract_player_name(title)) if not base_player else ""
    if parsed_player:
        parsed_tokens = [normalize_text(t) for t in parsed_player.split()]
        noise = set(CARD_STOPWORDS) | _RESEARCH_PLAYER_NOISE
        if any(t in noise for t in parsed_tokens):
            parsed_player = ""
    player = base_player or parsed_player
    set_name = _txt(base.get("set_name") or base.get("card_set")) or _txt(extract_set_name(title))
    season = _txt(base.get("season") or base.get("year")) or _txt(extract_season(title))
    card_number = _txt(base.get("card_number") or base.get("checklist_number")) or _txt(extract_card_number(title))

    recovered = []
    # The generic card parser is intentionally conservative and its player catalogue
    # is finite. For research only, recover a likely two-token name from a strongly
    # structured title when the strict parser has no usable player.
    if not player:
        inferred_player = _research_player_candidate(
            title, set_name=set_name or None, season=season or None, card_number=card_number or None
        )
        if inferred_player:
            player = inferred_player
            recovered.append("spelare")
    inferred_set = _research_set_candidate(
        title, season=season or None, card_number=card_number or None
    )
    if inferred_set:
        current_norm = normalize_text(set_name) if set_name else ""
        inferred_norm = normalize_text(inferred_set)
        generic_strict_sets = {
            "topps", "premier", "young guns", "upper deck", "score", "pinnacle",
            "fleer", "skybox", "pacific", "donruss", "bowman", "mvp",
        }
        richer = len(inferred_norm.split()) > len(current_norm.split())
        compatible = (not current_norm) or current_norm in inferred_norm or current_norm in generic_strict_sets
        current_tokens = set(current_norm.split())
        extra_meaningful = [
            t for t in inferred_norm.split()
            if t not in current_tokens and t not in _RESEARCH_SET_NOISE
        ]
        if richer and compatible and extra_meaningful:
            set_name = inferred_set
            recovered.append("set/program")
    if not card_number:
        inferred = _bare_card_number(title, set_name=set_name or None, season=season or None, player_name=player or None)
        if inferred:
            card_number = inferred
            recovered.append("kortnummer")

    fields = {
        "player_name": player or None,
        "set_name": set_name or None,
        "season": season or None,
        "card_number": card_number or None,
        "parallel": base.get("parallel") or None,
    }
    missing = [k for k, v in fields.items() if k in {"player_name", "set_name", "season", "card_number"} and not v]
    complete = not missing
    return {
        "fields": fields,
        "complete": complete,
        "missing": missing,
        "recovered_fields": recovered,
        "source": "listing_title_research_only",
        "normalized_title": normalize_text(title),
        "note": "Titelåtervinning är endast researchstöd och får aldrig ensam låsa upp värdering eller KÖP.",
    }
