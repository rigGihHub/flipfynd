from pathlib import Path

from src.seller_top5 import seller_result_tier


def test_plain_unverified_card_is_not_presented_as_a_find():
    assert seller_result_tier({"decision": "SKIP", "collector_signal_score": 0}) == "WEAK"
    assert seller_result_tier({"title": "Haaland Red 7/25", "price": 50, "decision": "SKIP", "collector_signal_score": 18}) == "RESEARCH"
    assert seller_result_tier({"title": "Unknown card", "price": 50, "decision": "KÖP", "collector_signal_score": 0}) == "RESEARCH"


def test_seller_ui_uses_truthful_headings():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Topp 5 hittills" in app
    assert "osäkert underlag" in app
    assert "verifierade fynd i listan" in app
    assert "seller_result_tier(row)" in app
