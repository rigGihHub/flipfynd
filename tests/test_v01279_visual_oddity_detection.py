from src.visual_oddity_detector import build_visual_oddity_signal
from src.visual_detective import response_schema


def test_schema_contains_visual_oddity_fields():
    props = response_schema()["properties"]
    for key in (
        "possible_missing_print", "possible_image_orientation_issue", "possible_censorship_or_edit",
        "possible_background_story", "possible_factory_or_promo_marker", "oddity_confidence",
        "ordinary_damage_only", "oddity_observations",
    ):
        assert key in props


def test_missing_print_becomes_research_candidate_not_value():
    out = build_visual_oddity_signal({
        "possible_missing_print": "yes", "oddity_confidence": 0.81,
        "ordinary_damage_only": False, "oddity_observations": ["Namnfältet ser tomt ut"],
    })
    assert out["candidate"] is True
    assert "MISSING_PRINT" in out["categories"]
    assert out["can_create_market_value"] is False
    assert out["can_create_buy_decision"] is False


def test_ordinary_damage_blocks_collectible_oddity_candidate():
    out = build_visual_oddity_signal({
        "possible_missing_print": "yes", "oddity_confidence": 0.8,
        "ordinary_damage_only": True, "oddity_observations": ["Färgfläck vid kanten"],
    })
    assert out["candidate"] is False
    assert "skick/produktionsfel" in out["status"]


def test_known_mark_jackson_registry_match_is_recognized():
    out = build_visual_oddity_signal({
        "player_name": "Mark Jackson", "set_or_product": "Hoops", "season_or_year": "1990-91",
        "card_number": "205", "possible_background_story": "yes", "oddity_confidence": 0.9,
        "ordinary_damage_only": False, "oddity_observations": ["Två personer syns i bakgrunden"],
    }, title="1990-91 Hoops #205 Mark Jackson", sport="basketball")
    assert out["candidate"] is True
    assert any("Menendez" in x for x in out["known_registry_matches"])
    assert out["research_only"] is True
