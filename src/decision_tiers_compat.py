"""Compatibility wrapper for decision tiers across partial/stale deploys.

Streamlit Cloud can briefly run a new app.py against an older imported module.
This wrapper preserves the verified-economic-edge gate even when the deployed
``build_decision_tiers`` implementation does not yet accept that keyword.
"""
from __future__ import annotations

import inspect


def _n(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _market_value(item):
    if item.get("valuation_display_safe") is not True:
        return None
    for key in ("market_value_estimate", "expected_resale", "estimated_market_value", "marknadsvarde"):
        if item.get(key) is not None:
            value = _n(item.get(key), -1)
            return value if value > 0 else None
    return None


def _supports_verified_economic_edge(item):
    decision = str(item.get("beslut") or item.get("decision") or item.get("recommendation") or "").upper()
    sold = int(_n(item.get("sold_comparable_count"), 0))
    identity_ok = bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG"}
    )
    total_cost = item.get("analysis_total_cost") if item.get("analysis_total_cost") is not None else item.get("total_cost")
    total_cost = _n(total_cost, -1)
    max_total = item.get("dynamic_max_total_price")
    if max_total is None:
        max_total = item.get("max_total_price")
    max_total = _n(max_total, 0)
    market_value = _market_value(item)
    return bool(
        (decision.startswith("KÖP") or decision.startswith("KOP"))
        and sold >= 2
        and identity_ok
        and market_value is not None
        and total_cost >= 0
        and max_total > 0
        and total_cost <= max_total
    )


def build_decision_tiers_compat(builder, candidates, *, total_limit=3, require_verified_economic_edge=False):
    """Call current builder, or safely adapt an older signature.

    The fallback deliberately pre-filters source candidates rather than merely
    hiding rows after ranking. That keeps the hard gate intact under a stale
    module and avoids promoting a non-edge card into Top 3.
    """
    rows = list(candidates or [])
    try:
        params = inspect.signature(builder).parameters
    except (TypeError, ValueError):
        params = {}

    if "require_verified_economic_edge" in params:
        return builder(
            rows,
            total_limit=total_limit,
            require_verified_economic_edge=require_verified_economic_edge,
        )

    gated = rows
    rejected_count = 0
    if require_verified_economic_edge:
        gated = [item for item in rows if _supports_verified_economic_edge(item)]
        rejected_count = len(rows) - len(gated)

    result = builder(gated, total_limit=total_limit)
    if not isinstance(result, dict):
        return result
    result = dict(result)
    result.setdefault("rejected_count", rejected_count)
    result.setdefault("rejection_reasons", {"legacy decision-tier module; compatibility gate applied": rejected_count} if rejected_count else {})
    note = str(result.get("note") or "").strip()
    compat_note = "Verified economic-edge gate applied through deploy compatibility wrapper."
    result["note"] = f"{note} {compat_note}".strip()
    return result
