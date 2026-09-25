"""Stable, honest net-profit summaries for highlighted seller results."""
from __future__ import annotations

from math import isfinite


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def build_seller_net_profit_summary(row: dict | None) -> dict:
    """Return the only profit figure the seller card is allowed to show.

    Active asking prices are explicitly labelled as a scenario. A normal net
    profit is shown only when the analyser says the valuation is display-safe.
    Risk-adjusted profit is deliberately not used: it is a ranking input, not
    the user's actual money outcome.
    """
    row = row or {}
    asking = row.get("asking_price_opportunity") or {}
    asking_margin = _number(asking.get("net_margin"))
    if asking_margin is not None:
        return {
            "available": True,
            "value": asking_margin,
            "label": "Nettovinst mot prisindikation",
            "basis": "aktiv jämförelse, inte genomförd försäljning",
        }

    net_profit = _number(row.get("net_profit_estimate"))
    if net_profit is not None and row.get("valuation_display_safe") is True:
        return {
            "available": True,
            "value": net_profit,
            "label": "Nettovinst efter kostnader",
            "basis": "verifierad marknadsevidens",
        }

    return {
        "available": False,
        "value": None,
        "label": "Nettovinst",
        "basis": "ej beräkningsbar med tillräckligt underlag",
    }
