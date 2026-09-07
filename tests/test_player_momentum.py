from src.player_momentum import normalize_momentum_event,build_player_momentum,build_starshot_watchlist

def ev(player="Prospect A",kind="ranking_rise",source="Scout",date="2026-09-01T10:00:00Z"):
    return {"player_name":player,"sport":"hockey","event_type":kind,"source_name":source,
            "source_url":"https://example.com/a","occurred_at":date,"detail":"documented change"}

def test_rejects_event_without_source_url():
    x=ev(); x["source_url"]=""
    assert normalize_momentum_event(x)["status"]=="REJECTED"

def test_rejects_unknown_event_type():
    x=ev(kind="future_superstar")
    assert normalize_momentum_event(x)["status"]=="REJECTED"

def test_momentum_has_no_synthetic_score():
    r=build_player_momentum([ev()])
    assert r["momentum_score"] is None

def test_momentum_never_creates_buy_signal():
    r=build_player_momentum([ev()])
    assert r["buy_signal_created"] is False and r["valuation_changed"] is False and r["max_bid_changed"] is False

def test_preserves_multiple_independent_event_types():
    r=build_player_momentum([ev(kind="ranking_rise"),ev(kind="senior_debut",source="League")])
    assert set(r["event_types"])=={"ranking_rise","senior_debut"}
    assert r["source_count"]==2

def test_watchlist_groups_by_player():
    r=build_starshot_watchlist([ev("A"),ev("A",kind="performance_breakout"),ev("B")])
    a=next(x for x in r["players"] if x["player_name"]=="A")
    assert a["event_count"]==2 and a["event_type_count"]==2

def test_watchlist_is_not_talent_forecast():
    r=build_starshot_watchlist([ev()])
    assert r["prospect_score_created"] is False
    assert "not a talent forecast" in r["ranking_basis"]

def test_invalid_dates_fail_closed():
    x=ev(); x["occurred_at"]="not-a-date"
    assert normalize_momentum_event(x)["status"]=="REJECTED"
