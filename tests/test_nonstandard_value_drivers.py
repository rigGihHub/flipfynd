from src.nonstandard_value_drivers import build_nonstandard_value_profile


def test_mark_jackson_story_card_is_research_signal_only():
    p=build_nonstandard_value_profile(title="1990-91 Hoops #205 Mark Jackson", sport="basketball", player_name="Mark Jackson", features={"season":"1990-91","set_name":"Hoops","card_number":"205"})
    assert "mark_jackson_menendez_background" in p["known_story_matches"]
    assert p["creates_market_value"] is False
    assert p["creates_buy_decision"] is False


def test_randy_johnson_marlboro_variation_is_flagged():
    p=build_nonstandard_value_profile(title="1989 Fleer #381 Randy Johnson Marlboro", sport="baseball", player_name="Randy Johnson", features={"season":"1989","set_name":"Fleer","card_number":"381"})
    assert "randy_johnson_marlboro" in p["known_story_matches"]
    assert any("censur" in x["type"].casefold() for x in p["signals"])


def test_generic_error_claim_does_not_create_value():
    p=build_nonstandard_value_profile(title="Rare error card", sport="hockey", player_name="Some Player", features={})
    assert p["signals"]
    assert p["safe_for_valuation"] is False
    assert p["signal_score"] < 50


def test_no_story_signal_for_plain_base_title():
    p=build_nonstandard_value_profile(title="2023-24 Upper Deck #12 Player Name", sport="hockey", player_name="Player Name", features={"season":"2023-24","set_name":"Upper Deck","card_number":"12"})
    assert p["known_story_matches"] == []
    assert p["signal_score"] == 0
