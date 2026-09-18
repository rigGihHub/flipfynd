from src.card_hierarchy_engine import build_card_hierarchy_engine


def test_numbered_to_99_is_not_base_or_tier_e():
    result = build_card_hierarchy_engine(
        sport="hockey", signals=[],
        features={"serial_denominator": 99, "identity_confidence_score": 80},
    )
    assert result["role"] == "SERIAL_NUMBERED_UNKNOWN_PARALLEL"
    assert "/99" in result["role_label"]
    assert result["tier"] != "TIER_E"
    assert "Bas/okänd" not in result["tier_label"]


def test_numbered_structure_does_not_create_value_or_buy():
    result = build_card_hierarchy_engine(
        sport="hockey", signals=[],
        features={"serial_denominator": 99, "identity_confidence_score": 80},
    )
    assert result["creates_market_value"] is False
    assert result["creates_buy_decision"] is False
    assert result["safe_for_valuation"] is False


def test_low_numbered_unknown_parallel_is_stronger_structure_than_99():
    low = build_card_hierarchy_engine(sport="hockey", signals=[], features={"serial_denominator": 10, "identity_confidence_score": 80})
    ninety_nine = build_card_hierarchy_engine(sport="hockey", signals=[], features={"serial_denominator": 99, "identity_confidence_score": 80})
    assert low["score"] > ninety_nine["score"]
