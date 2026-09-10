from src.decision_tiers import build_decision_tiers

def test_verified_buy_requires_evidence_not_just_score():
    weak={
        "titel":"Weak",
        "beslut":"SKIP",
        "deal_score":94,
        "confidence":5,
        "sold_comparable_count":0,
    }
    out=build_decision_tiers([weak])
    row=out["rows"][0]
    assert row["tier"]!="VERIFIED"
    assert row["potential"]==94
    assert row["certainty"]==5

def test_verified_tier_requires_buy_identity_sold_and_safe_value():
    strong={
        "titel":"Strong",
        "beslut":"KÖP",
        "deal_score":80,
        "ranking_confidence_score":85,
        "sold_comparable_count":3,
        "exact_identity_gate_supports_exact_comp_search":True,
        "valuation_display_safe":True,
        "market_value_estimate":500,
    }
    row=build_decision_tiers([strong])["rows"][0]
    assert row["tier"]=="VERIFIED"
    assert row["market_value"]==500

def test_unsafe_value_is_hidden():
    item={
        "titel":"X",
        "deal_score":70,
        "confidence":40,
        "valuation_display_safe":False,
        "market_value_estimate":999,
    }
    row=build_decision_tiers([item])["rows"][0]
    assert row["market_value"] is None
