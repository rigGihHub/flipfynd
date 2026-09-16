from src.seller_card_merit import assess_seller_card_merit
from src.seller_collector_signals import collector_signals
from src.sports_card_signal_knowledge import match_sports_card_signals


def _names(text):
    return {row["name"] for row in match_sports_card_signals(text)}


def test_young_guns_french_wording_is_a_flagship_variant_signal():
    assert "flagship_rookie_variant" in _names(
        "2022-23 Upper Deck Young Guns French Variation Kirill Marchenko #718"
    )
    assert "flagship_rookie_variant" in _names(
        "2021-22 French Parallel Young Guns Seth Jarvis #745"
    )
    assert "flagship_rookie_variant" in _names("UD Young Guns French Cole Caufield")


def test_french_language_or_base_parallel_without_young_guns_does_not_match():
    assert "flagship_rookie_variant" not in _names("French football rookie card")
    assert "flagship_rookie_variant" not in _names("Upper Deck French Parallel base card")
    assert "flagship_rookie_variant" not in _names("Young Guns English base")


def test_young_guns_french_passes_merit_gate_without_value_claim():
    title = "2022-23 Young Guns French Kirill Marchenko #718"
    collector = collector_signals({"titel": title})
    merit = assess_seller_card_merit({"titel": title, "decision": "SKIP"})
    match = next(
        row
        for row in collector["knowledge_matches"]
        if row["name"] == "flagship_rookie_variant"
    )

    assert collector["score"] == 27
    assert merit["eligible"] is True
    assert match["research_only"] is True
    assert match["creates_value"] is False
    assert match["creates_buy"] is False
    assert collector["verify_first"]
