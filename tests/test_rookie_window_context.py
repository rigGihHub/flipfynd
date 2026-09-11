from src.rookie_window_context import build_rookie_window_context

def test_young_active_high_demand_window():
    out=build_rookie_window_context(
        features={"season":"2023-24","is_rookie":True},
        player_knowledge={
            "verified":True,
            "date_of_birth":"2005-07-17",
            "activity_status":"active",
        },
        player_market_score=92,
        player_market_tier="elite",
    )
    assert out["career_window"]=="YOUNG_WINDOW"
    assert out["rookie_claim_support"]=="CHRONOLOGICALLY_PLAUSIBLE"
    assert out["player_archetype"] in {"YOUNG_HIGH_DEMAND","ACTIVE_ELITE"}
    assert out["creates_market_value"] is False
    assert out["creates_buy_decision"] is False

def test_late_rookie_claim_is_suspicious_not_proven():
    out=build_rookie_window_context(
        features={"year":2024,"is_rookie":True},
        player_knowledge={
            "verified":True,
            "date_of_birth":"1985-09-17",
            "activity_status":"active",
        },
        player_market_score=95,
        player_market_tier="elite",
    )
    assert out["rookie_claim_support"]=="CHRONOLOGICALLY_SUSPICIOUS"
    assert out["research_priority"]=="HIGH"
    assert out["official_rookie_year"] is None
    assert out["official_rookie_year_verified"] is False

def test_early_age_without_rc_is_not_called_rookie():
    out=build_rookie_window_context(
        features={"season":"2024-25","is_rookie":False},
        player_knowledge={
            "verified":True,
            "date_of_birth":"2007-07-13",
            "activity_status":"active",
        },
        player_market_score=90,
        player_market_tier="elite",
    )
    assert out["career_window"]=="YOUNG_WINDOW"
    assert out["explicit_rookie_claim"] is False
    assert out["rookie_claim_support"]=="UNPROVEN"
    assert any("inte automatiskt ett rookie-kort" in r for r in out["reasons"])

def test_unknown_birth_year_stays_unknown():
    out=build_rookie_window_context(
        features={"season":"2024-25","is_rookie":True},
        player_knowledge={"verified":True,"activity_status":"active"},
        player_market_score=80,
        player_market_tier="strong",
    )
    assert out["age_at_card_season"] is None
    assert out["career_window"]=="UNKNOWN"
