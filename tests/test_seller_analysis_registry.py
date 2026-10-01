from src.seller_analysis_registry import (
    begin_run,
    coverage,
    merge_best_rows,
    normalize_registry,
    record,
    registry_progress,
    rotate_unseen_first,
)


def _item(number):
    return {"tradera_item_id": str(number), "titel": f"Card {number}"}


def test_unseen_listings_rotate_ahead_of_previously_analysed_listings():
    items = [_item(1), _item(2), _item(3)]
    registry = record(begin_run(None), items[:2], "quick")

    ordered = rotate_unseen_first(items, registry, stage="quick")

    assert ordered[0]["tradera_item_id"] == "3"
    assert coverage(registry, items) == {
        "inventory_unique": 3,
        "quick_unique": 2,
        "quick_remaining": 1,
        "full_unique": 0,
        "full_remaining": 3,
        "full_complete": False,
    }


def test_registry_accumulates_unique_full_coverage_across_runs():
    items = [_item(1), _item(2), _item(3)]
    registry = record(begin_run(None), items[:2], "full")
    registry = record(begin_run(registry), items[1:], "full")

    result = coverage(registry, items)

    assert result["full_unique"] == 3
    assert result["full_remaining"] == 0
    assert result["full_complete"] is True


def test_best_positive_research_rows_survive_later_analysis_batches():
    first = {"tradera_item_id": "1", "title": "First", "rank_score": 80}
    second = {"tradera_item_id": "2", "title": "Second", "rank_score": 70}
    registry, _ = merge_best_rows(
        begin_run(None), [first], rank_key=lambda row: row["rank_score"], presentable=lambda row: True,
    )
    registry, rows = merge_best_rows(
        begin_run(registry), [second], rank_key=lambda row: row["rank_score"], presentable=lambda row: True,
    )

    assert [row["title"] for row in rows] == ["First", "Second"]


def test_unknown_registry_schema_fails_closed_to_empty_registry():
    result = normalize_registry({"schema": "old", "entries": {"1": {"full_count": 9}}})
    assert result["entries"] == {}
    assert result["run"] == 0


def test_same_listing_count_prefers_registry_with_more_full_coverage():
    items = [_item(1), _item(2)]
    quick_only = record(begin_run(None), items, "quick")
    newer = record(begin_run(quick_only), [items[0]], "full")

    assert registry_progress(newer) > registry_progress(quick_only)


def test_quick_row_uses_source_listing_id_for_full_coverage_rotation():
    old, new = _item(1), _item(2)
    registry = record(begin_run(None), [old], "full")
    rows = [{"url": "url-1", "source_item": old},
            {"url": "url-2", "source_item": new}]
    assert rotate_unseen_first(rows, registry, stage="full") == rows[::-1]


def test_new_invalid_analysis_removes_previous_positive_highlight():
    registry, _ = merge_best_rows(begin_run(None), [{'id': '1', 'rank_score': 90}],
                                 rank_key=lambda row: row['rank_score'],
                                 presentable=lambda row: row['rank_score'] > 0)
    _, rows = merge_best_rows(registry, [{'id': '1', 'rank_score': -1}],
                             rank_key=lambda row: row['rank_score'],
                             presentable=lambda row: row['rank_score'] > 0)
    assert rows == []
