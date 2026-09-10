from src.finding_funnel_diagnostic import build_finding_funnel_diagnostic


def test_funnel_preserves_stage_counts_and_decisions():
    debug = {
        "total_items": 100,
        "after_sport": 80,
        "valid_price": 70,
        "within_budget": 50,
        "after_search": 40,
        "after_sale_type": 40,
        "after_feature_filters": 35,
        "final_results": 30,
    }
    results = [
        {"beslut": "KÖP"},
        {"beslut": "KANSKE", "decision_diagnostics": ["För få sold comps."]},
        {"beslut": "SKIP", "decision_diagnostics": ["Kortidentitet behöver verifieras."]},
    ]
    out = build_finding_funnel_diagnostic(debug, results)
    assert out["stages"][-1]["count"] == 30
    assert out["decisions"] == {"KÖP": 1, "BEVAKA": 1, "SKIP": 1}
    assert out["creates_new_decision"] is False


def test_funnel_counts_existing_blocker_categories_without_upgrading():
    results = [
        {"beslut": "SKIP", "decision_diagnostics": ["Kortidentitet osäker."]},
        {"beslut": "SKIP", "decision_diagnostics": ["För få verifierade sold comps."]},
        {"beslut": "KANSKE", "decision_diagnostics": ["ROI och vinstmarginal för låg."]},
    ]
    out = build_finding_funnel_diagnostic({"final_results": 3}, results)
    labels = {row["label"]: row["count"] for row in out["blockers"]}
    assert labels["Osäker kortidentitet"] == 1
    assert labels["För svagt prisunderlag"] == 1
    assert labels["För liten ekonomisk marginal"] == 1
    assert out["decisions"]["KÖP"] == 0


def test_funnel_identifies_biggest_filter_drop():
    debug = {
        "total_items": 100,
        "after_sport": 90,
        "valid_price": 80,
        "within_budget": 20,
        "after_search": 20,
        "after_sale_type": 20,
        "after_feature_filters": 20,
        "final_results": 20,
    }
    out = build_finding_funnel_diagnostic(debug, [])
    assert out["biggest_drop"]["from"] == "Har pris"
    assert out["biggest_drop"]["to"] == "Inom budget"
    assert out["biggest_drop"]["drop"] == 60
