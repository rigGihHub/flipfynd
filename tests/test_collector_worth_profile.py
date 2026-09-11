from src.collector_worth_profile import build_collector_worth_profile

def profile(**overrides):
    args=dict(
        player_name="Connor McDavid", player_market_score=95, variant_rung=4,
        rookie_importance_score=90, rookie_importance_matched=True,
        valuable_structure_score=85, valuable_tags=["Rookie-program","Låg numrering"],
        sold_comparable_count=4, valuation_confidence_score=75,
        identity_confidence_score=90, liquidity_score=75,
        features={"grading_company":"PSA","grade":"10","card_number":"201"},
    )
    args.update(overrides)
    return build_collector_worth_profile(**args)

def test_strong_card_needs_player_structure_and_market_support():
    out=profile()
    assert out["verdict"] in {"STARK_SAMLARPROFIL","INTRESSANT"}
    assert out["market_proof_strength"] >= 55
    assert out["creates_market_value"] is False
    assert out["creates_buy_decision"] is False

def test_low_numbered_weak_player_triggers_rarity_trap():
    out=profile(player_market_score=35,sold_comparable_count=0,valuation_confidence_score=10,liquidity_score=20)
    assert any("Raritetsfälla" in x for x in out["hobby_traps"])
    assert out["score"] <= 52

def test_rookie_label_does_not_make_weak_player_valuable():
    out=profile(player_market_score=30,variant_rung=1,valuable_structure_score=35,sold_comparable_count=0)
    assert any("Rookiefälla" in x for x in out["hobby_traps"])
    assert out["verdict"] != "STARK_SAMLARPROFIL"

def test_star_base_card_is_called_out_as_standard_structure():
    out=profile(variant_rung=0,rookie_importance_score=0,rookie_importance_matched=False,valuable_structure_score=20,valuable_tags=[],sold_comparable_count=1,features={})
    assert any("standardkort" in x.casefold() or "bas" in x.casefold() for x in out["hobby_traps"] + out["cautions"])

def test_unknown_grader_gets_no_automatic_premium():
    out=profile(features={"grading_company":"XYZ","grade":"10"})
    assert out["grading_context"]["recognized"] is False
    assert out["grading_context"]["strength"] == 0
