from src.analysis_scope import select_recent_archive_fast_pool


def _row(number, *, latest=False):
    return {
        "tradera_item_id": str(number),
        "titel": f"2023-24 Upper Deck Player #{number}",
        "pris": 10 + number,
        "frakt": 22,
        **({"discovery_sort": "AddedOn", "latest_scan_at": "2026-09-25"} if latest else {}),
    }


def test_default_search_reserves_archive_coverage_without_growing_budget():
    latest = [_row(i, latest=True) for i in range(120)]
    archive = [_row(i) for i in range(120, 1000)]
    selected, stats = select_recent_archive_fast_pool(
        latest + archive, latest, cap=160, include_older=False
    )
    assert len(selected) == 160
    assert stats["latest_fast_selected"] == 120
    assert stats["archive_fast_selected"] == 40
    assert stats["automatic_archive_coverage"] is True


def test_explicit_archive_mode_uses_shared_pool_and_stays_bounded():
    latest = [_row(i, latest=True) for i in range(50)]
    archive = [_row(i) for i in range(50, 500)]
    selected, stats = select_recent_archive_fast_pool(
        latest + archive, latest, cap=80, include_older=True
    )
    assert len(selected) == 80
    assert stats["automatic_archive_coverage"] is False


def test_no_archive_keeps_all_recent_candidates():
    latest = [_row(i, latest=True) for i in range(20)]
    selected, stats = select_recent_archive_fast_pool(latest, latest, cap=80)
    assert len(selected) == 20
    assert stats["archive_fast_selected"] == 0


def test_4648_listing_market_does_not_silently_exclude_archive():
    latest = [_row(i, latest=True) for i in range(480)]
    archive = [_row(i) for i in range(480, 4648)]
    selected, stats = select_recent_archive_fast_pool(
        latest + archive, latest, cap=160, include_older=False
    )
    assert len(selected) == 160
    assert stats["latest_eligible_candidates"] == 480
    assert stats["archive_eligible_candidates"] == 4168
    assert stats["archive_fast_selected"] == 40
