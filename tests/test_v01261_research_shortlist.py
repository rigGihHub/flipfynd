from src.research_shortlist import evidence_coverage, build_research_shortlist


def test_coverage_exposes_comp_bottleneck():
    items=[{"sold_comparable_count":0},{"sold_comparable_count":0}]
    c=evidence_coverage(items)
    assert c["total"]==2 and c["with_2_sold"]==0


def test_research_shortlist_is_not_buy_logic_and_prefers_evidence():
    rows=build_research_shortlist([
        {"title":"Big Star Base", "deal_score":90, "collector_worth_score":100, "sold_comparable_count":0},
        {"title":"Exact Candidate", "deal_score":60, "collector_worth_score":20, "sold_comparable_count":1, "exact_identity_gate_supports_exact_comp_search":True},
    ], limit=2)
    assert rows[0]["title"]=="Exact Candidate"
    assert "decision" not in rows[0]


def test_research_shortlist_diversifies_players():
    items=[
        {"title":"A1", "deal_score":90, "player_name":"A"},
        {"title":"A2", "deal_score":89, "player_name":"A"},
        {"title":"B1", "deal_score":70, "player_name":"B"},
    ]
    rows=build_research_shortlist(items, limit=2)
    assert [r["title"] for r in rows]==["A1","B1"]
