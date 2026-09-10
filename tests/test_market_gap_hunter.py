from src.market_gap_hunter import build_market_gap_map, build_market_gap_queue

def test_no_demand_means_no_gap_claim():
    out=build_market_gap_map([{"player_name":"A","player_card_demand_score":0}])
    assert out["candidate_count"]==0
    assert out["creates_new_value"] is False
    assert out["creates_new_decision"] is False

def test_thin_supply_plus_demand_is_research_only_without_market_evidence():
    out=build_market_gap_map([{"player_name":"A","player_card_demand_score":20}])
    row=out["rows"][0]
    assert row["candidate"] is True
    assert row["status"]=="GAP_RESEARCH_ONLY"
    assert row["can_create_buy_decision"] is False
    assert row["can_create_market_value"] is False
    assert row["can_create_max_price"] is False

def test_supported_status_requires_sold_and_safe_value():
    items=[{"player_name":"A","player_card_demand_score":20,"sold_comparable_count":2,"valuation_display_safe":True}]
    row=build_market_gap_map(items)["rows"][0]
    assert row["status"]=="GAP_WITH_MARKET_EVIDENCE"

def test_three_active_candidates_not_called_thin():
    items=[{"player_name":"A","player_card_demand_score":20} for _ in range(3)]
    row=build_market_gap_map(items)["rows"][0]
    assert row["thin_supply"] is False
    assert row["candidate"] is False

def test_queue_only_surfaces_candidates():
    items=[
      {"player_name":"A","player_card_demand_score":20},
      {"player_name":"B","player_card_demand_score":0},
    ]
    q=build_market_gap_queue(items)
    assert [r["player_name"] for r in q["rows"]]==["A"]
