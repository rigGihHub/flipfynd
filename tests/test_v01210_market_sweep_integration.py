from pathlib import Path

def test_market_sweep_runs_before_discovery_fallback():
    pipeline=Path("src/ordinary_analysis_pipeline_v2.py").read_text(encoding="utf-8")
    pos_sweep=pipeline.find("market_sweep_indices = select_market_sweep_indices")
    pos_discovery=pipeline.find("discovery_indices = select_discovery_indices", pos_sweep)
    assert pos_sweep > 0
    assert pos_discovery > pos_sweep
    assert 'debug["market_sweep_deepened"]' in pipeline

def test_market_sweep_release_or_later():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "select_market_sweep_indices" in app


def test_no_buy_rescue_pass_has_capacity_beyond_first_deep_cap():
    pipeline=Path("src/ordinary_analysis_pipeline_v2.py").read_text(encoding="utf-8")
    assert "rescue_hard_cap = min(len(candidates), dynamic_deep_cap + 15)" in pipeline
    assert "total_hard_cap=rescue_hard_cap" in pipeline
