from src.seller_card_merit import assess_seller_card_merit
from src.seller_collector_signals import collector_signals
from src.sports_card_signal_knowledge import match_sports_card_signals


def _names(text):
    return {row["name"] for row in match_sports_card_signals(text)}


def test_official_topps_football_chase_names_get_research_priority():
    for title in (
        "2024 Topps Chrome UEFA Lamine Yamal Berlin at Night",
        "Topps Chrome UCC Jude Bellingham Helix",
        "Topps UEFA European Tour insert",
        "Topps Premier League Chrome Anime",
        "Topps UEFA Mindgame Endrick",
        "Topps UCL Hype rookie",
    ):
        assert "football_named_chase" in _names(title)


def test_chase_words_need_football_product_context():
    assert "football_named_chase" not in _names("Helix guitar processor")
    assert "football_named_chase" not in _names("Berlin at Night postcard")
    assert "football_named_chase" not in _names("Topps Chrome Golazo insert")
    assert "football_named_chase" not in _names("Topps Chrome base rookie")


def test_named_football_chase_routes_research_without_creating_value():
    title = "Topps Chrome UEFA Lamine Yamal Munich at Night"
    collector = collector_signals({"titel": title})
    merit = assess_seller_card_merit({"titel": title, "decision": "SKIP"})
    match = next(row for row in collector["knowledge_matches"] if row["name"] == "football_named_chase")

    assert "football_named_chase" in collector["signals"]
    assert merit["eligible"] is True
    assert match["research_only"] is True
    assert match["creates_value"] is False
    assert match["creates_buy"] is False
    assert collector["verify_first"]
