from src.analyzer import analyze_item, _premium_identity_needs_sold_evidence


def test_autograph_requires_sold_evidence_for_displayed_value():
    item = {
        "titel": "Lucas Bergvall Topps Finest Autograph RC",
        "pris": 499,
        "frakt": 29,
        "raw_text": "Köp nu Topps Finest autograph rookie",
        "url": "https://www.tradera.com/item/293311/example",
    }
    result = analyze_item(item, all_items=[], mode="full", sport="football")
    assert result["premium_identity_requires_sold_evidence"] is True
    assert result["valuation_display_safe"] is False
    assert "autograf" in result["valuation_display_note"].lower()
    assert result["value_source"] == "heuristic_only"


def test_plain_base_card_does_not_trigger_premium_display_guard():
    assert _premium_identity_needs_sold_evidence({"is_auto": False, "is_patch": False}) is False


def test_low_serial_triggers_premium_display_guard():
    assert _premium_identity_needs_sold_evidence({"is_low_serial": True}) is True
