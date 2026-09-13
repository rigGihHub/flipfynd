from src.autograph_authenticity_gate import classify_autograph, safe_visual_is_auto


def test_silver_script_is_not_autograph():
    r = classify_autograph(title="2021-22 MVP Hockey Silver Script #119 Nicklas Backstrom")
    assert r["status"] == "printed_or_facsimile"
    assert r["is_certified_autograph"] is False
    assert r["blocks_autograph_premium"] is True


def test_printed_visual_signature_is_blocked():
    f = {"autograph_visible": "yes", "autograph_type": "printed_or_facsimile"}
    assert safe_visual_is_auto(f) is False


def test_on_card_visual_signal_can_enter_auto_path():
    f = {"autograph_visible": "yes", "autograph_type": "on_card"}
    assert safe_visual_is_auto(f) is True
