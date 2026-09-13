from src.card_parser import parse_card_features
from src.research_title_identity import build_research_title_identity
from src.exact_identity_gate import build_exact_identity_gate
from src.auto_comp_research import identity_from_item


def test_recovers_bare_card_number_for_research_only():
    title = "1995-96 Pinnacle 101 Wayne Gretzky Los Angeles Kings"
    base = parse_card_features(title)
    rec = build_research_title_identity(title, base)
    assert rec["fields"]["card_number"] == "101"
    assert rec["complete"] is True
    assert "kortnummer" in rec["recovered_fields"]


def test_does_not_guess_when_multiple_bare_numbers_exist():
    title = "1995-96 Pinnacle 101 Wayne Gretzky 99"
    base = parse_card_features(title)
    rec = build_research_title_identity(title, base)
    assert rec["fields"]["card_number"] is None


def test_title_recovery_unlocks_research_but_not_exact_or_dynamic():
    title = "1995-96 Pinnacle 101 Wayne Gretzky"
    base = parse_card_features(title)
    base["player_match_confidence"] = "low"
    base["card_identity_confidence_score"] = 20
    rec = build_research_title_identity(title, base)
    gate = build_exact_identity_gate({**base, "research_title_identity": rec})
    assert gate["supports_comp_research"] is True
    assert gate["research_mode"] == "TITLE_RECOVERED"
    assert gate["supports_exact_comp_search"] is False
    assert gate["supports_dynamic_max_bid"] is False


def test_auto_research_uses_recovered_identity_without_promoting_strict_identity():
    item = {
        "exact_identity_gate_supports_comp_research": True,
        "exact_identity_gate_supports_exact_comp_search": False,
        "exact_identity_gate_research_identity_fields": {
            "player_name": "Wayne Gretzky",
            "set_name": "Pinnacle",
            "season": "1995-96",
            "card_number": "101",
        },
        "exact_identity_gate_identity_fields": {
            "player_name": "Wayne Gretzky",
            "set_name": "Pinnacle",
            "season": "1995-96",
            "card_number": None,
        },
    }
    research = identity_from_item(item, research=True)
    strict = identity_from_item(item, research=False)
    assert research["card_number"] == "101"
    assert strict["card_number"] is None
