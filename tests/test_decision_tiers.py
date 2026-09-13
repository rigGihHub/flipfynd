from src.decision_tiers import build_decision_tiers


def test_verified_buy_requires_evidence_not_just_score():
    weak={
        "titel":"Weak",
        "beslut":"SKIP",
        "deal_score":94,
        "confidence":5,
        "sold_comparable_count":0,
    }
    out=build_decision_tiers([weak])
    row=out["rows"][0]
    assert row["tier"]!="VERIFIED"
    assert row["potential"]==94
    assert row["certainty"]==5


def test_verified_tier_requires_buy_identity_sold_and_safe_value():
    strong={
        "titel":"Strong",
        "beslut":"KÖP",
        "deal_score":80,
        "ranking_confidence_score":85,
        "sold_comparable_count":3,
        "exact_identity_gate_supports_exact_comp_search":True,
        "valuation_display_safe":True,
        "market_value_estimate":500,
    }
    row=build_decision_tiers([strong])["rows"][0]
    assert row["tier"]=="VERIFIED"
    assert row["market_value"]==500


def test_unsafe_value_is_hidden():
    item={
        "titel":"X",
        "deal_score":70,
        "confidence":40,
        "valuation_display_safe":False,
        "market_value_estimate":999,
    }
    row=build_decision_tiers([item])["rows"][0]
    assert row["market_value"] is None


def test_low_guide_context_is_demoted_in_fallback_main_list():
    cheap={
        "titel":"Cheap superstar insert",
        "beslut":"SKIP",
        "deal_score":88,
        "ranking_confidence_score":80,
        "sold_comparable_count":0,
        "exact_identity_gate_supports_exact_comp_search":True,
        "exact_identity_gate_supports_comp_research":True,
        "guide_triage":{"status":"LOW_GUIDE_CONTEXT","ungraded_usd":1.5,"priority":3},
        "collector_worth_score":28,
        "card_hierarchy_score":20,
    }
    stronger={
        "titel":"Numbered rookie target",
        "beslut":"SKIP",
        "deal_score":72,
        "ranking_confidence_score":70,
        "sold_comparable_count":0,
        "exact_identity_gate_supports_comp_research":True,
        "collector_worth_score":76,
        "card_hierarchy_score":82,
        "features":{"is_rookie":True,"is_serial_numbered":True},
    }
    out=build_decision_tiers([cheap,stronger], total_limit=2, require_verified_economic_edge=True)
    assert out["fallback_investigate_mode"] is True
    assert out["rows"][0]["title"]=="Numbered rookie target"
    assert out["rows"][1]["title"]=="Cheap superstar insert"
    assert out["rows"][1]["guide_ungraded_usd"]==1.5
    assert out["rows"][1]["decision"]=="UNDERSÖK"


def test_low_value_noise_is_hidden_when_three_better_candidates_exist():
    cheap={
        "titel":"$1.50 base insert",
        "beslut":"SKIP",
        "deal_score":91,
        "ranking_confidence_score":82,
        "sold_comparable_count":0,
        "exact_identity_gate_supports_exact_comp_search":True,
        "exact_identity_gate_supports_comp_research":True,
        "guide_triage":{"status":"LOW_GUIDE_CONTEXT","ungraded_usd":1.5,"priority":3},
        "collector_worth_score":24,
        "card_hierarchy_score":18,
    }
    better=[]
    for idx in range(3):
        better.append({
            "titel":f"Better {idx}",
            "beslut":"SKIP",
            "deal_score":70-idx,
            "ranking_confidence_score":65,
            "sold_comparable_count":0,
            "exact_identity_gate_supports_comp_research":True,
            "collector_worth_score":70,
            "card_hierarchy_score":72,
            "features":{"is_serial_numbered":True},
            "player_name":f"Player {idx}",
        })
    out=build_decision_tiers([cheap]+better, total_limit=3, require_verified_economic_edge=True)
    titles=[row["title"] for row in out["rows"]]
    assert "$1.50 base insert" not in titles
    assert out["suppressed_low_value_count"]==1
    assert out["suppressed_low_value_titles"]==["$1.50 base insert"]


def test_low_value_noise_is_kept_when_not_enough_better_candidates_exist():
    cheap={
        "titel":"Only cheap fallback",
        "beslut":"SKIP",
        "deal_score":91,
        "ranking_confidence_score":82,
        "sold_comparable_count":0,
        "exact_identity_gate_supports_exact_comp_search":True,
        "guide_triage":{"status":"LOW_GUIDE_CONTEXT","ungraded_usd":1.25,"priority":3},
        "collector_worth_score":20,
        "card_hierarchy_score":15,
    }
    better={
        "titel":"One better option",
        "beslut":"SKIP",
        "deal_score":70,
        "ranking_confidence_score":65,
        "sold_comparable_count":0,
        "exact_identity_gate_supports_comp_research":True,
        "collector_worth_score":70,
        "card_hierarchy_score":72,
    }
    out=build_decision_tiers([cheap,better], total_limit=3, require_verified_economic_edge=True)
    assert "Only cheap fallback" in [row["title"] for row in out["rows"]]
    assert out["suppressed_low_value_count"]==0


def test_verified_buy_not_demoted_by_low_guide_context():
    verified={
        "titel":"Verified buy",
        "beslut":"KÖP",
        "deal_score":75,
        "ranking_confidence_score":90,
        "sold_comparable_count":3,
        "exact_identity_gate_supports_exact_comp_search":True,
        "valuation_display_safe":True,
        "market_value_estimate":500,
        "analysis_total_cost":200,
        "dynamic_max_total_price":300,
        "guide_triage":{"status":"LOW_GUIDE_CONTEXT","ungraded_usd":1.5,"priority":3},
    }
    row=build_decision_tiers([verified], require_verified_economic_edge=True)["rows"][0]
    assert row["tier"]=="VERIFIED"
    assert row["decision"]=="KÖP"
    assert row["market_value"]==500
