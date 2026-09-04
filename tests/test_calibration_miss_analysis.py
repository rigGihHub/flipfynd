from src.calibration_miss_analysis import build_miss_analysis, classify_outcome_misses


def sold(**overrides):
    row = {
        "status": "sålt",
        "purchase_price": 75,
        "sale_price": 180,
        "actual_net_profit": 85,
        "expected_net_profit_at_capture": 100,
        "expected_resale_at_capture": 190,
        "max_total_price_at_capture": 100,
        "flip_velocity_days_at_capture": 20,
        "days_to_sell": 22,
    }
    row.update(overrides)
    return row


def test_good_outcome_has_no_detected_miss():
    assert classify_outcome_misses(sold()) == []


def test_detects_supported_price_value_profit_and_velocity_misses():
    keys = {m["key"] for m in classify_outcome_misses(sold(
        purchase_price=130,
        sale_price=120,
        actual_net_profit=-30,
        expected_net_profit_at_capture=90,
        expected_resale_at_capture=200,
        max_total_price_at_capture=100,
        flip_velocity_days_at_capture=20,
        days_to_sell=40,
    ))}
    assert {"paid_over_max", "resale_overestimated", "profit_below_expectation", "slower_than_expected", "actual_loss"} <= keys


def test_small_prediction_noise_is_not_classified_as_miss():
    assert classify_outcome_misses(sold(sale_price=180, expected_resale_at_capture=190, actual_net_profit=80, expected_net_profit_at_capture=95)) == []


def test_pattern_requires_five_occurrences():
    rows = [sold(purchase_price=130, max_total_price_at_capture=100) for _ in range(5)]
    report = build_miss_analysis(rows)
    assert report["primary_pattern"]["key"] == "paid_over_max"
    assert report["primary_pattern"]["enough_for_pattern"] is True


def test_identity_miss_is_not_invented():
    report = build_miss_analysis([sold()])
    assert report["identity_miss_assessed"] is False
    assert report["automatic_weight_changes"] is False


def test_manual_identity_review_is_used_only_when_explicitly_recorded():
    row = sold(outcome_review_reasons=["identity_wrong"])
    misses = classify_outcome_misses(row)
    manual = [m for m in misses if m["key"] == "manual:identity_wrong"]
    assert len(manual) == 1
    assert manual[0]["source"] == "manual_review"
    report = build_miss_analysis([row])
    assert report["identity_miss_assessed"] is True


def test_unknown_manual_review_reason_is_ignored():
    misses = classify_outcome_misses(sold(outcome_review_reasons=["invented_reason"]))
    assert not any(m["source"] == "manual_review" for m in misses)
