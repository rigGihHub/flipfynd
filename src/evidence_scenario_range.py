"""Evidence-based resale scenarios from independent verified Exact sold comps.

This module does not estimate a new market value. It summarizes the observed
price range in an already decision-grade Exact comp set as low / median / high.
"""
from __future__ import annotations

from statistics import median
from src.comp_set_consistency import collapse_independent_observations


def _n(value):
    if value in (None, ""):
        return None
    try:
        number=float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _selling_fee(price: float) -> float:
    # Mirror the app's existing Tradera-private fee assumption; do not create
    # a scenario-specific fee heuristic.
    return min(200.0, max(3.0, price * 0.10)) if price > 0 else 0.0


def _economics(resale: float, total_cost: float | None) -> dict:
    if total_cost in (None, 0):
        return {"resale_price":round(resale,2),"net_profit":None,"roi_pct":None}
    fee=_selling_fee(resale)
    packaging=3.0
    profit=resale-total_cost-fee-packaging
    return {
        "resale_price":round(resale,2),
        "selling_fee":round(fee,2),
        "packaging":packaging,
        "net_profit":round(profit,2),
        "roi_pct":round(profit/total_cost*100,1),
    }


def build_evidence_scenario_range(exact_rows, *, total_cost=None, decision_grade=False):
    consistency=collapse_independent_observations(list(exact_rows or []))
    rows=consistency.get("rows") or []
    prices=[]
    for row in rows:
        price=_n(row.get("price") if row.get("price") not in (None,"") else row.get("sold_price"))
        if price is not None:
            prices.append(price)

    if not decision_grade:
        return {
            "status":"BLOCKED",
            "available":False,
            "independent_count":len(rows),
            "priced_count":len(prices),
            "note":"Scenariointervallet visas bara när Exact-underlaget redan är decision-grade. Det skapar aldrig kvalitet på egen hand.",
        }
    if len(prices) < 3:
        return {
            "status":"INSUFFICIENT_DATA",
            "available":False,
            "independent_count":len(rows),
            "priced_count":len(prices),
            "note":"Minst tre prissatta oberoende Exact-comps behövs eftersom Comp Quality Guard kräver det för decision-grade.",
        }

    prices=sorted(prices)
    low=prices[0]
    likely=median(prices)
    high=prices[-1]
    cost=_n(total_cost)

    scenarios=[
        {"key":"weak","label":"Svagt realistiskt","basis":"lägsta observerade Exact-försäljning",**_economics(low,cost)},
        {"key":"likely","label":"Troligt","basis":"medianen av observerade Exact-försäljningar",**_economics(likely,cost)},
        {"key":"strong","label":"Starkt","basis":"högsta observerade Exact-försäljning",**_economics(high,cost)},
    ]
    return {
        "status":"READY",
        "available":True,
        "independent_count":len(rows),
        "priced_count":len(prices),
        "price_low":round(low,2),
        "price_median":round(likely,2),
        "price_high":round(high,2),
        "scenarios":scenarios,
        "all_observed_prices":[round(x,2) for x in prices],
        "note":"Svagt/troligt/starkt är observerad låg/median/hög nivå i decision-grade Exact-comps. Det är inte sannolikhetsprognoser och inga procentpåslag används.",
    }
