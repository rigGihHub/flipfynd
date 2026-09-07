from src.comp_evidence_ladder import build_exact_evidence_ladder, build_premium_evidence_ladder


def test_exact_only_is_valuation_eligible():
    r=build_exact_evidence_ladder({"unlocked":True,"exact":[{"sold":True}],"near":[{"sold":True}]})
    assert r["valuation_basis_count"]==1
    assert r["levels"][0]["valuation_eligible"] is True
    assert r["levels"][1]["valuation_eligible"] is False


def test_player_only_detected_from_weak_verified_sale():
    r=build_exact_evidence_ladder({"unlocked":True,"weak":[{"sold":True,"matches":["spelare"]}]})
    level={x["key"]:x for x in r["levels"]}
    assert level["PLAYER_ONLY"]["count"]==1


def test_unverified_player_only_not_counted():
    r=build_exact_evidence_ladder({"unlocked":True,"weak":[{"sold":False,"matches":["spelare"]}]})
    level={x["key"]:x for x in r["levels"]}
    assert level["PLAYER_ONLY"]["count"]==0


def test_rejected_is_visible_but_never_eligible():
    r=build_exact_evidence_ladder({"unlocked":True,"rejected":[{"conflicts":["parallel"]}]})
    level={x["key"]:x for x in r["levels"]}
    assert level["REJECTED"]["count"]==1
    assert level["REJECTED"]["valuation_eligible"] is False


def test_exact_ladder_locked_when_hunt_locked():
    assert build_exact_evidence_ladder({"unlocked":False})["status"]=="LOCKED"


def test_premium_only_exact_is_valuation_eligible():
    r=build_premium_evidence_ladder({"active":True,"exact":[{}],"near":[{}],"safe_for_valuation":False})
    levels={x["key"]:x for x in r["levels"]}
    assert levels["EXACT_PREMIUM"]["valuation_eligible"] is True
    assert levels["NEAR_PREMIUM"]["valuation_eligible"] is False


def test_premium_insufficient_count_preserved():
    r=build_premium_evidence_ladder({"active":True,"insufficient_count":3})
    levels={x["key"]:x for x in r["levels"]}
    assert levels["INSUFFICIENT"]["count"]==3


def test_premium_safe_flag_is_descriptive_only():
    r=build_premium_evidence_ladder({"active":True,"exact":[{},{}],"safe_for_valuation":True})
    assert r["safe_for_valuation"] is True
    assert r["valuation_basis_count"]==2
