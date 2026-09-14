from src.adaptive_deepening import select_dynamic_seller_deep_rows


def _row(index, **changes):
    row = {
        "title": f"Kort {index}",
        "decision": "SKIP",
        "collector_signal_score": 0,
        "sold_comps": 0,
        "market_edge": 0,
    }
    row.update(changes)
    return row


def test_seller_deep_pool_is_small_for_weak_inventory():
    rows = [_row(i) for i in range(100)]
    selected = select_dynamic_seller_deep_rows(rows)
    assert selected == rows[:8]


def test_seller_deep_pool_adds_credible_late_rows_but_stops_at_cap():
    rows = [_row(i) for i in range(100)]
    for i in range(20, 40):
        rows[i]["collector_signal_score"] = 18
    selected = select_dynamic_seller_deep_rows(rows)
    assert len(selected) == 15
    assert rows[20] in selected
    assert rows[26] in selected
    assert rows[27] not in selected
