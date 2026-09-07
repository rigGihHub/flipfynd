from src.portfolio_identity_integrity import build_portfolio_identity_integrity

def card(name,cost,status="VERIFIERAD",exact=True,dynamic=True,score=95):
    return {
        "titel":name,"total_cost":cost,
        "exact_identity_gate_status":status,
        "exact_identity_gate_score":score,
        "exact_identity_gate_supports_exact_comp_search":exact,
        "exact_identity_gate_supports_dynamic_max_bid":dynamic,
        "exact_identity_gate_label":"label",
    }

def test_empty():
    assert build_portfolio_identity_integrity([])["status"]=="NO_SELECTION"

def test_missing_cost_fails_closed():
    assert build_portfolio_identity_integrity([card("A",None)])["status"]=="INSUFFICIENT_DATA"

def test_groups_capital_by_existing_gate_status():
    r=build_portfolio_identity_integrity([
        card("A",300,"VERIFIERAD"),card("B",100,"SÖKBAR",True,False)
    ])
    assert r["identity_groups"][0]["status"]=="VERIFIERAD"
    assert r["identity_groups"][0]["capital_share_pct"]==75.0
    assert r["identity_groups"][1]["status"]=="SÖKBAR"
    assert r["identity_groups"][1]["capital_share_pct"]==25.0

def test_exact_search_capital_is_separate_from_dynamic_max_bid():
    r=build_portfolio_identity_integrity([
        card("A",100,"VERIFIERAD",True,True),
        card("B",100,"SÖKBAR",True,False),
    ])
    assert r["exact_comp_search_capital_pct"]==100.0
    assert r["dynamic_max_bid_capital_pct"]==50.0

def test_unresolved_identity_capital_is_descriptive():
    r=build_portfolio_identity_integrity([
        card("A",100,"GRANSKA",False,False),
        card("B",300,"VERIFIERAD",True,True),
    ])
    assert r["unresolved_identity_capital"]==100
    assert r["unresolved_identity_capital_pct"]==25.0

def test_unknown_status_is_not_promoted():
    x=card("A",100)
    x["exact_identity_gate_status"]="mystery"
    x["exact_identity_gate_supports_exact_comp_search"]=False
    x["exact_identity_gate_supports_dynamic_max_bid"]=False
    r=build_portfolio_identity_integrity([x])
    assert r["identity_groups"][0]["status"]=="OKÄND"
    assert r["identity_inferred"] is False

def test_no_risk_score_or_ranking_change():
    r=build_portfolio_identity_integrity([card("A",100)])
    assert r["risk_score_created"] is False
    assert r["ranking_changed"] is False
