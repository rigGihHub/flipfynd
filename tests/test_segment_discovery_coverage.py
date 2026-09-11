from src.segment_discovery_coverage import (
    add_segment_coverage_indices,
    segment_key,
    segment_coverage_summary,
)

def c(price, score, player, title="", fast_extra=None):
    fast={"rank_score":score,"player_name":player}
    fast.update(fast_extra or {})
    return ({"pris":price,"titel":title},fast,{})

def test_segment_key_separates_price_sale_and_object_type():
    item,fast,_=c(300,50,"A","Köp nu")
    assert segment_key(item,fast,1000)==("mid","buy-now","single")
    item2,fast2,_=c(10,50,"B","Utropspris",{"is_lot":True})
    assert segment_key(item2,fast2,1000)==("micro","auction","lot")

def test_selector_adds_missing_mid_or_upper_segment_before_more_micro_noise():
    candidates=[
        c(10,100,"A","Köp nu"),
        c(20,95,"B","Köp nu"),
        c(300,80,"C","Köp nu"),
        c(700,70,"D","Utropspris"),
    ]
    selected,added=add_segment_coverage_indices(
        candidates,[0,1],budget=1000,extra_slots=1,hard_cap=3
    )
    assert added[0] in {2,3}

def test_selector_respects_hard_cap():
    candidates=[c(100*i,100-i,str(i),"Köp nu") for i in range(1,10)]
    selected,added=add_segment_coverage_indices(
        candidates,[0,1,2],budget=1000,extra_slots=6,hard_cap=5
    )
    assert len(selected)<=5

def test_summary_is_descriptive_only():
    candidates=[c(300,80,"C","Köp nu")]
    out=segment_coverage_summary(candidates,[0],1000)
    assert out["segment_count"]==1
    assert out["creates_new_score"] is False
    assert out["creates_new_decision"] is False
