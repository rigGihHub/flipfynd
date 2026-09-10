from src.candidate_coverage import diversify_full_analysis_indices


def c(rank, player=None, price=100, **fast):
    base = {"rank_score": rank}
    if player is not None:
        base["player_name"] = player
    base.update(fast)
    return ({"pris": price}, base, {"score": 0})


def test_preserves_baseline_top_n():
    rows = [c(100-i) for i in range(20)]
    out = diversify_full_analysis_indices(rows, list(range(12)), base_limit=12, hard_cap=18, coverage_slots=4)
    assert out[:12] == list(range(12))


def test_adds_rookie_tail_for_coverage():
    rows = [c(100-i) for i in range(12)]
    rows += [c(5, rookie_importance_matched=True)]
    out = diversify_full_analysis_indices(rows, list(range(12)), base_limit=12, hard_cap=18, coverage_slots=4)
    assert 12 in out


def test_adds_low_price_high_demand_relative_to_current_search():
    rows = [
        c(100, player="A", price=500, player_card_demand_score=10),
        c(99, player="B", price=450, player_card_demand_score=20),
        c(98, player="C", price=400, player_card_demand_score=30),
        c(97, player="D", price=350, player_card_demand_score=40),
    ]
    rows += [c(10, player="E", price=50, player_card_demand_score=50)]
    out = diversify_full_analysis_indices(rows, [0,1,2,3], base_limit=4, hard_cap=5, coverage_slots=1)
    assert 4 in out


def test_limits_same_player_in_coverage_tail():
    rows = [c(100-i, player=f"base{i}") for i in range(4)]
    rows += [
        c(20, player="Same", rookie_importance_matched=True),
        c(19, player="Same", rookie_importance_matched=True),
        c(18, player="Same", rookie_importance_matched=True),
        c(17, player="Different", rookie_importance_matched=True),
    ]
    out = diversify_full_analysis_indices(
        rows, [0,1,2,3], base_limit=4, hard_cap=8, coverage_slots=4, max_per_player=2
    )
    selected_same = sum(1 for i in out if rows[i][1].get("player_name") == "Same")
    assert selected_same <= 2
    assert 7 in out


def test_never_exceeds_hard_cap():
    rows = [c(100-i, rookie_importance_matched=True) for i in range(50)]
    out = diversify_full_analysis_indices(rows, list(range(30)), base_limit=12, hard_cap=30, coverage_slots=6)
    assert len(out) <= 30
