from src.adaptive_deepening import (
    dynamic_deep_analysis_cap,
    select_adaptive_full_analysis_indices,
    select_dynamic_seller_deep_rows,
)


def _candidate(title="Ordinary base", score=10):
    return ({"titel": title}, {"rank_score": score}, {"score": 0})


def test_main_search_deepens_late_numbered_card():
    candidates = [_candidate(score=100 - i) for i in range(70)]
    candidates.append(_candidate("Late rookie autograph 7/25", score=1))
    cap = dynamic_deep_analysis_cap(candidates, base_limit=12, floor=48, max_cap=96)
    selected = select_adaptive_full_analysis_indices(candidates, base_limit=12, hard_cap=cap)
    assert 70 in selected


def test_seller_search_deepens_value_signal_after_fixed_top_thirty():
    rows = [{"title": f"Base {i}", "collector_signal_score": 0} for i in range(100)]
    rows[87] = {"title": "Hidden numbered rookie", "collector_signal_score": 29}
    selected = select_dynamic_seller_deep_rows(rows, base_limit=30, max_cap=120)
    assert rows[87] in selected
    assert len(selected) == 31


def test_dynamic_caps_still_protect_runtime():
    candidates = [_candidate("Rookie auto /25", score=1) for _ in range(300)]
    assert dynamic_deep_analysis_cap(candidates, max_cap=72) == 72
    rows = [{"collector_signal_score": 40} for _ in range(300)]
    assert len(select_dynamic_seller_deep_rows(rows, max_cap=120)) == 120
