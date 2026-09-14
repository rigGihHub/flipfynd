from pathlib import Path

from src.seller_top5 import seller_result_tier


def test_plain_unverified_card_is_not_presented_as_a_find():
    assert seller_result_tier({"decision": "SKIP", "collector_signal_score": 0}) == "WEAK"
    assert seller_result_tier({"decision": "SKIP", "collector_signal_score": 18}) == "RESEARCH"
    assert seller_result_tier({"decision": "KÖP", "collector_signal_score": 0}) == "FIND"


def test_seller_ui_uses_truthful_headings():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Inga starka fynd hittade ännu" in app
    assert "Kandidater värda fortsatt kontroll" in app
    assert "APP_VERSION = \"v0.12.98\"" in app
