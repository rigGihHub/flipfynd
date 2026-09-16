from src.seller_card_merit import assess_seller_card_merit
from src.seller_collector_signals import collector_signals
from src.sports_card_signal_knowledge import match_sports_card_signals


def _names(text):
    return {row["name"] for row in match_sports_card_signals(text)}


def test_day_with_cup_and_flashback_are_exact_research_signals():
    assert "upper_deck_day_with_cup" in _names("2023-24 Day With The Cup DC5 Mark Stone")
    assert "upper_deck_day_with_cup" in _names("UD Day with Cup Flashbacks DC3")
    assert "upper_deck_day_with_cup" not in _names("Stanley Cup winner base card")
    assert "upper_deck_day_with_cup" not in _names("Upper Deck championship moments")


def test_day_with_cup_now_passes_merit_gate_without_value_claim():
    title = "2023-24 Upper Deck Day With The Cup DC5 Mark Stone"
    collector = collector_signals({"titel": title})
    merit = assess_seller_card_merit({"titel": title, "decision": "SKIP"})
    match = next(row for row in collector["knowledge_matches"] if row["name"] == "upper_deck_day_with_cup")

    assert collector["score"] == 18
    assert merit["eligible"] is True
    assert match["research_only"] is True
    assert match["creates_value"] is False
    assert match["creates_buy"] is False
    assert collector["verify_first"]
