from src.portfolio_concentration import build_portfolio_concentration

def card(name,cost,player=None,set_family=None,sport="hockey"):
    return {
        "titel":name,"total_cost":cost,"player_name":player,
        "card_identity_family":set_family,"sport":sport,
    }

def test_empty():
    assert build_portfolio_concentration([])["status"]=="NO_SELECTION"

def test_missing_cost_fails_closed():
    assert build_portfolio_concentration([card("A",None)])["status"]=="INSUFFICIENT_DATA"

def test_position_shares_are_factual():
    r=build_portfolio_concentration([card("A",300),card("B",100)])
    assert r["largest_position_share_pct"]==75.0
    assert r["top_two_position_share_pct"]==100.0

def test_player_concentration_groups_capital():
    r=build_portfolio_concentration([
        card("A",100,"Player X"),card("B",200,"Player X"),card("C",100,"Player Y")
    ])
    assert r["player_groups"][0]["label"]=="Player X"
    assert r["player_groups"][0]["capital_share_pct"]==75.0
    assert r["player_groups"][0]["card_count"]==2

def test_set_and_sport_groups():
    r=build_portfolio_concentration([
        card("A",100,"X","Young Guns","hockey"),
        card("B",100,"Y","Young Guns","hockey"),
        card("C",200,"Z","Topps Chrome","football"),
    ])
    yg=next(x for x in r["set_groups"] if x["label"]=="Young Guns")
    football=next(x for x in r["sport_groups"] if x["label"]=="football")
    assert yg["capital_share_pct"]==50.0
    assert football["capital_share_pct"]==50.0

def test_unknown_identity_is_transparent():
    r=build_portfolio_concentration([card("A",100,None,None)])
    assert r["unknown_player_capital_pct"]==100.0
    assert r["unknown_set_capital_pct"]==100.0

def test_no_arbitrary_limits_or_risk_bands():
    r=build_portfolio_concentration([card("A",100,"X","Set")])
    assert r["limits_applied"] is False
    assert r["risk_band_created"] is False

def test_never_changes_ranking():
    r=build_portfolio_concentration([card("A",100,"X","Set")])
    assert r["ranking_changed"] is False
