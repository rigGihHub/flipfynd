from pathlib import Path

def test_segment_coverage_runs_after_budget_coverage():
    app=Path("app.py").read_text(encoding="utf-8")
    pos_budget=app.find("add_budget_coverage_indices(")
    pos_segment=app.find("add_segment_coverage_indices(",pos_budget)
    assert pos_budget > 0
    assert pos_segment > pos_budget
    assert 'debug["segment_coverage_added"]' in app
