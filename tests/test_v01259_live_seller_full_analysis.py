from src.seller_live_full_analysis import full_analyze_live_seller_item


def test_full_analysis_uses_normal_full_pipeline_and_preserves_buy():
    calls = []

    def fake_analyze(item, **kwargs):
        calls.append(kwargs)
        return {
            "beslut": "KÖP",
            "exact_identity_gate_supports_exact_comp_search": True,
            "exact_identity_gate_score": 91,
            "sold_comparable_count": 3,
            "valuation_confidence_score": 72,
            "market_edge_score": 66,
            "max_buy_price": 180,
            "total_acquisition_cost": 120,
        }

    out = full_analyze_live_seller_item(
        {"titel": "Test card", "pris": 100},
        analyze_fn=fake_analyze,
        all_items=[{"titel": "market"}],
        sport="hockey",
    )
    assert calls[0]["mode"] == "full"
    assert calls[0]["all_items"] == [{"titel": "market"}]
    assert out["label"] == "KÖP-KANDIDAT"
    assert out["decision"] == "KÖP"
    assert out["sold_comps"] == 3
    assert out["max_price"] == 180


def test_full_analysis_does_not_promote_weak_evidence():
    def fake_analyze(item, **kwargs):
        return {
            "beslut": "SKIP",
            "exact_identity_gate_supports_exact_comp_search": False,
            "exact_identity_gate_score": 35,
            "sold_comparable_count": 0,
            "valuation_confidence_score": 18,
        }

    out = full_analyze_live_seller_item(
        {"titel": "Unknown card", "pris": 10},
        analyze_fn=fake_analyze,
    )
    assert out["label"] == "OTILLRÄCKLIGT UNDERLAG"
    assert out["decision"] == "SKIP"
    assert out["sold_comps"] == 0
