from src.card_hierarchy_engine import build_card_hierarchy_engine

def test_young_guns_gets_strong_hobby_hierarchy():
    out=build_card_hierarchy_engine(
        sport="hockey",
        signals=[{
            "label":"Young Guns Exclusives",
            "product_family":"Upper Deck Series",
            "program_family":"Young Guns",
            "category":"rookie_parallel",
            "print_run":100,
        }],
        features={"identity_confidence_score":90},
    )
    assert out["score"]>=80
    assert out["tier"] in {"TIER_A","TIER_B"}
    assert out["creates_market_value"] is False
    assert out["creates_buy_decision"] is False

def test_future_watch_and_the_cup_are_high_structural_hierarchy():
    fwa=build_card_hierarchy_engine(
        sport="hockey",
        signals=[{
            "label":"Future Watch Autograph",
            "product_family":"SP Authentic",
            "program_family":"Future Watch",
            "category":"rookie_auto",
        }],
        features={"identity_confidence_score":90},
    )
    cup=build_card_hierarchy_engine(
        sport="hockey",
        signals=[{
            "label":"The Cup Rookie Auto Patch",
            "product_family":"The Cup",
            "category":"rookie_patch_auto",
        }],
        features={"identity_confidence_score":90},
    )
    assert fwa["score"]>=88
    assert cup["score"]>=94

def test_generic_rc_is_not_treated_like_verified_key_rookie():
    out=build_card_hierarchy_engine(
        sport="hockey",
        signals=[],
        features={"is_rookie":True,"identity_confidence_score":30},
    )
    assert out["score"]<=64
    assert any("RC/rookie" in x for x in out["hobby_traps"])

def test_football_chrome_chase_gets_context_not_price():
    out=build_card_hierarchy_engine(
        sport="football",
        signals=[{
            "label":"Topps Chrome Helix",
            "product_family":"Topps Chrome UEFA",
            "program_family":"Topps Chrome Chase Inserts",
            "category":"ssp_insert",
        }],
        features={"identity_confidence_score":90},
    )
    assert out["score"]>=84
    assert out["safe_for_valuation"] is False
