from src.near_buy_guidance import build_near_buy_guidance


def base_item(**overrides):
    item = {
        "beslut": "SKIP",
        "confidence": 0.50,
        "risk_adjusted_profit": 18,
        "sale_probability": 60,
        "net_profit_estimate": 28,
        "roi_estimate": 0.16,
        "floor_profit_estimate": -5,
        "analysis_total_cost": 100,
        "exact_identity_gate_status": "SÖKBAR",
        "exact_identity_gate_score": 80,
        "sold_comparable_count": 3,
        "comparable_count": 4,
        "valuation_confidence_score": 75,
    }
    item.update(overrides)
    return item


def test_near_buy_lists_actual_threshold_gaps():
    result = build_near_buy_guidance(base_item())
    keys = {x["key"] for x in result["threshold_gaps"]}
    assert "risk_adjusted_profit" in keys
    assert "net_profit_estimate" in keys
    assert "roi_estimate" in keys
    assert result["status"] in {"NÄRA KÖP", "EKONOMIN RÄCKER INTE ÄN"}


def test_identity_blocker_takes_priority_and_caps_readiness():
    result = build_near_buy_guidance(base_item(
        exact_identity_gate_status="LÅST",
        exact_identity_gate_score=25,
        exact_identity_gate_blockers=["Kortnummer saknas."],
        risk_adjusted_profit=50,
        net_profit_estimate=100,
        roi_estimate=0.50,
    ))
    assert result["status"] == "VERIFIERA IDENTITET"
    assert result["readiness_score"] <= 49
    assert "Kortnummer saknas" in result["primary_action"] or "kort" in result["primary_action"].lower()


def test_weak_sold_evidence_is_explicit():
    result = build_near_buy_guidance(base_item(sold_comparable_count=0, valuation_confidence_score=35))
    assert result["status"] == "MER PRISUNDERLAG"
    assert any("2 verifierade" in step for step in result["next_steps"])
    assert result["readiness_score"] <= 59


def test_buy_ready_item_returns_100_without_rewriting_decision():
    result = build_near_buy_guidance(base_item(beslut="KÖP"))
    assert result["readiness_score"] == 100
    assert result["status"] == "KÖP-KLAR"
    assert result["safe_for_valuation"] is False


def test_guidance_contains_no_monetary_revaluation_fields():
    result = build_near_buy_guidance(base_item())
    forbidden = {"market_value", "expected_resale", "max_bid", "max_purchase_price"}
    assert not forbidden.intersection(result)
