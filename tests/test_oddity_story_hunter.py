from src.oddity_story_hunter import build_oddity_story_signal, build_oddity_story_queue


def test_known_story_without_story_in_title_is_high_priority():
    item={
        "title":"1990-91 Hoops #205 Mark Jackson",
        "nonstandard_value_signal_score":20,
        "nonstandard_value_known_matches":["mark_jackson_menendez_background"],
        "nonstandard_value_signals":[{"type":"Kulturell/bakgrundshistoria","reason":"Kontrollera bakgrunden.","confidence":"KNOWN_CARD_MATCH"}],
        "listing_quality_score":70,
    }
    s=build_oddity_story_signal(item)
    assert s["candidate"] is True
    assert s["seller_may_have_missed_story"] is True
    assert s["priority_score"] >= 70
    assert s["can_create_buy_decision"] is False


def test_generic_error_claim_is_research_only():
    item={
        "title":"Rare error card",
        "nonstandard_value_signal_score":6,
        "nonstandard_value_signals":[{"type":"Feltryck/error","reason":"Verifiera felet.","confidence":"LISTING_CLAIM"}],
    }
    s=build_oddity_story_signal(item)
    assert s["candidate"] is True
    assert s["can_create_market_value"] is False
    assert "faktiska SOLD-comps" in s["verify_first"]


def test_plain_card_is_not_oddity_candidate():
    s=build_oddity_story_signal({"title":"2023-24 Upper Deck #12 Player Name","nonstandard_value_signal_score":0})
    assert s["candidate"] is False


def test_queue_prioritizes_known_story_over_generic_claim():
    rows=build_oddity_story_queue([
        {"title":"Generic error","nonstandard_value_signal_score":6,"nonstandard_value_signals":[{"type":"Feltryck/error","reason":"verify","confidence":"LISTING_CLAIM"}]},
        {"title":"1990-91 Hoops #205 Mark Jackson","nonstandard_value_signal_score":20,"nonstandard_value_known_matches":["mark_jackson_menendez_background"],"nonstandard_value_signals":[{"type":"Story","reason":"verify","confidence":"KNOWN_CARD_MATCH"}]},
    ],limit=2)["rows"]
    assert "Mark Jackson" in rows[0]["title"]
