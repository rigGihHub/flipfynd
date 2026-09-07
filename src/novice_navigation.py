"""Action-first navigation helpers for novice FlipFynd users.

This layer does not create new valuation, buy decisions, max prices or market facts.
It only reorganises already analysed candidates into simpler user-facing views.
"""
from __future__ import annotations

from src.best_buy_decision_card import build_best_buy_decision_card
from src.ending_soon_hunter import build_ending_soon_opportunity


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _url(item):
    return item.get("lank") or item.get("url")


def _title(item):
    return item.get("titel") or item.get("title") or "Okänd annons"


def build_buy_view(candidates):
    """Return the existing fail-closed best-buy card without changing its decision."""
    result = build_best_buy_decision_card(candidates or [])
    return {
        "view": "buy",
        "status": result.get("status"),
        "card": result.get("card"),
        "note": result.get("note"),
        "creates_new_decision": False,
    }


def build_ending_soon_view(candidates, limit=8):
    """Prioritise only candidates already eligible in Ending Soon Hunter."""
    rows = []
    for item in candidates or []:
        ending = build_ending_soon_opportunity(item)
        if not ending.get("eligible"):
            continue
        rows.append({
            "title": _title(item),
            "url": _url(item),
            "decision": item.get("beslut") or item.get("decision") or item.get("recommendation"),
            "total_cost": item.get("analysis_total_cost") or item.get("total_cost"),
            "max_total_price": item.get("dynamic_max_total_price") or item.get("max_total_price"),
            "remaining_minutes": ending.get("remaining_minutes"),
            "label": ending.get("label"),
            "reasons": ending.get("reasons") or [],
            "_priority": _num(ending.get("score")),
        })
    rows.sort(key=lambda row: (-row["_priority"], row["title"]))
    for row in rows:
        row.pop("_priority", None)
    return {
        "view": "ending_soon",
        "status": "READY" if rows else "EMPTY",
        "rows": rows[: max(1, int(limit))],
        "count": len(rows),
        "creates_new_decision": False,
        "note": "Visar bara auktioner där sluttid, identitet, sold-underlag och befintligt säkert maxbud redan räcker för Ending Soon Hunter.",
    }


def build_watch_view(candidates, limit=8):
    """Surface existing watch/near-buy states; never upgrade them to BUY."""
    rows = []
    for item in candidates or []:
        decision = str(item.get("beslut") or item.get("decision") or "").upper()
        action = str(item.get("opportunity_action") or "").upper()
        if action != "BEVAKA" and decision not in {"KANSKE", "BEVAKA"}:
            continue
        rows.append({
            "title": _title(item),
            "url": _url(item),
            "decision": item.get("beslut") or item.get("decision"),
            "total_cost": item.get("analysis_total_cost") or item.get("total_cost"),
            "max_total_price": item.get("max_total_price"),
            "primary_blocker": (item.get("decision_diagnostics") or [None])[0],
            "identity_status": item.get("exact_identity_gate_status"),
            "sold_comps": int(item.get("sold_comparable_count") or 0),
            "_priority": _num(item.get("opportunity_priority_score"), _num(item.get("deal_score"))),
        })
    rows.sort(key=lambda row: (-row["_priority"], row["title"]))
    for row in rows:
        row.pop("_priority", None)
    return {
        "view": "watch",
        "status": "READY" if rows else "EMPTY",
        "rows": rows[: max(1, int(limit))],
        "count": len(rows),
        "creates_new_decision": False,
        "note": "Bevakningsvyn visar befintliga väntelägen. Den skapar aldrig ett nytt KÖP-beslut.",
    }


def build_research_view(candidates, limit=10):
    """Collect existing research flags without presenting them as buy signals."""
    rows = []
    for item in candidates or []:
        signals = []
        if item.get("is_information_edge_candidate"):
            signals.append("Variant/info kan vara underskattad")
        if item.get("is_market_edge_candidate"):
            signals.append("Möjlig marknadsedge")
        if item.get("is_hidden_find_candidate"):
            signals.append("Svårhittad annons")
        if item.get("misclassified_card_candidate"):
            signals.append("Kan vara felklassificerad")
        if item.get("mispriced_rookie_candidate"):
            signals.append("Rookie-signal kräver verifiering")
        if not signals:
            continue
        rows.append({
            "title": _title(item),
            "url": _url(item),
            "decision": item.get("beslut") or item.get("decision"),
            "signals": signals,
            "verify_first": list(item.get("information_edge_verify_first") or [])[:4],
            "_priority": _num(item.get("opportunity_priority_score"), _num(item.get("deal_score"))),
        })
    rows.sort(key=lambda row: (-row["_priority"], row["title"]))
    for row in rows:
        row.pop("_priority", None)
    return {
        "view": "research",
        "status": "READY" if rows else "EMPTY",
        "rows": rows[: max(1, int(limit))],
        "count": len(rows),
        "creates_new_decision": False,
        "note": "Researchsignaler är ledtrådar för vidare kontroll och får inte tolkas som KÖP utan ordinarie beslutsunderlag.",
    }
