"""Validate Capital Efficiency against completed Flip Journal outcomes.

Only rows where the score was actually captured at decision time are included.
Legacy rows without the signal are explicitly excluded instead of backfilled.
"""
from __future__ import annotations
from statistics import median

MIN_COHORT_SAMPLE = 5
MIN_REVIEW_SAMPLE = 20

def _num(v):
    if v in (None, ""): return None
    try: return float(v)
    except (TypeError, ValueError): return None

def _completed(rows):
    out=[]
    for r in rows or []:
        if r.get("status") != "sålt": continue
        if _num(r.get("actual_net_profit")) is None: continue
        if _num(r.get("capital_efficiency_score_at_capture")) is None: continue
        out.append(r)
    return out

def _summary(rows):
    rows=list(rows)
    profits=[_num(r.get("actual_net_profit")) for r in rows]
    profits=[x for x in profits if x is not None]
    rois=[_num(r.get("actual_roi_pct")) for r in rows]
    rois=[x for x in rois if x is not None]
    days=[r.get("days_to_sell") for r in rows if isinstance(r.get("days_to_sell"), int)]
    p30=[]
    for r in rows:
        profit=_num(r.get("actual_net_profit"))
        d=r.get("days_to_sell")
        if profit is not None and isinstance(d,int):
            p30.append(profit*30.0/max(1,d))
    return {
        "count":len(rows),
        "win_rate_pct": round(sum(1 for x in profits if x>0)/len(profits)*100,1) if profits else None,
        "median_actual_profit": round(median(profits),2) if profits else None,
        "median_actual_roi_pct": round(median(rois),1) if rois else None,
        "median_days_to_sell": round(median(days),1) if days else None,
        "median_actual_profit_30d": round(median(p30),1) if p30 else None,
        "enough_for_pattern": len(rows) >= MIN_COHORT_SAMPLE,
    }

def build_capital_efficiency_validation(rows):
    all_rows=list(rows or [])
    completed=_completed(all_rows)
    high=[r for r in completed if float(r["capital_efficiency_score_at_capture"]) >= 65]
    lower=[r for r in completed if float(r["capital_efficiency_score_at_capture"]) < 65]
    hs, ls=_summary(high), _summary(lower)

    direction=None
    if hs["enough_for_pattern"] and ls["enough_for_pattern"]:
        hp=hs.get("median_actual_profit_30d")
        lp=ls.get("median_actual_profit_30d")
        if hp is not None and lp is not None:
            direction = "supports" if hp > lp else ("mixed" if hp == lp else "challenges")

    return {
        "captured_completed_count":len(completed),
        "legacy_or_unscored_completed_count":sum(
            1 for r in all_rows
            if r.get("status")=="sålt"
            and _num(r.get("actual_net_profit")) is not None
            and _num(r.get("capital_efficiency_score_at_capture")) is None
        ),
        "high":hs,
        "lower":ls,
        "direction":direction,
        "supports_manual_review": len(completed) >= MIN_REVIEW_SAMPLE and hs["enough_for_pattern"] and ls["enough_for_pattern"],
        "min_review_sample":MIN_REVIEW_SAMPLE,
        "automatic_model_changes":False,
        "note":"Jämför endast verkliga avslut där Capital Efficiency faktiskt sparades vid köptillfället. Äldre poster fylls inte i i efterhand.",
    }
