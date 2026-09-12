from src.decision_tiers_compat import build_decision_tiers_compat


def _good(title="Good"):
    return {
        "title": title,
        "decision": "KÖP",
        "sold_comparable_count": 2,
        "exact_identity_gate_supports_exact_comp_search": True,
        "valuation_display_safe": True,
        "market_value_estimate": 200,
        "analysis_total_cost": 100,
        "dynamic_max_total_price": 130,
    }


def test_current_signature_receives_gate():
    seen = {}
    def current(candidates, total_limit=3, require_verified_economic_edge=False):
        seen["gate"] = require_verified_economic_edge
        return {"rows": candidates[:total_limit]}
    out = build_decision_tiers_compat(current, [_good()], require_verified_economic_edge=True)
    assert seen["gate"] is True
    assert len(out["rows"]) == 1


def test_legacy_signature_is_prefiltered():
    def legacy(candidates, total_limit=3):
        return {"rows": candidates[:total_limit]}
    bad = _good("Bad")
    bad["sold_comparable_count"] = 0
    out = build_decision_tiers_compat(legacy, [bad, _good()], require_verified_economic_edge=True)
    assert [row["title"] for row in out["rows"]] == ["Good"]
    assert out["rejected_count"] == 1


def test_legacy_gate_rejects_cost_above_max():
    def legacy(candidates, total_limit=3):
        return {"rows": candidates[:total_limit]}
    bad = _good("Too expensive")
    bad["analysis_total_cost"] = 150
    out = build_decision_tiers_compat(legacy, [bad], require_verified_economic_edge=True)
    assert out["rows"] == []
