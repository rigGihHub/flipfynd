"""Dynamic Max Bid for FlipFynd.

This module may only *tighten* an already calculated FlipFynd max price using
verified Exact Comp Hunter evidence. It never creates a buy ceiling from comp
prices alone and it never raises the existing max price.
"""
from __future__ import annotations

from typing import Any


def _num(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def build_dynamic_max_bid(
    *,
    base_max_total: object,
    shipping: object,
    comp_verdict: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return an evidence-adjusted max price without ever increasing base max.

    The existing FlipFynd ceiling remains the economic/risk ceiling. Exact sold
    comps are used only as an additional safety brake:
      * strong, recent and tight evidence -> retain almost all of base ceiling;
      * acceptable evidence -> larger safety haircut;
      * insufficient/spread evidence -> no dynamic max bid is issued.
    """
    verdict = dict(comp_verdict or {})
    base_total = _num(base_max_total)
    shipping_value = max(0.0, _num(shipping) or 0.0)

    result = {
        "available": False,
        "status": "Inte tillgängligt",
        "level": "låst",
        "max_total_price": None,
        "max_item_price": None,
        "base_max_total_price": round(base_total, 2) if base_total else None,
        "factor": None,
        "comp_price_cap": None,
        "reasons": [],
        "note": (
            "Dynamic Max Bid kan bara sänka ett redan beräknat FlipFynd-budtak. "
            "Det skapar aldrig ett budtak från comps och höjer aldrig maxpriset."
        ),
    }

    if base_total is None:
        result["reasons"].append("inget befintligt FlipFynd-budtak att justera")
        return result

    if not verdict.get("supports_safe_max_bid"):
        result["status"] = "Comp-underlaget är för svagt för dynamiskt budtak"
        result["level"] = "ej verifierat"
        result["reasons"].append("Comp Verdict stödjer inte ett säkert maxbud")
        return result

    score = int(verdict.get("score", 0) or 0)
    exact_count = int(verdict.get("exact_count", 0) or 0)
    recent_count = int(verdict.get("recent_exact_count", 0) or 0)
    spread = verdict.get("relative_spread")
    try:
        spread = float(spread) if spread is not None else None
    except (TypeError, ValueError):
        spread = None
    median_price = _num(verdict.get("price_median"))

    # Evidence factor controls how much of the existing risk-adjusted ceiling we
    # retain. It is deliberately conservative and can never exceed 1.0.
    if score >= 88 and exact_count >= 5 and recent_count >= 3 and (spread is None or spread <= 0.20):
        factor = 0.98
        comp_share = 0.84
        level = "mycket starkt"
        status = "Dynamiskt budtak – mycket starkt comp-stöd"
    elif score >= 80 and exact_count >= 4 and (spread is None or spread <= 0.30):
        factor = 0.95
        comp_share = 0.80
        level = "starkt"
        status = "Dynamiskt budtak – starkt comp-stöd"
    else:
        factor = 0.90
        comp_share = 0.75
        level = "försiktigt"
        status = "Dynamiskt budtak – försiktigt comp-stöd"

    evidence_ceiling = base_total * factor
    comp_cap = None
    if median_price is not None:
        comp_cap = median_price * comp_share
        evidence_ceiling = min(evidence_ceiling, comp_cap)

    dynamic_total = max(shipping_value, min(base_total, evidence_ceiling))
    dynamic_item = max(0.0, dynamic_total - shipping_value)

    result.update({
        "available": True,
        "status": status,
        "level": level,
        "max_total_price": round(dynamic_total, 2),
        "max_item_price": round(dynamic_item, 2),
        "factor": round(factor, 2),
        "comp_price_cap": round(comp_cap, 2) if comp_cap is not None else None,
    })
    result["reasons"].append(f"Comp Verdict {score}/100 med {exact_count} exakta avslut")
    if recent_count:
        result["reasons"].append(f"{recent_count} exakta avslut är högst 180 dagar gamla")
    if spread is not None:
        result["reasons"].append(f"relativ prisspridning {spread * 100:.0f}%")
    if median_price is not None:
        result["reasons"].append(
            f"median för exakta avslut {median_price:.0f} kr används som extra säkerhetsankare"
        )
    if dynamic_total < base_total:
        result["reasons"].append(
            f"befintligt budtak {base_total:.0f} kr sänks till {dynamic_total:.0f} kr av comp-säkerhetsmarginalen"
        )
    else:
        result["reasons"].append("comp-underlaget kräver ingen ytterligare sänkning av befintligt budtak")
    return result
