"""Explain why analysed listings do not reach FlipFynd's buy threshold.

This module only summarizes already-computed analysis fields. It does not alter
valuation, ranking, max-bid or decisions.
"""
from collections import Counter


def _primary_blocker(item: dict) -> str:
    decision = str(item.get("beslut") or "")
    if decision.startswith("KÖP"):
        return "KÖP"

    identity = float(item.get("exact_identity_gate_score") or item.get("card_identity_confidence_score") or 0)
    valuation = float(item.get("valuation_confidence_score") or item.get("valuation_confidence") or 0)
    comps = int(item.get("comparable_count") or 0)
    net = float(item.get("net_profit_estimate") or 0)
    roi = float(item.get("roi_estimate") or 0)
    risk = float(item.get("risk_score") or 0)
    liquidity = float(item.get("liquidity_score") or 0)

    if item.get("exact_identity_gate_status") in {"LÅST", "GRANSKA"} or identity < 55:
        return "Osäker kortidentitet"
    if comps < 2 or valuation < 60:
        return "För svagt prisunderlag"
    if net < 30 or roi < 0.18:
        return "För liten vinstmarginal"
    if risk >= 60:
        return "För hög risk"
    if liquidity and liquidity < 45:
        return "För låg säljbarhet"
    return "Når inte köpgränsen"


def summarize_no_find_reasons(items):
    analysed = list(items or [])
    counts = Counter(_primary_blocker(item) for item in analysed)
    buy_count = counts.pop("KÖP", 0)
    ordered = [
        "Osäker kortidentitet",
        "För svagt prisunderlag",
        "För liten vinstmarginal",
        "För hög risk",
        "För låg säljbarhet",
        "Når inte köpgränsen",
    ]
    return {
        "analysed": len(analysed),
        "buy_count": buy_count,
        "reasons": [{"label": label, "count": int(counts.get(label, 0))} for label in ordered if counts.get(label, 0)],
    }
