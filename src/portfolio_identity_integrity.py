"""Identity-integrity transparency for a selected FlipFynd portfolio.

The module reports how selected capital is distributed across existing Exact
Identity Gate states. It does not re-run identity inference, does not invent
missing evidence, and does not change portfolio ranking or buy decisions.
"""
from __future__ import annotations
from collections import defaultdict


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _cost(item):
    return _num((item or {}).get("total_cost") or (item or {}).get("analysis_total_cost"))


def _status(item):
    raw=str((item or {}).get("exact_identity_gate_status") or "").strip().upper()
    if raw in {"VERIFIERAD","SÖKBAR","GRANSKA","LÅST"}:
        return raw
    return "OKÄND"


def build_portfolio_identity_integrity(selected):
    rows=[]
    for item in (selected or []):
        cost=_cost(item)
        if cost is None or cost <= 0:
            return {
                "status":"INSUFFICIENT_DATA",
                "available":False,
                "note":"Alla valda kort måste ha faktisk kapitalbindning för identitetsanalys.",
            }
        rows.append({
            "title":item.get("titel") or "Okänt kort",
            "cost":cost,
            "identity_status":_status(item),
            "identity_score":_num(item.get("exact_identity_gate_score")),
            "supports_exact_comp_search":bool(item.get("exact_identity_gate_supports_exact_comp_search")),
            "supports_dynamic_max_bid":bool(item.get("exact_identity_gate_supports_dynamic_max_bid")),
            "identity_label":item.get("exact_identity_gate_label"),
            "url":item.get("lank"),
        })

    if not rows:
        return {
            "status":"NO_SELECTION",
            "available":False,
            "note":"Ingen vald portfölj att analysera.",
        }

    total=sum(r["cost"] for r in rows)
    grouped=defaultdict(lambda:{"capital":0.0,"card_count":0})
    for row in rows:
        g=grouped[row["identity_status"]]
        g["capital"] += row["cost"]
        g["card_count"] += 1

    order=["VERIFIERAD","SÖKBAR","GRANSKA","LÅST","OKÄND"]
    groups=[]
    for status in order:
        if status not in grouped:
            continue
        amount=grouped[status]["capital"]
        groups.append({
            "status":status,
            "capital":round(amount,2),
            "capital_share_pct":round(amount/total*100.0,1) if total > 0 else None,
            "card_count":grouped[status]["card_count"],
        })

    exact_capital=sum(r["cost"] for r in rows if r["supports_exact_comp_search"])
    dynamic_capital=sum(r["cost"] for r in rows if r["supports_dynamic_max_bid"])
    unresolved_capital=sum(
        r["cost"] for r in rows
        if r["identity_status"] in {"GRANSKA","LÅST","OKÄND"}
    )

    details=sorted(rows,key=lambda r:(-r["cost"],str(r["title"])))
    for row in details:
        row["capital_share_pct"]=round(row["cost"]/total*100.0,1) if total > 0 else None
        row["cost"]=round(row["cost"],2)

    return {
        "status":"READY",
        "available":True,
        "card_count":len(rows),
        "total_capital":round(total,2),
        "identity_groups":groups,
        "details":details,
        "exact_comp_search_capital":round(exact_capital,2),
        "exact_comp_search_capital_pct":round(exact_capital/total*100.0,1) if total > 0 else None,
        "dynamic_max_bid_capital":round(dynamic_capital,2),
        "dynamic_max_bid_capital_pct":round(dynamic_capital/total*100.0,1) if total > 0 else None,
        "unresolved_identity_capital":round(unresolved_capital,2),
        "unresolved_identity_capital_pct":round(unresolved_capital/total*100.0,1) if total > 0 else None,
        "identity_inferred":False,
        "risk_score_created":False,
        "ranking_changed":False,
        "note":"Visar bara befintliga Exact Identity Gate-statusar och kapitalandelar. Inga saknade identitetsfält gissas och analysen ändrar inte portföljurvalet.",
    }
