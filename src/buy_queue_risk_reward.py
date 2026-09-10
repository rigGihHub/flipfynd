"""Risk/reward scenarios for already-approved top buy candidates.

This module deliberately exposes numeric downside rather than invented low/medium/high
capital-risk labels. No empirical calibration currently supports those labels.
"""
from __future__ import annotations


def _n(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_risk_reward(item):
    total = _n(item.get("analysis_total_cost") or item.get("total_cost"))
    floor_profit = _n(item.get("floor_profit_estimate"))
    likely_profit = _n(item.get("net_profit_estimate"))
    best_resale = _n(item.get("best_case_resale"))
    expected_resale = _n(item.get("expected_resale"))

    if total in (None, 0) or likely_profit is None:
        return {"status": "INSUFFICIENT_DATA"}

    downside_pct = (
        round(max(0.0, -floor_profit) / total * 100, 1)
        if floor_profit is not None
        else None
    )
    likely_roi = round(likely_profit / total * 100, 1)
    floor_roi = round(floor_profit / total * 100, 1) if floor_profit is not None else None

    return {
        "status": "READY",
        "weak_profit": floor_profit,
        "likely_profit": likely_profit,
        "strong_profit": None,
        "strong_resale": best_resale,
        "expected_resale": expected_resale,
        "floor_roi_pct": floor_roi,
        "likely_roi_pct": likely_roi,
        "capital_downside_pct": downside_pct,
        "risk_band": None,
        "risk_band_supported": False,
        "note": (
            "Kapitalrisk visas som faktisk beräknad nedsida i procent. "
            "FlipFynd använder inte låg/medel/hög-etiketter utan empiriskt stöd."
        ),
    }


def build_queue_risk_reward(queue, candidates):
    by_title = {str(x.get("titel") or ""): x for x in (candidates or [])}
    rows = []
    for pick in (queue or {}).get("picks", []):
        rr = build_risk_reward(by_title.get(str(pick.get("title") or "")) or {})
        rows.append({"rank": pick.get("rank"), "title": pick.get("title"), "risk_reward": rr})
    return {"rows": rows}
