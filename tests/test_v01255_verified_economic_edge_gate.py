from src.decision_tiers import build_decision_tiers


def item(decision="SKIP", sold=0, identity=False, value=None, cost=32, max_total=0):
    return {
        "titel": "1995-96 Pinnacle #101 Wayne Gretzky",
        "deal_score": 90,
        "ranking_confidence_score": 90,
        "sold_comparable_count": sold,
        "exact_identity_gate_supports_exact_comp_search": identity,
        "exact_identity_gate_identity_fields": {"player_name": "Wayne Gretzky"},
        "beslut": decision,
        "valuation_display_safe": value is not None,
        "market_value_estimate": value,
        "analysis_total_cost": cost,
        "max_total_price": max_total,
    }


def test_cheap_famous_card_cannot_become_verified_buy_without_edge():
    r = build_decision_tiers([item()], require_verified_economic_edge=True)
    assert r["fallback_investigate_mode"] is True
    assert len(r["rows"]) == 1
    assert r["rows"][0]["decision"] == "UNDERSÖK"
    assert r["rows"][0]["economic_edge_ok"] is False


def test_verified_buy_below_max_can_enter():
    r = build_decision_tiers([item("KÖP", 3, True, 120, 50, 75)], require_verified_economic_edge=True)
    assert len(r["rows"]) == 1
    assert r["rows"][0]["decision"] == "KÖP"
    assert r["rows"][0]["economic_edge_ok"] is True


def test_above_max_is_never_returned_as_buy():
    r = build_decision_tiers([item("KÖP", 5, True, 25, 32, 18)], require_verified_economic_edge=True)
    assert len(r["rows"]) == 1
    assert r["rows"][0]["decision"] == "UNDERSÖK"
    assert r["rows"][0]["economic_edge_ok"] is False
    assert any("överstiger" in k for k in r["rejection_reasons"])
