"""Prioritise candidates that are worth researching and close to evidence unlock.

This queue never creates a valuation or BUY signal. It ranks research effort using
both evidence leverage and already-observed economic/card-quality signals. Exact
identity alone must never make a low-value commodity card the top research target.
"""
from __future__ import annotations


def _n(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _txt(value):
    return " ".join(str(value or "").strip().split())


def _clamp100(value):
    return max(0.0, min(100.0, _n(value)))


def _identity_ready(item):
    return bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG", "VERIFIERAD", "SÖKBAR"}
    )


def _research_identity_ready(item):
    return bool(
        item.get("exact_identity_gate_supports_comp_research")
        or _identity_ready(item)
        or item.get("exact_identity_gate_status") == "SÖKBAR_TITEL"
    )


def _market_value_ready(item):
    return bool(
        item.get("valuation_display_safe") is True
        and any(item.get(k) is not None for k in (
            "market_value_estimate", "expected_resale", "estimated_market_value", "marknadsvarde"
        ))
    )


def _max_price_ready(item):
    return _n(item.get("dynamic_max_total_price") or item.get("max_total_price"), 0) > 0


def _player_key(item):
    gate = item.get("exact_identity_gate_research_identity_fields") or item.get("exact_identity_gate_identity_fields") or {}
    if isinstance(gate, dict) and gate.get("player_name"):
        return _txt(gate.get("player_name")).casefold()
    for key in ("player_name", "matched_player_name", "player_match_name", "spelare"):
        if item.get(key):
            return _txt(item.get(key)).casefold()
    return ""


def _research_value_score(item):
    """Estimate whether spending comp-research time on the card is worthwhile.

    This deliberately uses only pre-existing non-valuation signals. It is not a
    market value estimate and cannot unlock BUY. The purpose is to stop easy-to-
    identify but economically trivial cards from monopolising the research queue.
    """
    deal = _clamp100(item.get("deal_score"))
    collector = _clamp100(item.get("collector_worth_score"))
    player = _clamp100(item.get("player_market_score"))
    hierarchy = max(
        _clamp100(item.get("card_hierarchy_score")),
        _clamp100(item.get("valuable_card_score")),
        _clamp100(item.get("nonstandard_value_score")),
    )

    score = (
        deal * 0.42
        + collector * 0.28
        + player * 0.12
        + hierarchy * 0.10
    )

    # Small research bonuses only. They can break ties, not turn a commodity
    # card into a high-value target on their own.
    if item.get("is_market_edge_candidate") or item.get("is_information_edge_candidate"):
        score += 4
    if item.get("is_hidden_find_candidate") or item.get("misclassified_card_candidate") or item.get("mispriced_rookie_candidate"):
        score += 5

    return max(0.0, min(100.0, score))


def _unlock_score(item):
    sold = int(_n(item.get("sold_comparable_count"), 0))
    identity = _identity_ready(item)
    research_identity = _research_identity_ready(item)
    market = _market_value_ready(item)
    max_price = _max_price_ready(item)
    value_score = _research_value_score(item)

    # Evidence leverage still matters, but it no longer dominates economic
    # relevance. A low-value exact-ID card should not outrank a materially more
    # promising card just because the former is easier to search.
    if identity and sold == 1:
        score = 70.0
    elif sold >= 2 and not (market and max_price):
        score = 62.0
    elif identity and sold == 0:
        score = 42.0
    elif research_identity and sold == 0:
        score = 36.0
    elif not identity:
        score = 18.0
    else:
        score = 30.0

    score += value_score * 0.55
    if market:
        score += 3
    if max_price:
        score += 3
    return score


def _status(item):
    sold = int(_n(item.get("sold_comparable_count"), 0))
    identity = _identity_ready(item)
    research_identity = _research_identity_ready(item)
    market = _market_value_ready(item)
    max_price = _max_price_ready(item)
    if identity and sold == 1:
        return "ONE_SALE_AWAY", "1 extra verifierad exact SOLD kan räcka för att nå comp-tröskeln."
    if identity and sold == 0:
        return "EXACT_READY_NO_SALES", "Exakt identitet är redo; nästa steg är att hitta första verifierade exact SOLD."
    if research_identity and sold == 0:
        return "RESEARCH_READY_NO_SALES", "Titeln är strukturerad nog för smal comp-research; verifiera identiteten innan en sale får räknas som exact."
    if sold >= 2 and not market:
        return "VALUATION_NEXT", "SOLD-underlag finns, men säker värdering är ännu inte upplåst."
    if sold >= 2 and market and not max_price:
        return "MAX_PRICE_NEXT", "Värdering finns; nästa steg är evidensbaserat maxpris."
    if not identity:
        return "IDENTITY_FIRST", "Verifiera exakt kortidentitet innan comp-research."
    return "REVIEW", "Granska nästa saknade evidenssteg."


def build_unlock_research_queue(items, limit=10):
    rows = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        title = _txt(item.get("titel") or item.get("title"))
        if not title:
            continue
        sold = int(_n(item.get("sold_comparable_count"), 0))
        status, action = _status(item)
        rows.append({
            "title": title,
            "url": item.get("lank") or item.get("url"),
            "player_key": _player_key(item),
            "status": status,
            "action": action,
            "unlock_score": _unlock_score(item),
            "research_value_score": _research_value_score(item),
            "sold_comps": sold,
            "identity_ready": _identity_ready(item),
            "research_identity_ready": _research_identity_ready(item),
            "market_value_ready": _market_value_ready(item),
            "max_price_ready": _max_price_ready(item),
            "potential": _clamp100(item.get("deal_score")),
            "source_item": item,
        })

    status_order = {
        "ONE_SALE_AWAY": 0,
        "VALUATION_NEXT": 1,
        "MAX_PRICE_NEXT": 2,
        "EXACT_READY_NO_SALES": 3,
        "RESEARCH_READY_NO_SALES": 4,
        "IDENTITY_FIRST": 5,
        "REVIEW": 6,
    }
    # Primary sort is the blended research priority. Evidence stage is only a
    # tie-breaker, preventing "exact ID" from being mistaken for "valuable".
    rows.sort(key=lambda r: (-r["unlock_score"], status_order.get(r["status"], 9), -r["research_value_score"], r["title"]))

    selected, used_players = [], set()
    for row in rows:
        pk = row.get("player_key")
        if pk and pk in used_players:
            continue
        selected.append(row)
        if pk:
            used_players.add(pk)
        if len(selected) >= max(0, int(limit)):
            break
    for row in rows:
        if len(selected) >= max(0, int(limit)):
            break
        if row not in selected:
            selected.append(row)

    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "rows": selected,
        "counts": counts,
        "total": len(rows),
        "near_unlock_count": counts.get("ONE_SALE_AWAY", 0),
        "exact_ready_no_sales_count": counts.get("EXACT_READY_NO_SALES", 0),
        "note": "Researchkön väger nu ihop evidenshävstång med ekonomisk relevans. Exakt identitet ensam får inte göra ett lågvärdeskort till högsta prioritet. Kön skapar aldrig KÖP eller marknadsvärde.",
    }
