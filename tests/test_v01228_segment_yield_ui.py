from pathlib import Path

def test_segment_yield_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Vilka delar av marknaden ger bäst fyndunderlag?" in app
    assert "ändrar inte KÖP-regler eller analysbudget automatiskt" in app
