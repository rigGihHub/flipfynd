from src.segment_yield_learning import build_segment_yield_report, best_observed_segments

def verified_item(price=300, title="Köp nu"):
    return {
        "pris":price,
        "titel":title,
        "beslut":"KÖP",
        "deal_score":80,
        "ranking_confidence_score":80,
        "sold_comparable_count":3,
        "exact_identity_gate_supports_exact_comp_search":True,
        "valuation_display_safe":True,
    }

def test_verified_segment_yield_is_observational_only():
    items=[verified_item() for _ in range(8)]
    out=build_segment_yield_report(items,budget=1000,minimum_hits=8)
    row=out["rows"][0]
    assert row["segment"]=="mid/buy-now/single"
    assert row["verified"]==8
    assert row["evidence_status"]=="VERIFIERAD_YIELD_OBSERVERAD"
    assert out["can_auto_tune"] is False
    assert out["can_change_buy_rules"] is False
    assert out["can_change_analysis_budget"] is False
    assert out["creates_new_score"] is False

def test_small_sample_is_not_compared():
    out=build_segment_yield_report([verified_item()],budget=1000,minimum_hits=8)
    assert out["rows"][0]["evidence_status"]=="OTILLRÄCKLIGT_UNDERLAG"
    assert best_observed_segments(out)==[]

def test_segments_are_split_by_listing_type_and_lot():
    buy=verified_item()
    auction=verified_item(title="Utropspris")
    lot=verified_item()
    lot["is_lot"]=True
    out=build_segment_yield_report([buy,auction,lot],budget=1000,minimum_hits=1)
    segments={r["segment"] for r in out["rows"]}
    assert "mid/buy-now/single" in segments
    assert "mid/auction/single" in segments
    assert "mid/buy-now/lot" in segments

def test_promising_without_verified_is_not_called_verified():
    item={
        "pris":100,
        "titel":"Köp nu",
        "beslut":"BEVAKA",
        "deal_score":70,
        "ranking_confidence_score":30,
        "sold_comparable_count":0,
        "valuation_display_safe":False,
    }
    out=build_segment_yield_report([item]*8,budget=1000,minimum_hits=8)
    row=out["rows"][0]
    assert row["verified"]==0
    assert row["promising"]==8
    assert row["evidence_status"]=="LOVANDE_YIELD_OBSERVERAD"
