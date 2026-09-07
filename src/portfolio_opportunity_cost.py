"""Opportunity-cost transparency for an already selected FlipFynd portfolio.

No return is assigned to idle cash. The module only compares the selected
portfolio with other already verified, budget-feasible card combinations and
shows the verified profit-rate sacrificed by choosing a slower alternative.
"""
from __future__ import annotations


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _card_cost(item):
    return _num((item or {}).get("total_cost") or (item or {}).get("analysis_total_cost"))


def _profit30(item):
    return _num(((item or {}).get("capital_efficiency") or {}).get("profit_30d"))


def _verified_candidate(item):
    cost=_card_cost(item)
    p30=_profit30(item)
    ce=((item or {}).get("capital_efficiency") or {}).get("score")
    floor=_num((item or {}).get("floor_profit_estimate"))
    decision=str((item or {}).get("decision") or (item or {}).get("recommendation") or "").upper()
    return (
        (decision.startswith("KÖP") or decision.startswith("KOP"))
        and cost is not None and cost > 0
        and p30 is not None
        and ce is not None
        and floor is not None
        and (item or {}).get("flip_velocity_evidence")=="verified_sold_velocity"
    )


def build_portfolio_opportunity_cost(portfolio, candidates):
    portfolio=dict(portfolio or {})
    if portfolio.get("status")!="READY":
        return {
            "status":"NO_PORTFOLIO",
            "available":False,
            "note":"Ingen färdig verifierad portfölj att jämföra.",
        }

    selected=list(portfolio.get("selected") or [])
    budget=_num(portfolio.get("budget"),0.0) or 0.0
    spent=_num(portfolio.get("spent"),0.0) or 0.0
    remaining=max(0.0,_num(portfolio.get("remaining"),budget-spent) or 0.0)
    best_p30=_num(portfolio.get("profit_30d"))
    if best_p30 is None:
        return {
            "status":"INSUFFICIENT_DATA",
            "available":False,
            "note":"Verifierad portföljvinst per 30 dagar saknas.",
        }

    selected_ids={str(x.get("lank") or x.get("url") or x.get("id") or x.get("titel") or "") for x in selected}
    verified=[x for x in (candidates or []) if _verified_candidate(x)]
    unselected=[
        x for x in verified
        if str(x.get("lank") or x.get("url") or x.get("id") or x.get("titel") or "") not in selected_ids
    ]

    affordable_reserve=[]
    for item in unselected:
        cost=_card_cost(item)
        if cost is not None and cost <= remaining:
            affordable_reserve.append({
                "title":item.get("titel") or "Okänt kort",
                "cost":round(cost,2),
                "profit_30d":round(_profit30(item),2),
                "url":item.get("lank"),
            })
    affordable_reserve.sort(key=lambda x:(-x["profit_30d"],x["cost"],str(x["title"])))

    alternatives=[]
    for alt in (portfolio.get("alternatives") or []):
        alt_p30=_num(alt.get("profit_30d"))
        alt_spent=_num(alt.get("spent"))
        if alt_p30 is None or alt_spent is None:
            continue
        sacrifice=best_p30-alt_p30
        alternatives.append({
            "titles":[str(x.get("titel") or "Okänt kort") for x in (alt.get("selected") or [])],
            "spent":round(alt_spent,2),
            "profit_30d":round(alt_p30,2),
            "profit_30d_sacrificed":round(max(0.0,sacrifice),2),
            "capital_difference":round(alt_spent-spent,2),
            "floor_profit":_num(alt.get("floor_profit")),
        })

    selected_efficiency=[]
    for item in selected:
        cost=_card_cost(item)
        p30=_profit30(item)
        if cost is None or cost <= 0 or p30 is None:
            continue
        selected_efficiency.append({
            "title":item.get("titel") or "Okänt kort",
            "cost":round(cost,2),
            "profit_30d":round(p30,2),
            "profit_30d_per_100_capital":round(p30/cost*100.0,2),
            "url":item.get("lank"),
        })
    selected_efficiency.sort(key=lambda x:(x["profit_30d_per_100_capital"],str(x["title"])))

    if affordable_reserve:
        reserve_status="VERIFIED_OPTION_EXISTS"
        reserve_note=(
            "Det finns minst ett ytterligare verifierat KÖP som ryms i reservkapitalet. "
            "Eftersom huvudportföljen redan är optimerad inom sin sökpool bör detta granskas som en möjlig pool-/max_cards-begränsning, inte automatiskt köpas."
        )
    else:
        reserve_status="HOLD_CASH"
        reserve_note=(
            "Ingen annan verifierad KÖP-kandidat i nuvarande underlag ryms i det kvarvarande kapitalet. "
            "FlipFynd sätter därför ingen alternativ avkastning på kontanterna."
        )

    return {
        "status":"READY",
        "available":True,
        "budget":round(budget,2),
        "spent":round(spent,2),
        "remaining":round(remaining,2),
        "selected_profit_30d":round(best_p30,2),
        "reserve_status":reserve_status,
        "reserve_note":reserve_note,
        "affordable_verified_unselected":affordable_reserve,
        "alternative_portfolios":alternatives,
        "selected_capital_efficiency":selected_efficiency,
        "slowest_selected":selected_efficiency[0] if selected_efficiency else None,
        "idle_cash_return_assumed":False,
        "ranking_changed":False,
        "note":"Opportunity cost visas endast mot faktiska verifierade alternativa kort/kombinationer. Kontanter får ingen antagen avkastning och inga framtida fynd modelleras.",
    }
