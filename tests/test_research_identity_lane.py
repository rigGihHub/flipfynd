from src.card_parser import parse_card_features
from src.exact_identity_gate import build_exact_identity_gate
from src.exact_comp_hunter import hunt_exact_comps


def test_structured_title_can_unlock_research_without_unlocking_valuation():
    gate = build_exact_identity_gate({
        "player_name": "Jamal Musiala",
        "player_match_confidence": "low",
        "player_match_type": "parser_fallback",
        "set_name": "Topps UCL Super-Stars",
        "season": "2022-23",
        "card_number": "100",
        "card_identity_confidence_score": 45,
        "identity_evidence_sources": {
            "player_name": ["title"], "set_name": ["title"],
            "season": ["title"], "card_number": ["title"],
        },
    })
    assert gate["supports_comp_research"] is True
    assert gate["supports_exact_comp_search"] is False
    assert gate["supports_dynamic_max_bid"] is False
    assert gate["status"] == "SÖKBAR_TITEL"


def test_research_only_identity_builds_links_but_no_exact_sales():
    identity = {"player_name":"Jamal Musiala","set_name":"Topps UCL Super-Stars","season":"2022-23","card_number":"100"}
    out = hunt_exact_comps({"verified_identity":False,"research_identity":True,"identity_fields":identity}, [])
    assert out["research_unlocked"] is True
    assert out["unlocked"] is False
    assert out["search_targets"]
    assert out["exact_sold_count"] == 0


def test_ucl_superstars_parser_recognises_set():
    f = parse_card_features("2022/23 Topps UCL Super-Stars #100 Jamal Musiala Uncommon Green")
    assert f["set_name"] == "Topps UCL Super-Stars"
    assert f["season"] == "2022-23"
    assert f["card_number"] == "100"


def test_silver_script_is_named_parallel_not_generic_silver():
    f = parse_card_features("Nicklas Backstrom 2021-22 MVP Hockey Silver Script #119")
    assert f["parallel"] == "Silver Script"


def test_season_slash_is_not_serial_denominator():
    f = parse_card_features("2022/23 Topps UCL Super-Stars #100 Jamal Musiala")
    assert f["season"] == "2022-23"
    assert f["serial_number"] is None

