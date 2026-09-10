from pathlib import Path

def test_exact_supply_ui_is_fail_closed():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Exact Card Supply – kontrollera just det här kortet" in app
    assert "Tradera-träffarna är kandidater" in app
    assert "måste nu passera vanlig FlipFynd-analys" in app
    assert "Exact Card Supply – kontrollera just det här kortet" in app
