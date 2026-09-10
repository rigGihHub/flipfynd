"""Bad Listing Hunter 2.0.

Finds listings whose *presentation* may make them easier for other buyers to miss.
It only reuses evidence already produced by FlipFynd. It does not spell-correct a
player into a new identity, infer a missing variant, create market value, or make a
BUY decision.
"""
from __future__ import annotations


def _text_list(value):
    return [str(x).strip() for x in (value or []) if str(x).strip()]


def build_bad_listing_signal(item: dict | None) -> dict:
    item = item or {}
    reasons = []
    verify = []
    traits = []

    warnings = _text_list(item.get("listing_quality_warnings"))
    blockers = _text_list(item.get("listing_quality_blockers"))
    quality = item.get("listing_quality_score")
    try:
        quality = float(quality) if quality is not None else None
    except (TypeError, ValueError):
        quality = None

    # Existing listing-quality evidence is the primary source.
    for warning in warnings:
        w = warning.casefold()
        if "kort annonstitel" in w:
            traits.append("very-short-title")
        if "set/program" in w:
            traits.append("missing-set")
            verify.append("set/program")
        if "år/säsong" in w:
            traits.append("missing-season")
            verify.append("år/säsong")
        if "kortnummer" in w:
            traits.append("missing-card-number")
            verify.append("kortnummer")
        if "vag" in w or "osäker" in w:
            traits.append("vague-description")
        if "premiumegenskap" in w:
            traits.append("incomplete-premium-identity")
            verify.extend(["set/program", "år/säsong", "exakt premiumegenskap"])
        reasons.append(warning)

    for blocker in blockers:
        b = blocker.casefold()
        if "spelaren" in b:
            traits.append("uncertain-player-text")
            verify.append("spelare")
        if "variant" in b:
            traits.append("variant-without-product-identity")
            verify.extend(["parallel/variant", "set/program"])
        if "motstridig" in b:
            traits.append("identity-conflict")
            verify.append("motstridig kortinformation")
        reasons.append(blocker)

    # Reuse existing discoverability / information-asymmetry evidence.
    if item.get("is_hidden_find_candidate"):
        traits.append("underexposed")
        reasons.extend(_text_list(item.get("hidden_find_reasons")))
    if item.get("is_information_edge_candidate"):
        traits.append("information-gap")
        reasons.extend(_text_list(item.get("information_edge_reasons")))
        verify.extend(_text_list(item.get("information_edge_verify_first")))

    # A non-standard player match is only a review clue. We never convert it
    # into a corrected player identity.
    match_type = str(item.get("player_match_type") or "").strip().casefold()
    match_conf = str(item.get("player_match_confidence") or "").strip().casefold()
    if match_type and match_type not in {"exact", "alias"}:
        traits.append("nonstandard-player-text")
        verify.append("spelarnamn mot annonsbild/annonsinfo")
    if match_conf == "low":
        traits.append("low-player-text-confidence")

    # Candidate threshold is evidence-count based, not a market/opportunity score.
    unique_traits = list(dict.fromkeys(traits))
    candidate = bool(
        len(unique_traits) >= 2
        or (quality is not None and quality < 55 and unique_traits)
        or "identity-conflict" in unique_traits
    )

    if "identity-conflict" in unique_traits:
        label = "Motstridig annons – manuell identitetskontroll"
    elif candidate:
        label = "Dåligt beskriven annons – kan missas av andra"
    elif unique_traits:
        label = "Mindre annonsbrist"
    else:
        label = "Ingen tydlig Bad Listing-signal"

    return {
        "candidate": candidate,
        "label": label,
        "traits": unique_traits[:10],
        "reasons": list(dict.fromkeys(reasons))[:8],
        "verify_first": list(dict.fromkeys(verify))[:8],
        "listing_quality_score": quality,
        "review_only": True,
        "can_create_identity": False,
        "can_create_market_value": False,
        "can_create_buy_decision": False,
        "note": (
            "Bad Listing Hunter hittar svaga annonser. Den får inte rätta stavning till "
            "en ny spelare, fylla i saknad variant eller skapa värde/KÖP."
        ),
    }


def build_bad_listing_queue(items, limit=8):
    rows=[]
    for item in items or []:
        signal=build_bad_listing_signal(item)
        if not signal["candidate"]:
            continue
        rows.append({
            "title": item.get("titel") or item.get("title") or "Okänd annons",
            "url": item.get("url"),
            "decision": item.get("beslut") or item.get("decision"),
            "signal": signal,
            "_rank": (
                len(signal["traits"]),
                -float(signal["listing_quality_score"]) if signal["listing_quality_score"] is not None else 0.0,
                float(item.get("opportunity_priority_score") or 0),
                float(item.get("rank_score") or 0),
            ),
        })
    rows.sort(key=lambda r:r["_rank"], reverse=True)
    for row in rows:
        row.pop("_rank",None)
    return {"rows":rows[:max(0,int(limit))],"creates_new_decision":False,"creates_new_value":False}
