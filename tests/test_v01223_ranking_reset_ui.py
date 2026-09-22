from pathlib import Path

def test_ui_separates_potential_and_certainty():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Fyndpotential" in app
    assert '"Säkerhet"' in app
    assert "Verifierat fynd" in app
    assert "Lovande · undersök" in app
    assert "Inte fynd · bäst av resten" in app

def test_budget_coverage_integrated_before_full_analysis():
    pipeline=Path("src/ordinary_analysis_pipeline_v2.py").read_text(encoding="utf-8")
    assert "add_budget_coverage_indices(" in pipeline
    assert 'debug["budget_coverage_added"]' in pipeline
