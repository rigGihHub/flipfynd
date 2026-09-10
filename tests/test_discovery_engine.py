from src.discovery_engine import build_discovery_map, select_discovery_indices


def c(price=100, rank=10, player="P", **fast):
    f={"rank_score":rank,"player_name":player}
    f.update(fast)
    return ({"pris":price}, f, {})


def test_map_uses_existing_hunter_signals_without_new_score():
    out=build_discovery_map([
        c(is_hidden_find_candidate=True),
        c(player="Q", rookie_importance_matched=True),
    ])
    assert out["hunter_counts"]["hidden-find"] == 1
    assert out["hunter_counts"]["rookie-prospect"] == 1
    assert out["creates_new_score"] is False
    assert out["creates_new_decision"] is False


def test_discovery_prefers_distinct_omitted_hypotheses():
    candidates=[
        c(rank=100, player="A"),
        c(rank=90, player="B"),
        c(rank=20, player="C", is_hidden_find_candidate=True),
        c(rank=15, player="D", rookie_importance_matched=True),
    ]
    picked=select_discovery_indices(candidates,{0,1},extra_limit=2,total_hard_cap=4)
    assert set(picked)=={2,3}


def test_discovery_does_not_select_signal_free_tail():
    # Same-price rows are deliberately relative low-price candidates; use a
    # clearly above-median tail to test a genuinely signal-free omitted row.
    candidates=[
        c(price=10,rank=100,player="A"),
        c(price=1000,rank=5,player="B"),
        c(price=20,rank=4,player="C"),
    ]
    assert 1 not in select_discovery_indices(candidates,{0,2},extra_limit=2,total_hard_cap=4)


def test_low_price_is_relative_to_current_pool():
    out=build_discovery_map([
        c(price=10,player="A"),
        c(price=100,player="B"),
        c(price=200,player="C"),
    ])
    assert "low-price" in out["rows"][0]["tags"]
    assert "low-price" not in out["rows"][2]["tags"]


def test_total_hard_cap_respected():
    candidates=[c(player=str(i),is_hidden_find_candidate=True) for i in range(10)]
    picked=select_discovery_indices(candidates,{0,1,2,3},extra_limit=10,total_hard_cap=6)
    assert len(picked)==2
