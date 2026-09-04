from src.market_overview import build_market_overview


def cov(*, complete=True, freshness="fresh", pages=20):
    return {
        "complete": complete,
        "freshness": freshness,
        "loaded_page_count": pages,
        "next_page": pages + 1,
        "age_hours": 2,
        "missing_pages": [],
    }


def test_ready_when_both_markets_are_fresh_and_complete():
    result = build_market_overview(cov(), cov(), {"due": False}, {"due": False})
    assert result["status"] == "ready"
    assert result["all_complete"] is True


def test_building_is_not_presented_as_failure():
    result = build_market_overview(cov(complete=False), cov(), {"due": False}, {"due": False})
    assert result["status"] == "building"
    assert "användbar" in result["headline"].lower()


def test_due_refresh_has_priority_over_incomplete_coverage():
    result = build_market_overview(cov(complete=False), cov(), {"due": True}, {"due": False})
    assert result["status"] == "needs_update"
    assert result["any_refresh_due"] is True


def test_stale_market_needs_update_even_if_scheduler_has_no_due_block():
    result = build_market_overview(cov(freshness="stale"), cov(), {"due": False}, {"due": False})
    assert result["status"] == "needs_update"
