from src.reference_image_verification import verify_against_reference_traits
from src.oddity_registry import match_curated_cards


def test_registry_rows_expose_reference_traits_for_known_seed():
    rows = match_curated_cards(title="1990-91 Hoops #205 Mark Jackson", sport="basketball", player_name="Mark Jackson", features={"set_name": "Hoops", "season": "1990-91", "card_number": "205"})
    assert rows
    assert rows[0].get("reference_traits")


def test_mark_jackson_background_signal_builds_abc_reference_check():
    out = verify_against_reference_traits({
        "player_name": "Mark Jackson", "set_or_product": "Hoops", "season_or_year": "1990-91", "card_number": "205",
        "possible_background_story": "yes", "oddity_confidence": 0.9, "identity_confidence": 0.9,
        "front_visible": "yes", "back_visible": "no", "photo_quality": "good", "ordinary_damage_only": False,
        "oddity_observations": ["Två personer syns i bakgrunden"],
    }, title="1990-91 Hoops #205 Mark Jackson", sport="basketball")
    assert out["matches"]
    assert out["best_score"] >= 80
    assert any(x["label"] == "A" for x in out["matches"][0]["checklist"])
    assert out["can_create_market_value"] is False


def test_identity_only_does_not_claim_visual_variant():
    out = verify_against_reference_traits({
        "player_name": "Frank Thomas", "set_or_product": "Topps", "season_or_year": "1990", "card_number": "414",
        "possible_missing_print": "no", "oddity_confidence": 0.1, "identity_confidence": 0.9,
        "front_visible": "yes", "back_visible": "yes", "photo_quality": "good", "ordinary_damage_only": False,
    }, title="1990 Topps #414 Frank Thomas", sport="baseball")
    assert out["matches"]
    assert "inte visuellt bekräftat" in out["matches"][0]["status"]
    assert out["research_only"] is True


def test_damage_caps_reference_score_and_blocks_strong_claim():
    out = verify_against_reference_traits({
        "player_name": "Frank Thomas", "set_or_product": "Topps", "season_or_year": "1990", "card_number": "414",
        "possible_missing_print": "yes", "oddity_confidence": 0.95, "identity_confidence": 0.95,
        "front_visible": "yes", "back_visible": "yes", "photo_quality": "excellent", "ordinary_damage_only": True,
        "oddity_observations": ["Färgsläpp vid namnplattan"],
    }, title="1990 Topps #414 Frank Thomas", sport="baseball")
    assert out["best_score"] <= 35
    assert "skick/produktionsfel" in out["status"]
