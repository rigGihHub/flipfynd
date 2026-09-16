from src.seller_card_merit import assess_seller_card_merit
from src.seller_collector_signals import collector_signals
from src.sports_card_signal_knowledge import match_sports_card_signals


def _names(text):
    return {row["name"] for row in match_sports_card_signals(text)}


def test_population_count_program_and_tiers_are_exact_research_signals():
    assert "upper_deck_population_count" in _names(
        "2024-25 Upper Deck Population Count 100 Connor Bedard PC-3"
    )
    assert "upper_deck_population_count" in _names(
        "Population Count 1 Macklin Celebrini PC-42"
    )
    assert "upper_deck_population_count" in _names("Upper Deck Population Count acetate")


def test_generic_population_and_serial_numbering_do_not_match():
    assert "upper_deck_population_count" not in _names("PSA population report count 100")
    assert "upper_deck_population_count" not in _names("Upper Deck serial numbered /100")
    assert "upper_deck_population_count" not in _names("Upper Deck base card")


def test_population_count_passes_merit_gate_without_value_claim():
    title = "2024-25 Upper Deck Population Count 100 Connor Bedard PC-3"
    collector = collector_signals({"titel": title})
    merit = assess_seller_card_merit({"titel": title, "decision": "SKIP"})
    match = next(
        row
        for row in collector["knowledge_matches"]
        if row["name"] == "upper_deck_population_count"
    )

    assert collector["score"] == 18
    assert merit["eligible"] is True
    assert match["research_only"] is True
    assert match["creates_value"] is False
    assert match["creates_buy"] is False
    assert collector["verify_first"]
