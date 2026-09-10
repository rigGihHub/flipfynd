from pathlib import Path

def test_market_sweep_runs_before_discovery_fallback():
    app=Path("app.py").read_text(encoding="utf-8")
    pos_sweep=app.find("market_sweep_indices = select_market_sweep_indices")
    pos_discovery=app.find("discovery_indices = select_discovery_indices", pos_sweep)
    assert pos_sweep > 0
    assert pos_discovery > pos_sweep
    assert 'debug["market_sweep_deepened"]' in app

def test_market_sweep_release_or_later():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "select_market_sweep_indices" in app
