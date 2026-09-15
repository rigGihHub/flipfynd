"""Final evidence gate for presenting a card as an actionable find."""
from __future__ import annotations

from src.card_listing_integrity import assess_listing_integrity


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def assess_deal_readiness(row: dict) -> dict:
    decision = str(row.get("beslut") or row.get("decision") or "SKIP").upper()
    identity = bool(
        row.get("exact_identity_gate_supports_exact_comp_search")
        or row.get("exact_identity_gate_supports_dynamic_max_bid")
        or row.get("identity_ok")
    )
    sold = int(_num(row.get("sold_comparable_count") or row.get("sold_comps")))
    valuation = _num(row.get("valuation_confidence_score") or row.get("valuation_confidence"))
    risk = _num(row.get("risk_score"), 50)
    integrity = assess_listing_integrity(row.get("source_item") or row)
    blockers = []
    if not decision.startswith("KÖP"):
        blockers.append("analysen ger ingen köpsignal")
    if not identity:
        blockers.append("exakt kortidentitet är inte verifierad")
    if sold < 1:
        blockers.append("verifierade SOLD-comps saknas")
    if valuation < 55:
        blockers.append("värderingssäkerheten är under 55/100")
    if risk > 65:
        blockers.append("köprisken är för hög")
    if not integrity["eligible_physical_single_card"]:
        blockers.append("annonsen är inte ett verifierbart fysiskt singelkort")
    if integrity["reprint_risk"]:
        blockers.append("nytryck/reproduktion är inte köpklart")
    return {
        "ready_for_find": not blockers,
        "status": "KÖPKLAR" if not blockers else "INTE KÖPKLAR",
        "blockers": blockers,
        "identity_verified": identity,
        "sold_comparable_count": sold,
        "valuation_confidence_score": valuation,
        "risk_score": risk,
    }
