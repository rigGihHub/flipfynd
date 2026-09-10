from src.find_more_cards import select_second_pass_indices


def test_second_pass_takes_next_unanalysed_candidates():
    assert select_second_pass_indices(20, {0, 1, 2}, extra_limit=4, total_hard_cap=10) == [3, 4, 5, 6]


def test_second_pass_respects_total_hard_cap():
    selected = set(range(43))
    assert select_second_pass_indices(60, selected, extra_limit=12, total_hard_cap=45) == [43, 44]


def test_second_pass_returns_empty_when_cap_reached():
    assert select_second_pass_indices(100, set(range(45)), extra_limit=12, total_hard_cap=45) == []


def test_second_pass_never_reselects_existing_indices():
    out = select_second_pass_indices(8, {0, 2, 4}, extra_limit=5, total_hard_cap=20)
    assert out == [1, 3, 5, 6, 7]
