from pathlib import Path

def test_ui_is_explicitly_not_buy_signal():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Market Gap – tunt utbud att undersöka" in app
    assert "Det betyder inte automatiskt fynd eller KÖP" in app
    assert "Market Gap – tunt utbud att undersöka" in app
