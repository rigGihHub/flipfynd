from src.seller_card_merit import assess_seller_card_merit
from src.seller_collector_signals import collector_signals
from src.sports_card_signal_knowledge import match_sports_card_signals


def _names(text):
    return {row["name"] for row in match_sports_card_signals(text)}


def test_documented_young_guns_variants_get_research_priority():
    for title in (
        "2025-26 Young Guns High Gloss rookie",
        "Young Guns Exclusives /100",
        "Clear Cut Young Guns",
        "Young Guns Outburst Red /25",
        "UD Canvas Young Guns rookie",
    ):
        assert "flagship_rookie_variant" in _names(title)


def test_plain_young_guns_or_canvas_does_not_invent_variant():
    assert "flagship_rookie_variant" not in _names("Upper Deck Young Guns rookie")
    assert "flagship_rookie_variant" not in _names("UD Canvas veteran star")
    assert "flagship_rookie_variant" not in _names("Rare rookie parallel")


def test_variant_signal_routes_underdescribed_card_without_creating_value():
    title = "Macklin Celebrini UD Canvas Young Guns"
    collector = collector_signals({"titel": title})
    merit = assess_seller_card_merit({"titel": title, "decision": "SKIP"})
    match = next(row for row in collector["knowledge_matches"] if row["name"] == "flagship_rookie_variant")

    assert "flagship_rookie_variant" in collector["signals"]
    assert merit["eligible"] is True
    assert match["research_only"] is True
    assert match["creates_value"] is False
    assert match["creates_buy"] is False
    assert collector["verify_first"]
