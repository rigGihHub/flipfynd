"""Stable, honest net-profit summaries for highlighted seller results."""
from __future__ import annotations

from math import isfinite


PROFIT_EVIDENCE_FIELDS = (
    "net_profit_estimate", "estimated_net_profit", "valuation_display_safe",
    "practical_price_source", "asking_price_opportunity", "asking_net_margin",
)


def seller_profit_evidence(row: dict | None) -> dict:
    """Carry economics through compact results and older saved snapshots.

    Explicit compact values (including zero, False and None) win over the
    original source. Only absent fields are recovered from the source.
    """
    row = row or {}
    source = row.get("source_item") or {}
    return {key: row[key] if key in row else source[key]
            for key in PROFIT_EVIDENCE_FIELDS if key in row or key in source}


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
    row = seller_profit_evidence(row)
    net_profit = _number(row.get("net_profit_estimate"))
    if net_profit is None:
        net_profit = _number(row.get("estimated_net_profit"))
    verified_source = str(row.get("practical_price_source") or "").upper() == "VERIFIED"
    if net_profit is not None and (row.get("valuation_display_safe") is True or verified_source):
        return {
            "available": True,
            "value": net_profit,
            "label": "Nettovinst efter kostnader",
            "basis": "verifierad marknadsevidens",
            "evidence_kind": "VERIFIED_SOLD",
        }

    asking = row.get("asking_price_opportunity") or {}
    asking_margin = _number(asking.get("net_margin"))
    if asking_margin is not None:
        return {
            "available": True,
            "value": asking_margin,
            "label": "Nettoscenario mot begärda priser",
            "basis": "aktiv jämförelse, inte genomförd försäljning",
            "evidence_kind": "ACTIVE_ASKING",
        }

    active_margin = _number(row.get("asking_net_margin"))
    if active_margin is not None:
        return {
            "available": True,
            "value": active_margin,
            "label": "Nettoscenario mot begärda priser",
            "basis": "aktiva jämförelser, inte genomförda försäljningar",
            "evidence_kind": "ACTIVE_ASKING",
        }

    return {
        "available": False,
        "value": None,
        "label": "Nettovinst",
        "basis": "ej beräkningsbar med tillräckligt underlag",
        "evidence_kind": "UNAVAILABLE",
    }


def known_negative_net_profit(row: dict | None) -> bool:
    """Whether the available economics prove that buying loses money."""
    summary = build_seller_net_profit_summary(row)
    return summary["available"] and summary["value"] < 0


def known_positive_net_profit(row: dict | None) -> bool:
    """Whether verified SOLD-backed economics prove a positive resale outcome."""
    summary = build_seller_net_profit_summary(row)
    return (
        summary["available"]
        and summary["value"] > 0
        and summary.get("evidence_kind") == "VERIFIED_SOLD"
    )


def positive_active_price_indication(row: dict | None) -> bool:
    """Whether active listings show a positive research-only scenario."""
    summary = build_seller_net_profit_summary(row)
    return (
        summary["available"]
        and summary["value"] > 0
        and summary.get("evidence_kind") == "ACTIVE_ASKING"
    )
