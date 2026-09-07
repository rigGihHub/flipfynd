from src.capital_efficiency import build_capital_efficiency, capital_efficiency_sort_key

def vel(days=20):
    return {"expected_days": days, "evidence": "verified_sold_velocity"}

def test_abstains_without_verified_velocity():
    r=build_capital_efficiency(total_cost=100,net_profit=70,floor_profit=20,sale_probability=80,liquidity_score=80,velocity={})
    assert r["score"] is None and r["label"]=="Ej bedömd"

def test_fast_small_flip_can_beat_slow_large_flip():
    fast=build_capital_efficiency(total_cost=100,net_profit=70,floor_profit=10,sale_probability=85,liquidity_score=85,velocity=vel(10))
    slow=build_capital_efficiency(total_cost=1000,net_profit=300,floor_profit=-100,sale_probability=70,liquidity_score=55,velocity=vel(60))
    assert fast["score"] > slow["score"]
    assert fast["roi_30d_pct"] > slow["roi_30d_pct"]

def test_downside_penalizes_otherwise_equal_flip():
    safe=build_capital_efficiency(total_cost=300,net_profit=120,floor_profit=20,sale_probability=80,liquidity_score=75,velocity=vel())
    bad=build_capital_efficiency(total_cost=300,net_profit=120,floor_profit=-120,sale_probability=80,liquidity_score=75,velocity=vel())
    assert safe["score"] > bad["score"]

def test_zero_cost_is_safe():
    r=build_capital_efficiency(total_cost=0,net_profit=50,floor_profit=0,sale_probability=90,liquidity_score=90,velocity=vel())
    assert r["score"] == 0

def test_sort_key_prefers_scored_then_profit():
    a={"capital_efficiency":{"score":70},"net_profit_estimate":50,"deal_score":60}
    b={"capital_efficiency":{"score":None},"net_profit_estimate":500,"deal_score":99}
    assert capital_efficiency_sort_key(a) > capital_efficiency_sort_key(b)
