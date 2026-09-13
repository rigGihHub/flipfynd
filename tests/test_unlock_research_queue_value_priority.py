from src.unlock_research_queue import build_unlock_research_queue


def test_economic_relevance_can_outrank_trivial_exact_id():
    cheap_exact = {
        "titel": "Cheap commodity parallel",
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_status": "EXACT",
        "sold_comparable_count": 0,
        "deal_score": 8,
        "collector_worth_score": 6,
        "player_market_score": 65,
        "card_hierarchy_score": 5,
        "is_market_edge_candidate": True,
        "player_name": "Star A",
    }
    promising = {
        "titel": "Promising scarcer card",
        "exact_identity_gate_supports_comp_research": True,
        "exact_identity_gate_status": "SÖKBAR_TITEL",
        "sold_comparable_count": 0,
        "deal_score": 78,
        "collector_worth_score": 82,
        "player_market_score": 70,
        "card_hierarchy_score": 75,
        "player_name": "Star B",
    }

    queue = build_unlock_research_queue([cheap_exact, promising], limit=2)

    assert queue["rows"][0]["title"] == "Promising scarcer card"
    assert queue["rows"][0]["research_value_score"] > queue["rows"][1]["research_value_score"]


def test_one_sale_away_still_gets_strong_research_leverage():
    almost_unlocked = {
        "titel": "One sale away",
        "exact_identity_gate_supports_exact_comp_search": True,
        "sold_comparable_count": 1,
        "deal_score": 35,
        "collector_worth_score": 35,
        "player_name": "Player A",
    }
    zero_sales = {
        "titel": "Zero sales",
        "exact_identity_gate_supports_exact_comp_search": True,
        "sold_comparable_count": 0,
        "deal_score": 50,
        "collector_worth_score": 50,
        "player_name": "Player B",
    }

    queue = build_unlock_research_queue([zero_sales, almost_unlocked], limit=2)

    assert queue["rows"][0]["title"] == "One sale away"
    assert queue["near_unlock_count"] == 1
