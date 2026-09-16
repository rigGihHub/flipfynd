from pathlib import Path


def test_latest_refresh_replaces_coverage_autopilot():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Uppdatera senaste annonser" in app
    assert "Fler hämtningsalternativ" in app
    assert "top_market_autopilot" not in app
    assert "Ta med äldre sparade annonser" in app
