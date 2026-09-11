from pathlib import Path

def test_collector_worth_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Samlarprofil:" in app
    assert "Varför är kortet samlarvärt – eller inte?" in app
    assert "Samlarfälla:" in app
