from src.capital_efficiency_validation import build_capital_efficiency_validation

def row(score,profit,roi=20,days=10,status="sålt"):
    return {"status":status,"capital_efficiency_score_at_capture":score,
            "actual_net_profit":profit,"actual_roi_pct":roi,"days_to_sell":days}

def test_legacy_rows_are_excluded_not_backfilled():
    r=build_capital_efficiency_validation([row(None,100),row(80,50)])
    assert r["captured_completed_count"]==1
    assert r["legacy_or_unscored_completed_count"]==1

def test_open_rows_are_excluded():
    r=build_capital_efficiency_validation([row(90,100,status="köpt")])
    assert r["captured_completed_count"]==0

def test_high_and_lower_cohorts_split_at_65():
    r=build_capital_efficiency_validation([row(65,100),row(64,50)])
    assert r["high"]["count"]==1 and r["lower"]["count"]==1

def test_actual_profit_30d_uses_real_days_to_sell():
    rows=[row(80,100,days=10) for _ in range(5)]
    r=build_capital_efficiency_validation(rows)
    assert r["high"]["median_actual_profit_30d"]==300

def test_direction_supports_when_high_realized_faster_profit():
    rows=[row(80,100,days=10) for _ in range(5)] + [row(50,100,days=30) for _ in range(5)]
    r=build_capital_efficiency_validation(rows)
    assert r["direction"]=="supports"

def test_manual_review_needs_20_and_both_cohorts():
    rows=[row(80,100) for _ in range(10)] + [row(50,50) for _ in range(10)]
    r=build_capital_efficiency_validation(rows)
    assert r["supports_manual_review"] is True
    assert r["automatic_model_changes"] is False
