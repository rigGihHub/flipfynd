from pathlib import Path

def test_segment_coverage_runs_after_budget_coverage():
    pipeline=Path("src/ordinary_analysis_pipeline_v2.py").read_text(encoding="utf-8")
    pos_budget=pipeline.find("add_budget_coverage_indices(")
    pos_segment=pipeline.find("add_segment_coverage_indices(",pos_budget)
    assert pos_budget > 0
    assert pos_segment > pos_budget
    assert 'debug["segment_coverage_added"]' in pipeline
