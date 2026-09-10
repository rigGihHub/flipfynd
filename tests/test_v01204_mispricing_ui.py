from pathlib import Path

def test_ui_calls_research_candidates_not_new_buys():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Misstänkt felprissatta – extra kontroll" in app
    assert "Research-kandidater, inte nya KÖP" in app
