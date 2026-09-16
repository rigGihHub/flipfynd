from pathlib import Path

def test_latest_scope_and_older_scope_are_explained():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Sökningen fokuserar på senaste snabba hämtningen." in app
    assert "Ta med äldre sparade annonser" in app
