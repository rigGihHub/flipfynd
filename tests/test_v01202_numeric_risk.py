from pathlib import Path
from src.buy_queue_risk_reward import build_risk_reward


def test_downside_percentage_preserved_without_label():
    out = build_risk_reward({
        "analysis_total_cost": 200,
        "floor_profit_estimate": -50,
        "net_profit_estimate": 80,
    })
    assert out["capital_downside_pct"] == 25.0
    assert out["risk_band"] is None
    assert "empiriskt stöd" in out["note"]


def test_positive_floor_means_zero_capital_downside():
    out = build_risk_reward({
        "analysis_total_cost": 200,
        "floor_profit_estimate": 20,
        "net_profit_estimate": 80,
    })
    assert out["capital_downside_pct"] == 0.0


def test_app_does_not_render_risk_band_label():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "rr['risk_band']" not in app
    assert "Risk visas numeriskt" in app
