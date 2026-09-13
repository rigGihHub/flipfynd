from src.oddity_registry import match_curated_cards, classify_listing_text, registry_stats
from src.nonstandard_value_drivers import build_nonstandard_value_profile


def test_mark_jackson_registry_match():
    m=match_curated_cards(title="1990-91 Hoops #205 Mark Jackson", sport="basketball", player_name="Mark Jackson", features={"season":"1990-91","set_name":"Hoops","card_number":"205"})
    assert any(x["key"]=="mark_jackson_menendez_background" for x in m)


def test_dale_murphy_reverse_negative_match():
    m=match_curated_cards(title="1989 Upper Deck #357 Dale Murphy", sport="baseball", player_name="Dale Murphy", features={"season":"1989","set_name":"Upper Deck","card_number":"357"})
    assert any(x["key"]=="dale_murphy_reverse_negative" for x in m)


def test_generic_error_is_research_only():
    p=build_nonstandard_value_profile(title="1989 card error misprint", sport="baseball", player_name="X", features={})
    assert p["safe_for_valuation"] is False
    assert p["creates_market_value"] is False
    assert p["creates_buy_decision"] is False


def test_registry_stats_and_classification():
    st=registry_stats()
    assert st["seed_cards"] >= 6
    assert st["taxonomy_categories"] >= 10
    assert "MISSING_PRINT" in classify_listing_text("rare NNOF no name card")
