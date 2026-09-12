"""Prioritise candidates that are closest to crossing FlipFynd's evidence gate.

This queue never creates a valuation or BUY signal.  It only estimates research
leverage from already-structured evidence: exact identity readiness, exact SOLD
count and whether downstream valuation/max-price fields are already available.
"""
from __future__ import annotations


def _n(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _txt(value):
    return " ".join(str(value or "").strip().split())


def _identity_ready(item):
    return bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG"}
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
    gate = item.get("exact_identity_gate_identity_fields") or {}
    if isinstance(gate, dict) and gate.get("player_name"):
        return _txt(gate.get("player_name")).casefold()
    for key in ("player_name", "matched_player_name", "player_match_name", "spelare"):
        if item.get(key):
            return _txt(item.get(key)).casefold()
    return ""


def _unlock_score(item):
    sold = int(_n(item.get("sold_comparable_count"), 0))
    identity = _identity_ready(item)
    market = _market_value_ready(item)
    max_price = _max_price_ready(item)

    # Research leverage dominates.  Prestige may never compensate for missing
    # evidence; deal score is only a tie-breaker among equally researchable rows.
    if identity and sold == 1:
        score = 100.0
    elif identity and sold == 0:
        score = 78.0
    elif sold >= 2 and not (market and max_price):
        score = 72.0
    elif not identity:
        score = 40.0
    else:
        score = 55.0

    if market:
        score += 4
    if max_price:
        score += 4
    if item.get("is_market_edge_candidate") or item.get("is_information_edge_candidate"):
        score += 4
    if item.get("is_hidden_find_candidate") or item.get("misclassified_card_candidate") or item.get("mispriced_rookie_candidate"):
        score += 3
    score += min(5.0, max(0.0, _n(item.get("deal_score"))) * 0.05)
    return score


def _status(item):
    sold = int(_n(item.get("sold_comparable_count"), 0))
    identity = _identity_ready(item)
    market = _market_value_ready(item)
    max_price = _max_price_ready(item)
    if identity and sold == 1:
        return "ONE_SALE_AWAY", "1 extra verifierad exact SOLD kan räcka för att nå comp-tröskeln."
    if identity and sold == 0:
        return "EXACT_READY_NO_SALES", "Exakt identitet är redo; nästa steg är att hitta första verifierade exact SOLD."
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
            "sold_comps": sold,
            "identity_ready": _identity_ready(item),
            "market_value_ready": _market_value_ready(item),
            "max_price_ready": _max_price_ready(item),
            "potential": max(0.0, min(100.0, _n(item.get("deal_score")))),
            "source_item": item,
        })

    status_order = {
        "ONE_SALE_AWAY": 0,
        "EXACT_READY_NO_SALES": 1,
        "VALUATION_NEXT": 2,
        "MAX_PRICE_NEXT": 3,
        "IDENTITY_FIRST": 4,
        "REVIEW": 5,
    }
    rows.sort(key=lambda r: (status_order.get(r["status"], 9), -r["unlock_score"], -r["potential"], r["title"]))

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
        "note": "Researchkön prioriterar kort där minsta möjliga nästa evidenssteg ger störst chans att låsa upp en riktig värdering. Den skapar aldrig KÖP.",
    }
