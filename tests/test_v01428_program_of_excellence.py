from src.seller_card_merit import assess_seller_card_merit
from src.seller_collector_signals import collector_signals
from src.sports_card_signal_knowledge import match_sports_card_signals


def _names(text):
    return {row["name"] for row in match_sports_card_signals(text)}


def test_program_of_excellence_with_card_context_is_research_signal():
    assert "upper_deck_program_of_excellence" in _names(
        "2023-24 UD Canvas Program of Excellence Connor Bedard C258"
    )
    assert "upper_deck_program_of_excellence" in _names(
        "Program of Excellence Nathan MacKinnon C-257"
    )
    assert "upper_deck_program_of_excellence" in _names(
        "Upper Deck Program of Excellence Black and White Connor McDavid"
    )


def test_generic_excellence_wording_without_card_context_does_not_match():
    assert "upper_deck_program_of_excellence" not in _names(
        "School Program of Excellence award"
    )
    assert "upper_deck_program_of_excellence" not in _names(
        "Program of Excellence hockey certificate"
    )
    assert "upper_deck_program_of_excellence" not in _names("UD Canvas base card C121")


def test_program_of_excellence_passes_merit_gate_without_value_claim():
    title = "2023-24 UD Canvas Program of Excellence Connor Bedard C258"
    collector = collector_signals({"titel": title})
    merit = assess_seller_card_merit({"titel": title, "decision": "SKIP"})
    match = next(
        row
        for row in collector["knowledge_matches"]
        if row["name"] == "upper_deck_program_of_excellence"
    )

    assert collector["score"] == 18
    assert merit["eligible"] is True
    assert match["research_only"] is True
    assert match["creates_value"] is False
    assert match["creates_buy"] is False
    assert collector["verify_first"]
