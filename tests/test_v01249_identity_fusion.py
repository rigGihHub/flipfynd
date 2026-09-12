from src.card_explanation import build_card_identity_summary
from src.card_parser import parse_card_features
from src.decision_tiers import build_decision_tiers


def test_collectors_choice_title_parses_specific_identity():
    title = "1997-98 Upper Deck Collector's Choice #167 Wayne Gretzky New York Rangers"
    f = parse_card_features(title)
    assert f["player_name"] == "Wayne Gretzky"
    assert f["set_name"] == "Upper Deck Collector's Choice"
    assert f["season"] == "1997-98"
    assert f["card_number"] == "167"


def test_identity_summary_shows_observed_title_without_claiming_verified():
    item = {
        "titel": "1997-98 Upper Deck Collector's Choice #167 Wayne Gretzky New York Rangers",
        "exact_identity_gate_status": "LÅST",
        "exact_identity_gate_label": "Exakt identitet låst",
        "exact_identity_gate_supports_exact_comp_search": False,
    }
    summary = build_card_identity_summary(item)
    rows = {r["label"]: r for r in summary["rows"]}
    assert rows["Spelare"]["value"] == "Wayne Gretzky"
    assert rows["Spelare"]["level"] == "observed"
    assert rows["Set / program"]["value"] == "Upper Deck Collector's Choice"
    assert rows["Säsong / år"]["value"] == "1997-98"
    assert rows["Kortnummer"]["value"] == "#167"
    assert summary["supports_exact_comp_search"] is False


def test_decision_tier_keeps_original_analysis_for_explanation_drilldown():
    item = {
        "titel": "1997-98 Upper Deck Collector's Choice #167 Wayne Gretzky",
        "deal_score": 21,
        "confidence": 88,
        "player_name": "Wayne Gretzky",
        "exact_identity_gate_identity_fields": {"player_name": "Wayne Gretzky"},
    }
    row = build_decision_tiers([item])["rows"][0]
    assert row["_source_item"] is item
    assert row["_source_item"]["exact_identity_gate_identity_fields"]["player_name"] == "Wayne Gretzky"
