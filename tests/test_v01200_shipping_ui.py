from pathlib import Path


def test_shipping_ui_distinguishes_assumed_shipping():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Antagen frakt" in app
    assert "shipping_label" in app


def test_no_old_best_buy_shipping_or_bug():
    text = Path("src/best_buy_decision_card.py").read_text(encoding="utf-8")
    assert 'max_price_shipping_assumption") or item.get("frakt")' not in text
