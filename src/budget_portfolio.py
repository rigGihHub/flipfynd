"""Budget-aware capital allocation for FlipFynd.

v0.11.75 compares combinations of candidates that already have a KÖP decision
and decision-grade Capital Efficiency. It never invents a target allocation,
never forces the full budget into the market, and never upgrades a candidate.
"""
from __future__ import annotations

from itertools import combinations


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _is_buy(item):
    d=str((item or {}).get("decision") or (item or {}).get("recommendation") or "").strip().upper()
    return d.startswith("KÖP") or d.startswith("KOP")


def _eligible(item):
    if not _is_buy(item):
        return False
    ce=dict((item or {}).get("capital_efficiency") or {})
    if ce.get("score") is None or _num(ce.get("profit_30d")) is None:
        return False
    cost=_num((item or {}).get("total_cost") or (item or {}).get("analysis_total_cost"))
    profit=_num((item or {}).get("net_profit_estimate"))
    floor=_num((item or {}).get("floor_profit_estimate"))
    days=_num((item or {}).get("flip_velocity_expected_days"))
    velocity_ok=(item or {}).get("flip_velocity_evidence")=="verified_sold_velocity"
    return (
        cost is not None and cost > 0
        and profit is not None and profit > 0
        and floor is not None
        and days is not None and days > 0
        and velocity_ok
    )


def _candidate_rank(item):
    ce=item.get("capital_efficiency") or {}
    return (
        _num(ce.get("score"), -1),
        _num(ce.get("profit_30d"), -1),
        _num(item.get("net_profit_estimate"), -1),
        str(item.get("titel") or ""),
    )


def _portfolio_metrics(items, budget):
    spent=sum(_num(x.get("total_cost") or x.get("analysis_total_cost"),0.0) for x in items)
    expected=sum(_num(x.get("net_profit_estimate"),0.0) for x in items)
    floor=sum(_num(x.get("floor_profit_estimate"),0.0) for x in items)
    profit30=sum(_num((x.get("capital_efficiency") or {}).get("profit_30d"),0.0) for x in items)
    roi30=(profit30/spent*100.0) if spent > 0 else None
    worst_loss=max(0.0,-floor)
    return {
        "selected":list(items),
        "spent":round(spent,2),
        "remaining":round(max(0.0,budget-spent),2),
        "expected_profit":round(expected,2),
        "floor_profit":round(floor,2),
        "worst_case_loss":round(worst_loss,2),
        "profit_30d":round(profit30,2),
        "roi_30d_pct":round(roi30,1) if roi30 is not None else None,
        "capital_usage_pct":round(spent/budget*100,1) if budget else 0.0,
    }


def _portfolio_key(portfolio):
    # Lexicographic, not a weighted synthetic score:
    # 1) verified SEK/30d, 2) stronger downside in SEK,
    # 3) expected SEK profit, 4) less capital if otherwise equal.
    return (
        portfolio["profit_30d"],
        portfolio["floor_profit"],
        portfolio["expected_profit"],
        -portfolio["spent"],
    )


def build_budget_portfolio(
    candidates,
    budget,
    *,
    max_single_share=None,
    max_cards=12,
    alternative_count=3,
):
    budget=max(0.0,_num(budget,0.0))
    if budget <= 0:
        return {"status":"NO_BUDGET","selected":[],"budget":budget,"spent":0.0,"remaining":budget}

    eligible=[dict(x) for x in (candidates or []) if _eligible(x)]
    if not eligible:
        return {
            "status":"NO_ELIGIBLE","selected":[],"budget":budget,"spent":0.0,"remaining":budget,
            "note":"Inga befintliga KÖP har samtidigt verifierad Capital Efficiency, verifierad sold-velocity och dokumenterat svagt scenario.",
        }

    # Keep exhaustive subset search bounded. The pool itself is ordered only by
    # already-existing Capital Efficiency evidence.
    pool=sorted(eligible,key=_candidate_rank,reverse=True)[:max(1,int(max_cards))]

    share_cap=None
    if max_single_share is not None:
        share=float(max(0.0,min(1.0,_num(max_single_share,1.0))))
        share_cap=budget*share

    portfolios=[]
    for size in range(1,len(pool)+1):
        for subset in combinations(pool,size):
            costs=[_num(x.get("total_cost") or x.get("analysis_total_cost"),0.0) for x in subset]
            spent=sum(costs)
            if spent > budget:
                continue
            if share_cap is not None and any(cost > share_cap for cost in costs):
                continue
            portfolios.append(_portfolio_metrics(subset,budget))

    if not portfolios:
        return {
            "status":"BUDGET_BLOCKED","selected":[],"budget":round(budget,2),"spent":0.0,"remaining":round(budget,2),
            "note":"Ingen verifierad kombination ryms inom budgeten" + (" och den uttryckliga koncentrationsgränsen." if share_cap is not None else "."),
        }

    portfolios.sort(key=_portfolio_key,reverse=True)
    best=portfolios[0]
    alternatives=portfolios[1:1+max(0,int(alternative_count))]

    return {
        "status":"READY",
        "selected":best["selected"],
        "budget":round(budget,2),
        "spent":best["spent"],
        "remaining":best["remaining"],
        "expected_profit":best["expected_profit"],
        "floor_profit":best["floor_profit"],
        "worst_case_loss":best["worst_case_loss"],
        "profit_30d":best["profit_30d"],
        "roi_30d_pct":best["roi_30d_pct"],
        "capital_usage_pct":best["capital_usage_pct"],
        "alternatives":alternatives,
        "eligible_count":len(eligible),
        "evaluated_combination_count":len(portfolios),
        "max_single_share":max_single_share,
        "budget_fill_forced":False,
        "selection_basis":[
            "högst verifierad nettovinst per 30 dagar",
            "därefter bättre summerat svagt utfall",
            "därefter högre trolig nettovinst",
            "därefter lägre bundet kapital",
        ],
        "note":"Jämför kombinationer av befintliga KÖP. Hela budgeten behöver inte användas. Ingen syntetisk portföljscore eller automatisk köp-uppgradering används.",
    }
