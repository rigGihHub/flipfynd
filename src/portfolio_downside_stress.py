"""Deterministic downside stress test for a selected FlipFynd portfolio.

The stress test does not estimate probabilities, correlations or market-wide
shocks. It only recombines each selected card's already documented likely and
floor profit outcomes into transparent portfolio scenarios.
"""
from __future__ import annotations


def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_portfolio_downside_stress(selected, *, budget=None):
    rows=[]
    for item in (selected or []):
        cost=_num(item.get("total_cost") or item.get("analysis_total_cost"))
        likely=_num(item.get("net_profit_estimate"))
        floor=_num(item.get("floor_profit_estimate"))
        if cost is None or cost <= 0 or likely is None or floor is None:
            return {
                "status":"INSUFFICIENT_DATA",
                "available":False,
                "note":"Alla valda kort måste ha faktisk kapitalbindning samt dokumenterat troligt och svagt vinstutfall.",
            }
        rows.append({
            "title":item.get("titel") or "Okänt kort",
            "cost":cost,
            "likely_profit":likely,
            "floor_profit":floor,
            "shock_damage":likely-floor,
            "url":item.get("lank"),
        })

    if not rows:
        return {
            "status":"NO_SELECTION",
            "available":False,
            "note":"Ingen vald portfölj att stresstesta.",
        }

    spent=sum(r["cost"] for r in rows)
    likely_total=sum(r["likely_profit"] for r in rows)
    all_floor=sum(r["floor_profit"] for r in rows)
    all_floor_damage=likely_total-all_floor
    budget_value=_num(budget)
    capital_loss=max(0.0,-all_floor)
    loss_vs_spent=(capital_loss/spent*100.0) if spent > 0 else None
    loss_vs_budget=(capital_loss/budget_value*100.0) if budget_value and budget_value > 0 else None

    single_shocks=[]
    for row in rows:
        stressed_total=likely_total-row["likely_profit"]+row["floor_profit"]
        single_shocks.append({
            "title":row["title"],
            "portfolio_profit":round(stressed_total,2),
            "damage_vs_likely":round(row["shock_damage"],2),
            "card_floor_profit":round(row["floor_profit"],2),
            "url":row["url"],
        })
    single_shocks.sort(key=lambda x:(-x["damage_vs_likely"],str(x["title"])))

    largest=max(rows,key=lambda r:(r["cost"],str(r["title"])))
    largest_share=(largest["cost"]/spent*100.0) if spent > 0 else None

    return {
        "status":"READY",
        "available":True,
        "card_count":len(rows),
        "spent":round(spent,2),
        "likely_portfolio_profit":round(likely_total,2),
        "all_floor_portfolio_profit":round(all_floor,2),
        "all_floor_damage_vs_likely":round(all_floor_damage,2),
        "all_floor_capital_loss":round(capital_loss,2),
        "all_floor_loss_pct_of_spent":round(loss_vs_spent,1) if loss_vs_spent is not None else None,
        "all_floor_loss_pct_of_budget":round(loss_vs_budget,1) if loss_vs_budget is not None else None,
        "single_card_shocks":single_shocks,
        "largest_capital_position":{
            "title":largest["title"],
            "cost":round(largest["cost"],2),
            "share_of_selected_capital_pct":round(largest_share,1) if largest_share is not None else None,
        },
        "scenario_labels":{
            "likely":"Alla kort på befintligt troligt utfall",
            "single_floor":"Ett kort i taget på sitt befintliga floor-utfall",
            "all_floor":"Alla kort samtidigt på sina befintliga floor-utfall",
        },
        "probabilities_used":False,
        "correlations_assumed":False,
        "ranking_changed":False,
        "note":"Stresstestet kombinerar bara redan dokumenterade likely/floor-utfall. Det säger inte hur sannolikt ett scenario är och antar ingen korrelation mellan korten.",
    }
