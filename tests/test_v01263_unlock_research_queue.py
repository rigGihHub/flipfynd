from src.unlock_research_queue import build_unlock_research_queue


def test_one_sale_away_is_prioritised_over_famous_zero_comp_card():
    rows = build_unlock_research_queue([
        {"title":"Famous Star Base", "deal_score":95, "collector_worth_score":100, "sold_comparable_count":0, "exact_identity_gate_supports_exact_comp_search":True, "player_name":"Star"},
        {"title":"Near Unlock", "deal_score":55, "sold_comparable_count":1, "exact_identity_gate_supports_exact_comp_search":True, "player_name":"Other"},
    ], limit=2)
    assert rows["rows"][0]["title"] == "Near Unlock"
    assert rows["rows"][0]["status"] == "ONE_SALE_AWAY"


def test_identity_first_never_beats_exact_ready_comp_research():
    rows = build_unlock_research_queue([
        {"title":"Unknown", "deal_score":100, "sold_comparable_count":0},
        {"title":"Exact", "deal_score":10, "sold_comparable_count":0, "exact_identity_gate_supports_exact_comp_search":True},
    ], limit=2)
    assert rows["rows"][0]["title"] == "Exact"
    assert rows["rows"][1]["status"] == "IDENTITY_FIRST"


def test_queue_diversifies_players_when_possible():
    rows = build_unlock_research_queue([
        {"title":"A1", "player_name":"A", "sold_comparable_count":1, "exact_identity_gate_supports_exact_comp_search":True},
        {"title":"A2", "player_name":"A", "sold_comparable_count":1, "exact_identity_gate_supports_exact_comp_search":True},
        {"title":"B1", "player_name":"B", "sold_comparable_count":0, "exact_identity_gate_supports_exact_comp_search":True},
    ], limit=2)
    assert [r["title"] for r in rows["rows"]] == ["A1", "B1"]


def test_queue_never_creates_buy_decision():
    out = build_unlock_research_queue([{"title":"X", "sold_comparable_count":1, "exact_identity_gate_supports_exact_comp_search":True}], limit=1)
    assert "decision" not in out["rows"][0]
