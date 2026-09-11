from pathlib import Path

def test_targeted_market_gap_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "vilken sport som behöver mer marknadsdata först" in app
    assert "Varför denna marknad:" in app
