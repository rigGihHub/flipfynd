from src.seller_recall_diagnostics import (
    build_seller_coverage_funnel,
    evaluate_labelled_recall,
)


def test_production_funnel_calls_coverage_coverage_not_recall():
    out = build_seller_coverage_funnel(
        inventory_unique=400,
        quick_selected=120,
        quick_success=118,
        full_success=24,
        cumulative_full_unique=48,
        cumulative_full_remaining=352,
    )
    assert out["quick_coverage_pct_this_run"] == 29.5
    assert out["cumulative_full_coverage_pct"] == 12.0
    assert out["recall_measured"] is False
    assert out["inventory_analysis_complete"] is False


def test_labelled_portfolio_measures_selection_and_result_recall():
    out = evaluate_labelled_recall(
        {"find-1", "find-2", "find-3", "find-4"},
        {"find-1", "find-2", "find-3", "ordinary"},
        {"find-1", "find-2", "ordinary"},
    )
    assert out["selection_recall_pct"] == 75.0
    assert out["result_recall_pct"] == 50.0
    assert out["missed_before_full_analysis"] == ["find-4"]
    assert out["missed_after_full_analysis"] == ["find-3"]
