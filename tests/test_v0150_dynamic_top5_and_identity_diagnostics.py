from pathlib import Path

from src.finding_funnel_diagnostic import build_finding_funnel_diagnostic


def test_readiness_separates_research_identity_from_decision_grade_identity():
    results = [
        {
            "beslut": "SKIP",
            "exact_identity_gate_supports_comp_research": True,
            "exact_identity_gate_supports_exact_comp_search": False,
        },
        {
            "beslut": "SKIP",
            "exact_identity_gate_supports_comp_research": True,
            "exact_identity_gate_supports_exact_comp_search": True,
        },
    ]
    report = build_finding_funnel_diagnostic({}, results)
    rows = {row["key"]: row for row in report["decision_readiness"]}
    assert rows["research_identity"]["count"] == 2
    assert rows["research_identity"]["label"] == "Sökbar identitet för comp-research"
    assert rows["exact_identity"]["count"] == 1
    assert rows["exact_identity"]["label"] == "Beslutsstark exakt identitet"


def test_main_search_renders_dynamic_top_five():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v0.14.30"' in app
    assert "total_limit=5, require_verified_economic_edge=True" in app
    assert "Dynamisk topp 5 i den här sökningen" in app
    assert "verifierade fynd · {review_top_count} värda fortsatt kontroll" in app
    assert 'd3.metric("EJ KÖPKLARA"' in app
    assert 'with st.expander("🔎 Varför blir inget ett verifierat KÖP?", expanded=False)' in app
