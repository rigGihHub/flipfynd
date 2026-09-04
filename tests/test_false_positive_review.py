from src.false_positive_review import build_false_positive_review, classify_false_positive


def sold_buy(actual, expected=100, score=90, **extra):
    row = {
        "status": "sålt",
        "recommended_decision": "KÖP",
        "actual_net_profit": actual,
        "expected_net_profit_at_capture": expected,
        "deal_score_at_capture": score,
    }
    row.update(extra)
    return row


def test_loss_is_false_positive():
    result = classify_false_positive(sold_buy(-10))
    assert result["eligible"] is True
    assert result["is_false_positive"] is True
    assert "actual_loss" in result["reasons"]


def test_small_forecast_noise_is_not_false_positive():
    result = classify_false_positive(sold_buy(80, expected=100))
    assert result["is_false_positive"] is False


def test_large_profit_shortfall_can_be_false_positive_without_loss():
    result = classify_false_positive(sold_buy(40, expected=120))
    assert result["is_false_positive"] is True
    assert result["reasons"] == ["large_profit_shortfall"]


def test_unsold_or_non_buy_is_not_eligible():
    assert classify_false_positive({"status": "köpt", "recommended_decision": "KÖP"})["eligible"] is False
    assert classify_false_positive({"status": "sålt", "recommended_decision": "KANSKE", "actual_net_profit": -50})["eligible"] is False


def test_pattern_gate_requires_five_completed_buy_recommendations():
    assert build_false_positive_review([sold_buy(-10)] * 4)["supports_pattern_review"] is False
    assert build_false_positive_review([sold_buy(-10)] * 5)["supports_pattern_review"] is True


def test_segments_require_own_sample_and_do_not_change_weights():
    rows = [sold_buy(-10, information_edge_candidate_at_capture=True) for _ in range(5)]
    review = build_false_positive_review(rows)
    edge = next(x for x in review["segments"] if x["key"] == "information_edge")
    assert edge["enough_for_pattern"] is True
    assert edge["false_positive_rate_pct"] == 100.0
    assert review["automatic_weight_changes"] is False
