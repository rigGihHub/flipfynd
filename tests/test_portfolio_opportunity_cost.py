from src.portfolio_opportunity_cost import build_portfolio_opportunity_cost

def card(name,cost,p30,floor=0):
    return {
        "titel":name,"decision":"KÖP","total_cost":cost,"floor_profit_estimate":floor,
        "flip_velocity_evidence":"verified_sold_velocity",
        "capital_efficiency":{"score":80,"profit_30d":p30},
    }

def portfolio():
    a=card("A",200,100)
    return {
        "status":"READY","budget":500,"spent":200,"remaining":300,
        "profit_30d":100,"selected":[a],
        "alternatives":[
            {"selected":[card("B",250,80)],"spent":250,"profit_30d":80,"floor_profit":5}
        ],
    }

def test_no_portfolio():
    assert build_portfolio_opportunity_cost({},[])["status"]=="NO_PORTFOLIO"

def test_alternative_sacrifice_is_factual_difference():
    r=build_portfolio_opportunity_cost(portfolio(),[card("A",200,100),card("B",250,80)])
    assert r["alternative_portfolios"][0]["profit_30d_sacrificed"]==20

def test_idle_cash_gets_no_assumed_return():
    r=build_portfolio_opportunity_cost(portfolio(),[card("A",200,100)])
    assert r["idle_cash_return_assumed"] is False
    assert r["reserve_status"]=="HOLD_CASH"

def test_affordable_verified_unselected_is_exposed():
    r=build_portfolio_opportunity_cost(portfolio(),[card("A",200,100),card("B",250,80)])
    assert r["reserve_status"]=="VERIFIED_OPTION_EXISTS"
    assert r["affordable_verified_unselected"][0]["title"]=="B"

def test_unverified_candidate_not_counted_as_reserve_option():
    b=card("B",250,80); b["flip_velocity_evidence"]="heuristic"
    r=build_portfolio_opportunity_cost(portfolio(),[card("A",200,100),b])
    assert r["reserve_status"]=="HOLD_CASH"

def test_slowest_selected_uses_profit_rate_per_capital():
    a=card("A",100,60); b=card("B",300,90)
    p={"status":"READY","budget":500,"spent":400,"remaining":100,"profit_30d":150,"selected":[a,b],"alternatives":[]}
    r=build_portfolio_opportunity_cost(p,[a,b])
    assert r["slowest_selected"]["title"]=="B"
    assert r["slowest_selected"]["profit_30d_per_100_capital"]==30.0

def test_never_changes_ranking():
    r=build_portfolio_opportunity_cost(portfolio(),[card("A",200,100)])
    assert r["ranking_changed"] is False
