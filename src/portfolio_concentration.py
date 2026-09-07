"""Transparent concentration analysis for a selected FlipFynd portfolio.

This module describes where selected capital is concentrated. It does not
declare any concentration level safe/unsafe, does not impose limits, and does
not change portfolio ranking or buy decisions.
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


def _identity_family(item):
    direct=(item or {}).get("card_identity_family")
    if direct:
        return str(direct)
    identity=(item or {}).get("card_identity")
    if isinstance(identity, dict):
        family=identity.get("card_identity_family") or identity.get("family") or identity.get("set_name")
        if family:
            return str(family)
    return None


def _group(rows, key, unknown_label):
    capital=defaultdict(float)
    count=defaultdict(int)
    for row in rows:
        label=row.get(key) or unknown_label
        capital[str(label)] += row["cost"]
        count[str(label)] += 1
    total=sum(capital.values())
    groups=[]
    for label, amount in capital.items():
        groups.append({
            "label":label,
            "capital":round(amount,2),
            "capital_share_pct":round(amount/total*100.0,1) if total > 0 else None,
            "card_count":count[label],
        })
    groups.sort(key=lambda x:(-x["capital"],str(x["label"])))
    return groups


def build_portfolio_concentration(selected):
    rows=[]
    for item in (selected or []):
        cost=_cost(item)
        if cost is None or cost <= 0:
            return {
                "status":"INSUFFICIENT_DATA",
                "available":False,
                "note":"Alla valda kort måste ha faktisk kapitalbindning för koncentrationsanalys.",
            }
        rows.append({
            "title":item.get("titel") or "Okänt kort",
            "cost":cost,
            "player":item.get("player_name"),
            "set_family":_identity_family(item),
            "sport":item.get("sport"),
            "url":item.get("lank"),
        })

    if not rows:
        return {"status":"NO_SELECTION","available":False,"note":"Ingen vald portfölj att analysera."}

    total=sum(r["cost"] for r in rows)
    positions=sorted(rows,key=lambda r:(-r["cost"],str(r["title"])))
    for row in positions:
        row["capital_share_pct"]=round(row["cost"]/total*100.0,1) if total > 0 else None
        row["cost"]=round(row["cost"],2)

    top1=positions[0]["capital_share_pct"] if positions else None
    top2_capital=sum(r["cost"] for r in positions[:2])
    top2=round(top2_capital/total*100.0,1) if total > 0 else None

    players=_group(rows,"player","Okänd spelare")
    sets=_group(rows,"set_family","Okänt set/program")
    sports=_group(rows,"sport","Okänd sport")

    return {
        "status":"READY",
        "available":True,
        "card_count":len(rows),
        "total_capital":round(total,2),
        "positions":positions,
        "player_groups":players,
        "set_groups":sets,
        "sport_groups":sports,
        "largest_position_share_pct":top1,
        "top_two_position_share_pct":top2,
        "unique_player_count":len([g for g in players if g["label"]!="Okänd spelare"]),
        "unique_set_count":len([g for g in sets if g["label"]!="Okänt set/program"]),
        "unique_sport_count":len([g for g in sports if g["label"]!="Okänd sport"]),
        "unknown_player_capital_pct":next((g["capital_share_pct"] for g in players if g["label"]=="Okänd spelare"),0.0),
        "unknown_set_capital_pct":next((g["capital_share_pct"] for g in sets if g["label"]=="Okänt set/program"),0.0),
        "limits_applied":False,
        "risk_band_created":False,
        "ranking_changed":False,
        "note":"Visar faktisk koncentration av valt kapital. Inga gränsvärden används för att kalla koncentrationen låg, medel eller hög och analysen ändrar inte urvalet.",
    }
