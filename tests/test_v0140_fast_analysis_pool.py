from src.fast_analysis_pool import select_fast_analysis_pool


def test_pool_is_bounded_and_keeps_strong_structure():
    rows = [{"titel": f"Plain card {i}", "pris": 10 + i, "lank": f"u{i}"} for i in range(1000)]
    rows.append({"titel": "Connor Bedard Rookie Patch Auto 7/25", "pris": 500, "lank": "rare"})
    out = select_fast_analysis_pool(rows, cap=120)
    assert len(out) == 120
    assert any(row["lank"] == "rare" for row in out)


def test_pool_reserves_deterministic_blind_exploration():
    rows = [{"titel": f"Ordinary listing {i}", "pris": 100, "lank": f"u{i}"} for i in range(500)]
    first = select_fast_analysis_pool(rows, cap=100, exploration_fraction=0.25)
    second = select_fast_analysis_pool(rows, cap=100, exploration_fraction=0.25)
    assert [x["lank"] for x in first] == [x["lank"] for x in second]
    assert len(first) == 100


def test_nonphysical_rows_do_not_consume_analysis_budget():
    rows = [
        {"titel": "Gretzky custom proxy card", "lank": "proxy"},
        {"titel": "Gretzky Young Guns rookie", "lank": "real"},
    ]
    assert [x["lank"] for x in select_fast_analysis_pool(rows, cap=10)] == ["real"]
