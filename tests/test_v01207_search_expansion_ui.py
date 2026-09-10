from pathlib import Path

def test_ui_explains_search_expansion_is_discovery_only():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Search Expansion – fler sökvägar till fynd" in app
    assert "skapar aldrig kortidentitet, marknadsvärde eller KÖP" in app
