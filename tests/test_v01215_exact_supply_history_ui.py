from pathlib import Path

def test_history_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Spara exact-supply observation" in app
    assert "Minst två behövs innan riktning visas" in app
    assert "Spara exact-supply observation" in app
