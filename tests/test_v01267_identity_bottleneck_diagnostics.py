from src.card_parser import parse_card_features, extract_player_name
from src.exact_identity_gate import build_exact_identity_gate
from src.research_shortlist import research_identity_failure_diagnostics
from src.unlock_research_queue import build_unlock_research_queue


def test_narrow_research_missing_card_number_requires_variant_discriminator():
    gate = build_exact_identity_gate({
        "player_name": "Nicklas Backstrom",
        "player_match_confidence": "low",
        "set_name": "MVP",
        "season": "2021-22",
        "parallel": "Silver Script",
        "card_identity_confidence_score": 45,
    })
    assert gate["supports_comp_research"] is True
    assert gate["research_mode"] == "NARROW"
    assert gate["supports_exact_comp_search"] is False
    assert gate["research_missing_fields"] == ["kortnummer"]


def test_narrow_research_missing_season_can_use_card_number():
    gate = build_exact_identity_gate({
        "player_name": "Wayne Gretzky",
        "player_match_confidence": "low",
        "set_name": "Pinnacle",
        "card_number": "101",
        "card_identity_confidence_score": 45,
    })
    assert gate["supports_comp_research"] is True
    assert gate["research_mode"] == "NARROW"
    assert gate["supports_exact_comp_search"] is False


def test_missing_number_without_other_discriminator_stays_locked():
    gate = build_exact_identity_gate({
        "player_name": "Wayne Gretzky",
        "player_match_confidence": "low",
        "set_name": "Pinnacle",
        "season": "1995-96",
        "card_identity_confidence_score": 40,
    })
    assert gate["supports_comp_research"] is False


def test_diagnostics_counts_missing_anchors():
    items = [
        {"exact_identity_gate_missing_fields": ["kortnummer", "set/program"], "exact_identity_gate_blockers": []},
        {"exact_identity_gate_missing_fields": ["kortnummer"], "exact_identity_gate_blockers": []},
    ]
    out = research_identity_failure_diagnostics(items)
    assert out["counts"]["kortnummer"] == 2
    assert out["counts"]["set/program"] == 1


def test_research_ready_lane_sorts_before_identity_first():
    items = [
        {"titel":"Locked", "deal_score":99, "exact_identity_gate_supports_comp_research":False},
        {"titel":"Researchable", "deal_score":10, "exact_identity_gate_supports_comp_research":True},
    ]
    out = build_unlock_research_queue(items, limit=2)
    assert out["rows"][0]["status"] == "RESEARCH_READY_NO_SALES"


def test_parser_knows_common_older_hockey_sets():
    assert parse_card_features("1995-96 Pinnacle #101 Wayne Gretzky")["set_name"] == "Pinnacle"
    assert parse_card_features("1991-92 Score #1 Wayne Gretzky")["set_name"] == "Score"


def test_fallback_player_parser_ignores_brand_and_program_words():
    name = extract_player_name("2022/23 Topps UCL Super-Stars #100 Some Player Uncommon Green")
    assert name == "Some Player"
