from pathlib import Path

def test_auto_research_ui_is_low_click():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Automatisk research" in app
    assert "utan extra knapptryckningar" in app
    assert "Enda nästa steget" in app
