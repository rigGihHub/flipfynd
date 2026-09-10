from pathlib import Path

def test_pressure_drilldown_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Varför lyfts" in app
    assert "Vad saknas innan KÖP ens kan övervägas?" in app
    assert "Verifierade exakta SOLD i perioden" in app
    assert "Exact-supply-historik" in app
    assert "Varför lyfts" in app
