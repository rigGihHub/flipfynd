"""Mispricing Detector 2.0.

Explains *why* an already-analysed listing deserves extra mispricing research.
It creates no market value, price gap, card identity, max bid or BUY decision.
A listing is only called price-gap supported when an existing hunter has already
established that fact from sold-comparable evidence.
"""
from __future__ import annotations


def _n(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def build_mispricing_hypothesis(item: dict | None) -> dict:
    item = item or {}
    reasons, verify, types = [], [], []

    if item.get("misclassified_card_candidate"):
        types.append("possible-misclassification")
        reasons.extend(item.get("misclassified_card_reasons") or [])
        verify.extend(["exakt variant", "kortnummer", "set/program"])

    if item.get("is_information_edge_candidate"):
        types.append("information-gap")
        reasons.extend(item.get("information_edge_reasons") or [])
        verify.extend(item.get("information_edge_verify_first") or [])

    if item.get("is_hidden_find_candidate"):
        types.append("underexposed-listing")
        reasons.extend(item.get("hidden_find_reasons") or [])

    if item.get("mispriced_rookie_candidate"):
        types.append("rookie-underdescription")
        reasons.extend(item.get("mispriced_rookie_reasons") or [])
        verify.extend(["rookiestatus", "rookieprogram", "exakt variant"])

    rung = int(_n(item.get("variant_hierarchy_variant_rung")))
    tags = list(item.get("valuable_card_tags") or [])
    if rung > 0 or tags:
        types.append("variant-or-scarcity")
        if tags:
            reasons.append("Kortstrukturen har befintliga granskningssignaler: " + ", ".join(map(str, tags[:4])) + ".")
        verify.extend(["parallel/variant", "eventuell serienumrering"])

    price_gap_supported = bool(
        item.get("misclassified_card_price_gap_supported")
        or item.get("mispriced_rookie_price_gap_supported")
    )

    identity_status = str(item.get("exact_identity_gate_status") or "").upper()
    identity_search_ready = bool(item.get("exact_identity_gate_supports_exact_comp_search"))
    sold_count = max(0, int(_n(item.get("sold_comparable_count"))))
    valuation_safe = bool(item.get("valuation_display_safe"))

    if price_gap_supported:
        status = "SUPPORTED_PRICE_GAP"
        headline = "Verifierat prisgap värt extra kontroll"
    elif types:
        status = "RESEARCH_HYPOTHESIS"
        headline = "Misstänkt felprissättning – inte verifierad"
    else:
        status = "NO_SIGNAL"
        headline = "Ingen särskild felprissättningssignal"

    blockers = []
    if types and not identity_search_ready:
        blockers.append("exakt kortidentitet är inte redo för exact-comp-sökning")
    if types and sold_count < 2:
        blockers.append("minst två matchande verifierade sold comps saknas")
    if types and not valuation_safe:
        blockers.append("marknadsvärdet är inte godkänt för visning")

    return {
        "status": status,
        "headline": headline,
        "hypothesis_types": list(dict.fromkeys(types)),
        "reasons": list(dict.fromkeys(str(x) for x in reasons if x))[:8],
        "verify_first": list(dict.fromkeys(str(x) for x in verify if x))[:8],
        "blockers": blockers,
        "price_gap_supported": price_gap_supported,
        "identity_status": identity_status or "EJ SÄKERT",
        "sold_comparable_count": sold_count,
        "valuation_safe": valuation_safe,
        "review_only": not price_gap_supported,
        "can_create_buy_decision": False,
        "can_create_market_value": False,
        "note": "Mispricing Detector förklarar befintliga fyndsignaler. En research-hypotes är inte bevis på felprissättning.",
    }


def build_mispricing_review_queue(items, limit=10):
    rows=[]
    for item in items or []:
        h=build_mispricing_hypothesis(item)
        if h["status"] == "NO_SIGNAL":
            continue
        rows.append({
            "title": item.get("titel") or item.get("title") or "Okänt kort",
            "url": item.get("url"),
            "decision": item.get("beslut") or item.get("decision"),
            "hypothesis": h,
            "_priority": (
                1 if h["price_gap_supported"] else 0,
                len(h["hypothesis_types"]),
                _n(item.get("opportunity_priority_score")),
                _n(item.get("rank_score")),
            ),
        })
    rows.sort(key=lambda r:r["_priority"], reverse=True)
    for row in rows:
        row.pop("_priority",None)
    return {"rows":rows[:max(0,int(limit))],"creates_new_decision":False,"creates_new_value":False}
