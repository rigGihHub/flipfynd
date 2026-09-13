"""Oddity & Story Card Hunter.

Ranks listings that may hide a collector story/anomaly the seller has not priced
or described well. It is deliberately a *research* queue. It cannot create an
identity, market value, SOLD comp or BUY decision.
"""
from __future__ import annotations


def _text_list(value):
    return [str(x).strip() for x in (value or []) if str(x).strip()]


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def build_oddity_story_signal(item: dict | None) -> dict:
    item = item or {}
    signals = [x for x in (item.get("nonstandard_value_signals") or []) if isinstance(x, dict)]
    known = _text_list(item.get("nonstandard_value_known_matches"))
    title = str(item.get("titel") or item.get("title") or "")
    title_cf = title.casefold()

    reasons=[]
    verify=[]
    flags=[]

    for sig in signals:
        label=str(sig.get("type") or "Ovanlig värdedrivare").strip()
        reason=str(sig.get("reason") or "").strip()
        confidence=str(sig.get("confidence") or "").strip()
        flags.append(label)
        if reason:
            reasons.append(reason)
        if confidence == "KNOWN_CARD_MATCH":
            verify.extend(["exakt kort/variant", "referensbild/checklista", "faktiska SOLD-comps"])
        else:
            verify.extend(["erkänd variant", "faktisk knapphet", "faktiska SOLD-comps"])

    # Known story card whose story is not advertised in title = particularly
    # interesting information-asymmetry candidate.
    story_terms=("menendez","marlboro","error","feltryck","nnof","no name","variation","variant","censor","censur")
    story_mentioned=any(t in title_cf for t in story_terms)
    seller_may_have_missed_story=bool(known and not story_mentioned)
    if seller_may_have_missed_story:
        flags.append("story-omission")
        reasons.append("Känt story/error-kort men den särskilda värdedrivaren nämns inte tydligt i annonsrubriken.")
        verify.append("om annonsbilden faktiskt visar rätt story/error-variant")

    if item.get("is_hidden_find_candidate"):
        flags.append("underexposed")
        reasons.extend(_text_list(item.get("hidden_find_reasons"))[:2])
    if item.get("is_information_edge_candidate"):
        flags.append("information-gap")
        reasons.extend(_text_list(item.get("information_edge_reasons"))[:2])
        verify.extend(_text_list(item.get("information_edge_verify_first"))[:3])

    listing_quality=_num(item.get("listing_quality_score"), 100)
    if listing_quality < 60:
        flags.append("weak-listing")
        reasons.append("Annonsen är relativt svagt beskriven, vilket kan göra en udda variant lättare att missa.")

    signal_score=_num(item.get("nonstandard_value_signal_score"), 0)
    candidate=bool(known or signal_score >= 6)

    # Priority rewards documented story matches and information asymmetry, not
    # generic fame/player score. This queue is about *why this exact card may be
    # overlooked*, not who the player is.
    priority=(
        len(known)*45
        + min(25, signal_score)
        + (18 if seller_may_have_missed_story else 0)
        + (8 if item.get("is_information_edge_candidate") else 0)
        + (5 if item.get("is_hidden_find_candidate") else 0)
        + (5 if listing_quality < 60 else 0)
    )
    priority=min(100, int(round(priority)))

    if known and seller_may_have_missed_story:
        label="KÄND STORY/ODDITY – säljaren kan ha missat poängen"
    elif known:
        label="KÄND STORY/ODDITY – verifiera exakt variant"
    elif candidate:
        label="MÖJLIG ODDITY – värd riktad research"
    else:
        label="Ingen tydlig oddity/story-signal"

    return {
        "candidate": candidate,
        "label": label,
        "priority_score": priority,
        "known_story_matches": known,
        "flags": list(dict.fromkeys(flags))[:10],
        "reasons": list(dict.fromkeys(reasons))[:8],
        "verify_first": list(dict.fromkeys(verify))[:8],
        "research_prompts": _text_list(item.get("nonstandard_value_research_prompts"))[:6],
        "seller_may_have_missed_story": seller_may_have_missed_story,
        "research_only": True,
        "can_create_identity": False,
        "can_create_sold_comp": False,
        "can_create_market_value": False,
        "can_create_buy_decision": False,
        "note": "Oddity & Story Hunter hittar informationsasymmetri. Storyn måste verifieras mot exakt variant och SOLD-data innan någon premie får räknas.",
    }


def build_oddity_story_queue(items, limit=8):
    rows=[]
    for item in items or []:
        signal=build_oddity_story_signal(item)
        if not signal["candidate"]:
            continue
        rows.append({
            "title": item.get("titel") or item.get("title") or "Okänd annons",
            "url": item.get("url"),
            "decision": item.get("beslut") or item.get("decision"),
            "signal": signal,
            "_rank": (
                signal["priority_score"],
                len(signal["known_story_matches"]),
                _num(item.get("nonstandard_value_signal_score"),0),
                _num(item.get("opportunity_priority_score"),0),
            ),
        })
    rows.sort(key=lambda r:r["_rank"], reverse=True)
    for row in rows:
        row.pop("_rank",None)
    return {
        "rows": rows[:max(0,int(limit))],
        "creates_new_identity": False,
        "creates_new_sold_comp": False,
        "creates_new_value": False,
        "creates_new_decision": False,
    }
