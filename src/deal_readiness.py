"""Final evidence gate for presenting a card as an actionable find."""
from __future__ import annotations

from math import isfinite

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
    # Older compact seller rows omitted risk. Recover it from the original
    # analysis, but never turn absent/invalid evidence into a passing default.
    source = row.get("source_item") or {}
    risk_values = [item.get("risk_score") for item in (row, source)
                   if item.get("risk_score") not in (None, "")]
    parsed_risks = [_num(value, float("nan")) for value in risk_values]
    risk_verified = bool(parsed_risks) and all(
        not isinstance(value, bool) and isfinite(parsed) and 0 <= parsed <= 100
        for value, parsed in zip(risk_values, parsed_risks)
    )
    risk = max(parsed_risks) if risk_verified else None
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
    if not risk_verified:
        blockers.append("köprisken är inte verifierad")
    elif risk > 65:
        blockers.append("köprisken är för hög")
    if row.get("analysis_level") == "quick_fallback":
        blockers.append("djupanalys återstår")
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
