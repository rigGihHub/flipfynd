"""Capital-efficiency ranking for real-world card flipping.

v0.11.42 deliberately abstains when turnover cannot be supported by verified
sold evidence. It is a prioritisation layer, never a replacement for identity,
comp-quality or safety gates.
"""
from __future__ import annotations

def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def build_capital_efficiency(*, total_cost, net_profit, floor_profit, sale_probability,
                             liquidity_score, velocity):
    velocity = dict(velocity or {})
    days = velocity.get("expected_days")
    evidence = str(velocity.get("evidence") or "")
    if not isinstance(days, (int, float)) or days <= 0 or evidence != "verified_sold_velocity":
        return {
            "score": None, "label": "Ej bedömd", "profit_30d": None,
            "roi_30d_pct": None, "downside": None, "downside_pct": None,
            "expected_days": None, "evidence": evidence or "none",
            "note": "För lite verifierad data för att jämföra kapitalets fart.",
        }

    cost=max(0.0,_num(total_cost))
    profit=_num(net_profit)
    floor=_num(floor_profit)
    probability=max(0.0,min(100.0,_num(sale_probability)))
    liquidity=max(0.0,min(100.0,_num(liquidity_score)))
    profit30=profit*30.0/days
    roi30=(profit30/cost*100.0) if cost > 0 else None
    downside=min(0.0,floor)
    downside_pct=(downside/cost*100.0) if cost > 0 else None

    if cost <= 0 or profit <= 0 or roi30 is None:
        score=0.0
    else:
        # Capped components prevent tiny nominal buys or extreme ROI from
        # dominating. Downside is an explicit penalty.
        roi_component=min(100.0,max(0.0,roi30*2.0))
        profit_component=min(100.0,max(0.0,profit30/2.0))
        downside_penalty=min(35.0,abs(min(0.0,downside_pct or 0.0))*0.7)
        score=(roi_component*0.35 + profit_component*0.25 +
               probability*0.20 + liquidity*0.20 - downside_penalty)
        score=max(0.0,min(100.0,score))

    if score >= 80: label="Kapitalfavorit"
    elif score >= 65: label="Mycket effektiv"
    elif score >= 50: label="Effektiv"
    elif score >= 35: label="Måttlig"
    else: label="Svag"

    return {
        "score": round(score,1), "label": label,
        "profit_30d": round(profit30,1),
        "roi_30d_pct": round(roi30,1) if roi30 is not None else None,
        "downside": round(downside,1),
        "downside_pct": round(downside_pct,1) if downside_pct is not None else None,
        "expected_days": int(days), "evidence": evidence,
        "note": "Jämför vinst, kapitalbindning, säljchans, säljbarhet och nedsida. Ingen garanti.",
    }

def capital_efficiency_sort_key(item):
    ce=dict((item or {}).get("capital_efficiency") or {})
    score=ce.get("score")
    return (
        score is not None,
        _num(score, -1),
        _num((item or {}).get("net_profit_estimate")),
        _num((item or {}).get("deal_score")),
    )
