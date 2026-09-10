from pathlib import Path

def test_market_autopilot_replaces_required_manual_choice():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "En knapp räcker" in app
    assert "top_market_autopilot" in app
    assert "manuella reservverktyg" in app
    assert 'APP_VERSION = "v0.12.24"' in app
