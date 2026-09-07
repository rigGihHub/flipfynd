from src.portfolio_downside_stress import build_portfolio_downside_stress

def card(name,cost,likely,floor):
    return {"titel":name,"total_cost":cost,"net_profit_estimate":likely,"floor_profit_estimate":floor,"lank":"https://example.com"}

def test_empty():
    r=build_portfolio_downside_stress([])
    assert r["status"]=="NO_SELECTION" and not r["available"]

def test_missing_floor_fails_closed():
    x=card("A",100,40,-10); x["floor_profit_estimate"]=None
    assert build_portfolio_downside_stress([x])["status"]=="INSUFFICIENT_DATA"

def test_all_floor_math():
    r=build_portfolio_downside_stress([card("A",100,40,-20),card("B",200,70,10)],budget=500)
    assert r["likely_portfolio_profit"]==110
    assert r["all_floor_portfolio_profit"]==-10
    assert r["all_floor_damage_vs_likely"]==120
    assert r["all_floor_capital_loss"]==10

def test_single_card_shock_uses_existing_floor_only():
    r=build_portfolio_downside_stress([card("A",100,40,-20),card("B",200,70,10)])
    a=next(x for x in r["single_card_shocks"] if x["title"]=="A")
    assert a["portfolio_profit"]==50
    assert a["damage_vs_likely"]==60

def test_single_shocks_rank_by_actual_damage():
    r=build_portfolio_downside_stress([card("A",100,40,30),card("B",200,70,-30)])
    assert r["single_card_shocks"][0]["title"]=="B"

def test_largest_capital_position_is_descriptive():
    r=build_portfolio_downside_stress([card("A",100,40,10),card("B",300,70,20)])
    assert r["largest_capital_position"]["title"]=="B"
    assert r["largest_capital_position"]["share_of_selected_capital_pct"]==75.0

def test_no_probability_or_correlation_is_invented():
    r=build_portfolio_downside_stress([card("A",100,40,-20)])
    assert r["probabilities_used"] is False
    assert r["correlations_assumed"] is False

def test_budget_loss_share_is_descriptive():
    r=build_portfolio_downside_stress([card("A",100,40,-20)],budget=400)
    assert r["all_floor_loss_pct_of_budget"]==5.0
    assert r["all_floor_loss_pct_of_spent"]==20.0

def test_stress_test_never_changes_ranking():
    r=build_portfolio_downside_stress([card("A",100,40,-20)])
    assert r["ranking_changed"] is False
