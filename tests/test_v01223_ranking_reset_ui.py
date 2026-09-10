from pathlib import Path

def test_ui_separates_potential_and_certainty():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Fyndpotential" in app
    assert 'metric("Säkerhet"' in app
    assert "Bästa verifierade fynd" in app
    assert "Lovande – behöver verifieras" in app
    assert "Bästa av resten" in app

def test_budget_coverage_integrated_before_full_analysis():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "add_budget_coverage_indices(" in app
    assert 'debug["budget_coverage_added"]' in app
