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


def test_dynamic_percent_reasons_are_normalised_into_stable_categories():
    results = [
        {"beslut": "SKIP", "decision_diagnostics": ["Analyssäkerhet 5%; minst 28 % krävs för ett köpbeslut."]},
        {"beslut": "SKIP", "decision_diagnostics": ["Analyssäkerhet 24%; minst 28 % krävs för ett köpbeslut."]},
        {"beslut": "SKIP", "decision_diagnostics": ["Konservativt scenario motsvarar -84% av inköpskostnaden; KÖP kräver minst -25 %."]},
        {"beslut": "SKIP", "decision_diagnostics": ["Konservativt scenario motsvarar -93% av inköpskostnaden; KÖP kräver minst -25 %."]},
    ]
    out = build_finding_funnel_diagnostic({"final_results": 4}, results)
    labels = {row["label"]: row["count"] for row in out["blockers"]}
    assert labels["För låg analyssäkerhet"] == 2
    assert labels["För svag värderingsmarginal"] == 2
    assert labels.get("Övrigt", 0) == 0


def test_decision_readiness_uses_existing_evidence_fields_only():
    results = [
        {
            "beslut": "KÖP",
            "exact_identity_gate_supports_exact_comp_search": True,
            "sold_comparable_count": 3,
            "valuation_display_safe": True,
            "analysis_confidence": 0.61,
        },
        {
            "beslut": "SKIP",
            "exact_identity_gate_supports_exact_comp_search": False,
            "sold_comparable_count": 0,
            "valuation_display_safe": False,
            "analysis_confidence": 0.05,
        },
    ]
    out = build_finding_funnel_diagnostic({"final_results": 2}, results)
    readiness = {row["key"]: row for row in out["decision_readiness"]}
    assert readiness["analysed"]["count"] == 2
    assert readiness["exact_identity"]["count"] == 1
    assert readiness["sold"]["count"] == 1
    assert readiness["valuation"]["count"] == 1
    assert readiness["confidence"]["count"] == 1
    assert readiness["buy"]["count"] == 1
