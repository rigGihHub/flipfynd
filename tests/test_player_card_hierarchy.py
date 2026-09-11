from src.player_card_hierarchy import build_player_card_hierarchy

def test_elite_player_plus_strong_program_is_top_profile():
    out=build_player_card_hierarchy(
        player_name="Connor McDavid",
        player_market_score=96,
        player_market_tier="elite",
        card_hierarchy_score=90,
        card_hierarchy_tier="TIER_A",
        card_hierarchy_role="FLAGSHIP_ROOKIE",
        is_rookie=True,
        sold_comparable_count=3,
        valuation_confidence_score=70,
        identity_confidence_score=90,
    )
    assert out["profile"]=="ELITE_X_PREMIUM"
    assert out["score"]>=90
    assert out["creates_market_value"] is False
    assert out["creates_buy_decision"] is False

def test_elite_player_standard_card_is_not_premium_by_name_alone():
    out=build_player_card_hierarchy(
        player_name="Connor McDavid",
        player_market_score=96,
        player_market_tier="elite",
        card_hierarchy_score=20,
        card_hierarchy_tier="TIER_E",
        card_hierarchy_role="BASE_OR_UNKNOWN",
        identity_confidence_score=90,
    )
    assert out["profile"]=="STAR_X_STANDARD"
    assert any("ordinär kortstruktur" in x for x in out["cautions"])
    assert any("Stjärnfälla" in x for x in out["hobby_traps"])

def test_premium_program_weak_player_is_cautioned():
    out=build_player_card_hierarchy(
        player_name="Nils Höglander",
        player_market_score=24,
        player_market_tier="weak",
        card_hierarchy_score=92,
        card_hierarchy_tier="TIER_A",
        card_hierarchy_role="PREMIUM_ROOKIE_AUTO",
        is_rookie=True,
        identity_confidence_score=90,
    )
    assert out["profile"]=="PREMIUM_X_WEAK_PLAYER"
    assert any("strukturen ensam räcker inte" in x for x in out["cautions"])

def test_career_status_is_not_invented():
    out=build_player_card_hierarchy(
        player_name="Wayne Gretzky",
        player_market_score=94,
        player_market_tier="elite",
        card_hierarchy_score=20,
        card_hierarchy_tier="TIER_E",
        card_hierarchy_role="BASE_OR_UNKNOWN",
        identity_confidence_score=90,
    )
    assert out["career_status"] is None
    assert "saknar verifierad career-status" in out["career_status_note"]
