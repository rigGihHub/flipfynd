from src.budget_portfolio import build_budget_portfolio

def c(name,cost,profit,score,decision="KÖP",floor=10,p30=50,days=15):
    return {
        "titel":name,"decision":decision,"total_cost":cost,
        "analysis_total_cost":cost,"net_profit_estimate":profit,
        "floor_profit_estimate":floor,
        "flip_velocity_expected_days":days,
        "flip_velocity_evidence":"verified_sold_velocity",
        "capital_efficiency":{"score":score,"profit_30d":p30},
    }

def test_only_existing_buy_candidates_are_eligible():
    r=build_budget_portfolio([c("a",100,50,80,"KANSKE"),c("b",100,40,70)],500)
    assert [x["titel"] for x in r["selected"]]==["b"]

def test_unscored_capital_candidate_is_excluded():
    x=c("a",100,50,80); x["capital_efficiency"]["score"]=None
    assert build_budget_portfolio([x],500)["status"]=="NO_ELIGIBLE"

def test_unverified_velocity_is_excluded():
    x=c("a",100,50,80); x["flip_velocity_evidence"]="heuristic"
    assert build_budget_portfolio([x],500)["status"]=="NO_ELIGIBLE"

def test_missing_downside_abstains():
    x=c("a",100,50,80,floor=None)
    assert build_budget_portfolio([x],500)["status"]=="NO_ELIGIBLE"

def test_respects_budget():
    r=build_budget_portfolio([c("a",200,70,90,p30=80),c("b",200,60,80,p30=70)],500)
    assert r["spent"]<=500 and len(r["selected"])==2

def test_default_has_no_arbitrary_concentration_cap():
    r=build_budget_portfolio([c("a",600,300,95,p30=120)],1000)
    assert r["status"]=="READY" and r["spent"]==600

def test_explicit_concentration_cap_is_respected():
    r=build_budget_portfolio([c("a",600,300,95,p30=120)],1000,max_single_share=.45)
    assert r["status"]=="BUDGET_BLOCKED"

def test_combination_beats_single_card_on_verified_profit_rate():
    cards=[c("a",200,70,90,p30=90),c("b",200,60,80,p30=80),c("c",450,200,95,p30=150)]
    r=build_budget_portfolio(cards,450)
    assert [x["titel"] for x in r["selected"]]==["a","b"]
    assert r["profit_30d"]==170

def test_downside_breaks_equal_profit_rate_tie():
    cards=[c("safer",200,50,80,floor=5,p30=100),c("riskier",200,80,90,floor=-40,p30=100)]
    r=build_budget_portfolio(cards,200)
    assert r["selected"][0]["titel"]=="safer"

def test_does_not_force_full_budget():
    r=build_budget_portfolio([c("a",200,50,80,p30=100)],1000)
    assert r["spent"]==200 and r["remaining"]==800
    assert r["budget_fill_forced"] is False

def test_returns_alternative_combinations():
    r=build_budget_portfolio([c("a",100,30,90,p30=60),c("b",100,30,80,p30=55),c("c",100,30,70,p30=50)],200)
    assert r["alternatives"]
    assert r["evaluated_combination_count"]>=3

def test_summary_math():
    r=build_budget_portfolio([c("a",100,50,90,floor=-10,p30=100),c("b",150,70,80,floor=5,p30=80)],500)
    assert r["spent"]==250 and r["expected_profit"]==120
    assert r["floor_profit"]==-5 and r["profit_30d"]==180
