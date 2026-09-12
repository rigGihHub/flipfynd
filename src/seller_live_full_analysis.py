"""Full-analysis bridge for live same-seller Tradera discoveries.

The quick seller scan only triages which live listings deserve attention. This
module promotes one selected live listing into the normal full FlipFynd analysis
pipeline and returns a compact, evidence-aware summary for the same-seller UI.
It does not bypass any existing identity, SOLD, valuation or BUY gates.
"""
from __future__ import annotations

from typing import Callable, Iterable


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _price(item: dict):
    for key in ("pris", "price", "current_price"):
        value = item.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def _title(item: dict) -> str:
    return str(item.get("titel") or item.get("title") or "Kortannons").strip()


def full_analyze_live_seller_item(
    item: dict,
    *,
    analyze_fn: Callable,
    all_items: Iterable[dict] | None = None,
    sport: str = "hockey",
    strategy_mode: str = "quick_flip",
) -> dict:
    """Run the normal full analyser for one live seller listing.

    The returned status is a UI summary only. BUY is copied from the underlying
    analyser; this function never manufactures or upgrades the decision.
    """
    prepared = dict(item or {})
    if not prepared.get("source_category"):
        prepared["source_category"] = "Hockey - NHL" if sport == "hockey" else "Fotboll"

    result = analyze_fn(
        prepared,
        all_items=list(all_items or []),
        mode="full",
        strategy_mode=strategy_mode,
        sport=sport,
    )
    merged = dict(prepared)
    if isinstance(result, dict):
        merged.update(result)

    decision = str(merged.get("beslut") or merged.get("decision") or "SKIP")
    decision_upper = decision.upper()
    sold = int(_num(merged.get("sold_comparable_count") or merged.get("sold_comps")))
    identity_ok = bool(merged.get("exact_identity_gate_supports_exact_comp_search"))
    identity_score = _num(merged.get("exact_identity_gate_score"))
    valuation = _num(merged.get("valuation_confidence_score"))
    edge = _num(merged.get("market_edge_score"))
    max_price = merged.get("max_price")
    if max_price is None:
        max_price = merged.get("max_buy_price")
    total_cost = merged.get("total_cost")
    if total_cost is None:
        total_cost = merged.get("total_acquisition_cost")
    if total_cost is None:
        total_cost = _price(merged)

    if decision_upper.startswith("KÖP"):
        label = "KÖP-KANDIDAT"
        reason = "Fullanalysen gav köpsignal. Kontrollera annonsen och samfrakten innan du agerar."
    elif identity_ok and sold >= 2 and valuation >= 45:
        label = "VERIFIERAD MEN INTE KÖP"
        reason = "Identitet och marknadsunderlag är tillräckligt starka, men ekonomin klarar inte köpgränsen."
    elif identity_ok and sold >= 1:
        label = "BEVAKA / FORSKA VIDARE"
        reason = "Kortet är sökbart och har viss SOLD-evidens, men beslutsunderlaget är ännu för tunt."
    else:
        label = "OTILLRÄCKLIGT UNDERLAG"
        reason = "Fullanalysen kan ännu inte verifiera tillräcklig identitet och marknadsevidens för köp."

    return {
        "ok": True,
        "label": label,
        "reason": reason,
        "title": _title(merged),
        "url": merged.get("lank") or merged.get("url") or merged.get("link"),
        "decision": decision,
        "price": _price(merged),
        "total_cost": total_cost,
        "max_price": max_price,
        "identity_ok": identity_ok,
        "identity_score": identity_score,
        "sold_comps": sold,
        "valuation_confidence": valuation,
        "market_edge": edge,
        "source_item": merged,
    }
