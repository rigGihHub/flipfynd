"""Segment Yield Learning.

Observes which already-analysed market segments produce verified buys, promising
candidates, safe valuations and exact identities. It is intentionally
observational: it never changes BUY rules, valuation, risk, max price or analysis
budgets automatically.
"""
from __future__ import annotations
from collections import defaultdict

from src.segment_discovery_coverage import price_band, sale_type


def _n(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _object_type(item):
    return "lot" if (item or {}).get("is_lot") or (item or {}).get("lot_count") else "single"


def _certainty(item):
    for key in ("ranking_confidence_score","deal_confidence_score","confidence","valuation_confidence_score"):
        if (item or {}).get(key) is not None:
            return max(0.0,min(100.0,_n(item.get(key))))
    return 0.0


def _verified(item):
    decision=str(
        (item or {}).get("beslut")
        or (item or {}).get("decision")
        or (item or {}).get("recommendation")
        or ""
    ).upper()
    sold=int(_n((item or {}).get("sold_comparable_count"),0))
    identity_ok=bool(
        (item or {}).get("exact_identity_gate_supports_exact_comp_search")
        or (item or {}).get("exact_identity_gate_status") in {"READY","EXACT","STRONG"}
    )
    return bool(
        (decision.startswith("KÖP") or decision.startswith("KOP"))
        and _certainty(item) >= 60
        and sold >= 2
        and identity_ok
        and (item or {}).get("valuation_display_safe") is True
    )


def _segment(item, budget):
    price=(item or {}).get("pris")
    if price is None:
        price=(item or {}).get("analysis_total_cost")
    return (
        price_band(price,budget),
        sale_type(item),
        _object_type(item),
    )


def build_segment_yield_report(items, *, budget, minimum_hits=8):
    groups=defaultdict(lambda:{
        "hits":0,
        "verified":0,
        "promising":0,
        "safe_value":0,
        "exact_identity":0,
        "certainty_sum":0.0,
        "potential_sum":0.0,
    })

    for item in items or []:
        if not isinstance(item,dict):
            continue
        seg=_segment(item,budget)
        if seg[0]=="unknown":
            continue
        g=groups[seg]
        g["hits"]+=1
        certainty=_certainty(item)
        potential=max(0.0,min(100.0,_n(item.get("deal_score"))))
        g["certainty_sum"]+=certainty
        g["potential_sum"]+=potential
        if _verified(item):
            g["verified"]+=1
        if potential>=55:
            g["promising"]+=1
        if item.get("valuation_display_safe") is True:
            g["safe_value"]+=1
        if (
            item.get("exact_identity_gate_supports_exact_comp_search")
            or item.get("exact_identity_gate_status") in {"READY","EXACT","STRONG"}
        ):
            g["exact_identity"]+=1

    rows=[]
    for seg,g in groups.items():
        hits=g["hits"]
        if hits < minimum_hits:
            status="OTILLRÄCKLIGT_UNDERLAG"
        elif g["verified"]>0:
            status="VERIFIERAD_YIELD_OBSERVERAD"
        elif g["promising"]>0 or g["safe_value"]>0:
            status="LOVANDE_YIELD_OBSERVERAD"
        else:
            status="LÅG_YIELD_OBSERVERAD"

        rows.append({
            "segment":"/".join(seg),
            "price_band":seg[0],
            "sale_type":seg[1],
            "object_type":seg[2],
            "hits":hits,
            "verified":g["verified"],
            "promising":g["promising"],
            "safe_value":g["safe_value"],
            "exact_identity":g["exact_identity"],
            "verified_rate_observed":round(g["verified"]/hits*100,1) if hits else None,
            "promising_rate_observed":round(g["promising"]/hits*100,1) if hits else None,
            "safe_value_rate_observed":round(g["safe_value"]/hits*100,1) if hits else None,
            "avg_certainty":round(g["certainty_sum"]/hits,1) if hits else None,
            "avg_potential":round(g["potential_sum"]/hits,1) if hits else None,
            "evidence_status":status,
        })

    rows.sort(
        key=lambda r:(
            r["verified"],
            r["promising"],
            r["safe_value"],
            r["exact_identity"],
            r["hits"],
        ),
        reverse=True,
    )

    return {
        "rows":rows,
        "segment_count":len(rows),
        "total_hits":sum(r["hits"] for r in rows),
        "minimum_hits":int(minimum_hits),
        "can_change_buy_rules":False,
        "can_change_analysis_budget":False,
        "can_auto_tune":False,
        "creates_new_score":False,
        "creates_new_decision":False,
        "note":"Observerad segment-yield. Rapporten mäter utfallet av befintlig analys men ändrar inte automatiskt hur FlipFynd väljer eller bedömer kort.",
    }


def best_observed_segments(report, limit=3):
    rows=[
        r for r in (report or {}).get("rows",[])
        if r.get("evidence_status") != "OTILLRÄCKLIGT_UNDERLAG"
    ]
    return rows[:max(0,int(limit))]
