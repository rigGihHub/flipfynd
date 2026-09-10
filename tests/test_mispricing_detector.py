from src.mispricing_detector import build_mispricing_hypothesis, build_mispricing_review_queue


def test_no_signal_does_not_invent_mispricing():
    out=build_mispricing_hypothesis({})
    assert out["status"]=="NO_SIGNAL"
    assert out["price_gap_supported"] is False
    assert out["can_create_market_value"] is False
    assert out["can_create_buy_decision"] is False


def test_misclassified_signal_is_research_only_without_supported_gap():
    out=build_mispricing_hypothesis({
        "misclassified_card_candidate":True,
        "misclassified_card_reasons":["Variant saknas i titeln."],
        "exact_identity_gate_supports_exact_comp_search":False,
        "sold_comparable_count":0,
        "valuation_display_safe":False,
    })
    assert out["status"]=="RESEARCH_HYPOTHESIS"
    assert out["review_only"] is True
    assert "possible-misclassification" in out["hypothesis_types"]
    assert out["blockers"]


def test_existing_supported_gap_may_be_described_as_supported():
    out=build_mispricing_hypothesis({
        "mispriced_rookie_candidate":True,
        "mispriced_rookie_price_gap_supported":True,
        "exact_identity_gate_supports_exact_comp_search":True,
        "sold_comparable_count":2,
        "valuation_display_safe":True,
    })
    assert out["status"]=="SUPPORTED_PRICE_GAP"
    assert out["price_gap_supported"] is True


def test_variant_structure_alone_never_becomes_supported_price_gap():
    out=build_mispricing_hypothesis({
        "variant_hierarchy_variant_rung":4,
        "valuable_card_tags":["SSP / case hit"],
    })
    assert out["status"]=="RESEARCH_HYPOTHESIS"
    assert out["price_gap_supported"] is False


def test_queue_reuses_existing_priority_without_new_score():
    q=build_mispricing_review_queue([
        {"titel":"A","is_hidden_find_candidate":True,"rank_score":10},
        {"titel":"B","misclassified_card_candidate":True,"misclassified_card_price_gap_supported":True,"rank_score":1},
    ])
    assert q["rows"][0]["title"]=="B"
    assert q["creates_new_decision"] is False
    assert q["creates_new_value"] is False
