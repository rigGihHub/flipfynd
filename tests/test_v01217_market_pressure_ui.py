from pathlib import Path

def test_market_pressure_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Market Pressure – observerade fakta" in app
    assert "Ingen demand-signal" in app
    assert "för få verifierade exakta försäljningar för prisriktning" in app
    assert "Market Pressure – observerade fakta" in app
