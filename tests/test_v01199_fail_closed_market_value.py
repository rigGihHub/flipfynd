from pathlib import Path
from src.novice_navigation import build_watch_view


def test_novice_market_value_defaults_to_hidden_when_safety_flag_missing():
    row = {
        "titel": "Test card",
        "beslut": "BEVAKA",
        "expected_resale": 500,
        "analysis_total_cost": 100,
    }
    out = build_watch_view([row])
    assert out["rows"][0]["market_value"] is None


def test_app_uses_fail_closed_display_default():
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'item.get("valuation_display_safe", False)' in app
