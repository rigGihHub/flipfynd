from pathlib import Path

def test_pressure_research_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Pressure Research – kort värda extra kontroll" in app
    assert "manuell researchkö, inte en KÖP-lista" in app
    assert "Ingen ny score skapas" in app
    assert "Pressure Research – kort värda extra kontroll" in app
