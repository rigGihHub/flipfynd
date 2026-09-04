from src.calibration_dashboard import build_calibration_dashboard


def _sold(i, profit=100, reasons=None):
    return {
        "id": str(i),
        "status": "sålt",
        "actual_net_profit": profit,
        "purchase_price": 50,
        "sale_price": 170,
        "days_to_sell": 10,
        "recommended_decision": "KÖP",
        "information_edge_candidate_at_capture": True,
        "outcome_review_reasons": reasons or [],
    }


def test_dashboard_empty_state_is_conservative():
    out = build_calibration_dashboard([])
    assert out["readiness"] == "empty"
    assert out["sold_count"] == 0
    assert out["automatic_weight_changes"] is False


def test_dashboard_descriptive_gate_at_five():
    out = build_calibration_dashboard([_sold(i) for i in range(5)])
    assert out["readiness"] == "descriptive"
    assert out["overall"]["sample"]["supports_description"] is True
    assert out["overall"]["sample"]["supports_tendency"] is False


def test_dashboard_tendency_gate_at_ten():
    out = build_calibration_dashboard([_sold(i) for i in range(10)])
    assert out["readiness"] == "tendency"
    assert out["best_tendency"] is not None
    assert out["best_tendency"]["count"] >= 10


def test_dashboard_review_coverage_uses_explicit_reviews_only():
    rows = [_sold(i, reasons=["identity_wrong"] if i < 3 else []) for i in range(10)]
    out = build_calibration_dashboard(rows)
    assert out["reviewed_count"] == 3
    assert out["review_rate_pct"] == 30.0
    assert any(x["kind"] == "review" for x in out["attention"])


def test_dashboard_never_enables_automatic_weight_changes():
    out = build_calibration_dashboard([_sold(i) for i in range(30)])
    assert out["readiness"] == "review_ready"
    assert out["automatic_weight_changes"] is False
