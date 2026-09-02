from src.rookie_importance import build_player_rookie_importance


def test_non_rookie_does_not_activate():
    r = build_player_rookie_importance(signals=[], features={"is_rookie": False}, sport="hockey", player_name="A", player_market_score=90, sold_comparable_count=5, identity_confidence_score=90, valuation_confidence_score=90)
    assert r["matched"] is False
    assert r["importance_score"] == 0


def test_young_guns_is_high_importance_but_not_auto_key_without_evidence():
    r = build_player_rookie_importance(signals=[{"label":"Young Guns", "category":"rookie_program", "product_family":"Upper Deck Flagship", "program_family":"Young Guns"}], features={"is_rookie": True, "rookie_program":"Young Guns"}, sport="hockey", player_name="Prospect", player_market_score=90, sold_comparable_count=0, identity_confidence_score=90, valuation_confidence_score=20)
    assert r["importance_score"] >= 80
    assert r["safe_to_call_key_rookie"] is False
    assert "Flagship" in r["tier"]


def test_future_watch_auto_patch_outranks_generic_rookie():
    fwap = build_player_rookie_importance(signals=[{"label":"Future Watch Auto Patch", "category":"rookie_patch_auto", "product_family":"SP Authentic", "program_family":"Future Watch Auto Patch"}], features={"is_rookie": True, "rookie_program":"Future Watch Auto Patch"}, sport="hockey", player_name="Prospect", player_market_score=80, sold_comparable_count=1, identity_confidence_score=85, valuation_confidence_score=50)
    generic = build_player_rookie_importance(signals=[{"label":"Rookie Insert", "category":"rookie_program"}], features={"is_rookie": True}, sport="hockey", player_name="Prospect", player_market_score=80, sold_comparable_count=1, identity_confidence_score=85, valuation_confidence_score=50)
    assert fwap["importance_score"] > generic["importance_score"]


def test_key_rookie_label_requires_strong_local_evidence():
    r = build_player_rookie_importance(signals=[{"label":"Young Guns", "category":"rookie_program", "program_family":"Young Guns"}], features={"is_rookie": True, "rookie_program":"Young Guns"}, sport="hockey", player_name="Prospect", player_market_score=95, sold_comparable_count=4, identity_confidence_score=90, valuation_confidence_score=80)
    assert r["safe_to_call_key_rookie"] is True
    assert r["safe_for_valuation"] is False


def test_low_identity_blocks_key_rookie_claim():
    r = build_player_rookie_importance(signals=[{"label":"Young Guns", "category":"rookie_program", "program_family":"Young Guns"}], features={"is_rookie": True, "rookie_program":"Young Guns"}, sport="hockey", player_name="Prospect", player_market_score=95, sold_comparable_count=5, identity_confidence_score=40, valuation_confidence_score=90)
    assert r["safe_to_call_key_rookie"] is False
    assert r["importance_score"] <= 64
