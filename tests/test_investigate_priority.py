from src.decision_tiers import build_decision_tiers


def test_investigate_fallback_prefers_researchable_candidate():
    searchable = {
        "titel": "Searchable",
        "beslut": "SKIP",
        "deal_score": 62,
        "confidence": 35,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_comp_research": True,
    }
    flashy = {
        "titel": "Flashy",
        "beslut": "SKIP",
        "deal_score": 90,
        "confidence": 35,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_comp_research": False,
    }
    out = build_decision_tiers([flashy, searchable], total_limit=2, require_verified_economic_edge=True)
    assert out["fallback_investigate_mode"] is True
    assert out["rows"][0]["title"] == "Searchable"
    assert out["rows"][0]["decision"] == "UNDERSÖK"
    assert out["rows"][0]["research_ready"] is True


def test_investigate_score_never_creates_buy_or_market_value():
    item = {
        "titel": "Interesting",
        "beslut": "SKIP",
        "deal_score": 88,
        "confidence": 70,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_comp_research": True,
        "is_information_edge_candidate": True,
        "valuation_display_safe": False,
        "market_value_estimate": 999,
    }
    row = build_decision_tiers([item], require_verified_economic_edge=True)["rows"][0]
    assert row["decision"] == "UNDERSÖK"
    assert row["market_value"] is None
    assert row["economic_edge_ok"] is False
    assert row["investigate_score"] > 0
