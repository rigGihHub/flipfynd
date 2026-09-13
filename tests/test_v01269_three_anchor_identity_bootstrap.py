from src.exact_identity_gate import build_exact_identity_gate


def _base(**kwargs):
    d = {
        "player_name": "Wayne Gretzky",
        "player_match_confidence": "low",
        "card_identity_confidence_score": 32,
        "research_title_identity": {"fields": {}, "complete": False},
    }
    d.update(kwargs)
    return d


def test_bootstrap_allows_player_season_number_without_set_for_research_only():
    d = _base(research_title_identity={"fields": {
        "player_name": "Wayne Gretzky",
        "season": "1995-96",
        "card_number": "101",
    }, "complete": False})
    gate = build_exact_identity_gate(d)
    assert gate["supports_comp_research"] is True
    assert gate["research_mode"] == "BOOTSTRAP"
    assert gate["supports_exact_comp_search"] is False
    assert gate["supports_dynamic_max_bid"] is False


def test_missing_number_without_discriminator_stays_locked():
    d = _base(set_name="Pinnacle", season="1995-96", research_title_identity={"fields": {
        "player_name": "Wayne Gretzky",
        "set_name": "Pinnacle",
        "season": "1995-96",
    }, "complete": False})
    gate = build_exact_identity_gate(d)
    assert gate["supports_comp_research"] is False
    assert gate["research_mode"] == "LOCKED"


def test_two_anchor_identity_stays_locked():
    d = _base(research_title_identity={"fields": {
        "player_name": "Wayne Gretzky",
        "set_name": "Pinnacle",
    }, "complete": False})
    gate = build_exact_identity_gate(d)
    assert gate["supports_comp_research"] is False
    assert gate["research_mode"] == "LOCKED"
