"""Scenario engine for FlipFynd.

Builds three transparent resale scenarios from values already produced by the
main analyzer. It does not invent a new market value and may not alter the buy
decision or max bid. The scenarios only show the economics if the card is sold
at the analyzer's floor, expected, or best-reasonable resale values.
"""
from __future__ import annotations

from typing import Any


def _num(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sale_costs(resale_price: float) -> dict[str, float]:
    """Mirror current FlipFynd selling assumptions explicitly."""
    outbound_shipping = 18.0 if resale_price <= 200 else 36.0
    selling_fee = round(resale_price * 0.08)
    packaging = 3.0
    return {
        "outbound_shipping": outbound_shipping,
        "selling_fee": float(selling_fee),
        "packaging": packaging,
        "total_selling_cost": outbound_shipping + float(selling_fee) + packaging,
    }


def _sellability_label(score: float) -> str:
    if score >= 82:
        return "Mycket lättsålt"
    if score >= 68:
        return "Lättsålt"
    if score >= 50:
        return "Normalt"
    if score >= 35:
        return "Trögsålt"
    return "Svårsålt"


def _scenario(
    *,
    key: str,
    label: str,
    resale_price: float,
    total_cost: float,
    liquidity_score: float,
    probability: float,
    sellability_adjustment: float,
    explanation: str,
) -> dict[str, Any]:
    costs = _sale_costs(resale_price)
    net_profit = resale_price - total_cost - costs["total_selling_cost"]
    roi = net_profit / total_cost if total_cost > 0 else 0.0
    sellability_score = max(0.0, min(100.0, liquidity_score + sellability_adjustment))
    # This is a scenario-relative indicator, not a forecasted probability.
    relative_exit = max(0.0, min(100.0, probability + sellability_adjustment * 0.6))
    return {
        "key": key,
        "label": label,
        "resale_price": round(resale_price, 2),
        "net_profit": round(net_profit, 2),
        "roi": round(roi, 3),
        "sellability_score": round(sellability_score, 1),
        "sellability_label": _sellability_label(sellability_score),
        "relative_exit_score": round(relative_exit, 1),
        "selling_costs": costs,
        "profitable": net_profit > 0,
        "explanation": explanation,
    }


def build_flip_scenarios(
    *,
    total_cost: object,
    floor_resale: object,
    expected_resale: object,
    best_case_resale: object,
    liquidity_score: object,
    sale_probability: object,
) -> dict[str, Any]:
    """Return quick/normal/best-reasonable scenarios from existing values."""
    cost = _num(total_cost)
    floor = max(0.0, _num(floor_resale))
    expected = max(0.0, _num(expected_resale))
    best = max(0.0, _num(best_case_resale))
    liquidity = max(0.0, min(100.0, _num(liquidity_score, 50.0)))
    probability = max(0.0, min(100.0, _num(sale_probability, 50.0)))

    if cost <= 0 or max(floor, expected, best) <= 0:
        return {
            "available": False,
            "scenarios": [],
            "resilient_flip": False,
            "summary": "Otillräckligt underlag för scenariosimulering.",
            "note": "Scenario Engine skapar aldrig ett eget marknadsvärde.",
        }

    scenarios = [
        _scenario(
            key="quick",
            label="Snabb försäljning",
            resale_price=floor,
            total_cost=cost,
            liquidity_score=liquidity,
            probability=probability,
            sellability_adjustment=10,
            explanation="Utgår från FlipFynds försiktiga/floor-värde för att testa om affären håller vid snabbare exit.",
        ),
        _scenario(
            key="normal",
            label="Normal försäljning",
            resale_price=expected,
            total_cost=cost,
            liquidity_score=liquidity,
            probability=probability,
            sellability_adjustment=0,
            explanation="Utgår från FlipFynds förväntade värde och ordinarie säljbarhetsbedömning.",
        ),
        _scenario(
            key="best",
            label="Bästa rimliga försäljning",
            resale_price=best,
            total_cost=cost,
            liquidity_score=liquidity,
            probability=probability,
            sellability_adjustment=-15,
            explanation="Utgår från FlipFynds befintliga best-case-värde och antar att en högre prisnivå normalt kräver mer tålamod.",
        ),
    ]

    quick = scenarios[0]
    normal = scenarios[1]
    resilient = quick["net_profit"] >= 20 and quick["roi"] >= 0.10
    if resilient:
        summary = "Affären ser robust ut även i scenariot Snabb försäljning."
    elif normal["net_profit"] > 0:
        summary = "Affären kräver ungefär normal prisnivå för att ge positiv nettovinst."
    else:
        summary = "Affären är svag även vid FlipFynds förväntade försäljningsvärde."

    return {
        "available": True,
        "scenarios": scenarios,
        "resilient_flip": resilient,
        "summary": summary,
        "note": (
            "Scenario Engine använder bara redan beräknade floor/expected/best-värden. "
            "Säljbarhet per scenario är en relativ heuristik, inte en tids- eller sannolikhetsgaranti."
        ),
    }
