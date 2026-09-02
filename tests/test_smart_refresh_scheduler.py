from datetime import datetime, timezone, timedelta

import src.tradera_fetcher as tf


def _iso(hours_ago):
    return (datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def test_refresh_intervals_follow_depth():
    assert tf._page_refresh_interval_hours(1) == 2
    assert tf._page_refresh_interval_hours(5) == 2
    assert tf._page_refresh_interval_hours(6) == 8
    assert tf._page_refresh_interval_hours(20) == 8
    assert tf._page_refresh_interval_hours(21) == 24
    assert tf._page_refresh_interval_hours(60) == 24
    assert tf._page_refresh_interval_hours(61) == 72


def test_scheduler_prioritizes_shallow_due_pages(monkeypatch):
    now = datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc)
    state = {"categories": {"Fotboll": {
        "loaded_pages": list(range(1, 70)),
        "page_loaded_at": {str(p): _iso(1) for p in range(1, 70)},
    }}}
    state["categories"]["Fotboll"]["page_loaded_at"]["2"] = _iso(3)
    state["categories"]["Fotboll"]["page_loaded_at"]["61"] = _iso(100)
    monkeypatch.setattr(tf, "load_fetch_state", lambda: state)
    plan = tf.get_smart_refresh_plan("Fotboll", now=now)
    assert plan["due"] is True
    assert plan["start_page"] == 2
    assert plan["interval_hours"] == 2


def test_scheduler_reports_fresh_when_nothing_due(monkeypatch):
    now = datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc)
    state = {"categories": {"Hockey - NHL": {
        "loaded_pages": list(range(1, 30)),
        "page_loaded_at": {str(p): _iso(1) for p in range(1, 30)},
    }}}
    monkeypatch.setattr(tf, "load_fetch_state", lambda: state)
    plan = tf.get_smart_refresh_plan("Hockey - NHL", now=now)
    assert plan["due"] is False
    assert plan["next_due_hours"] is not None


def test_scheduler_without_data_starts_at_top(monkeypatch):
    monkeypatch.setattr(tf, "load_fetch_state", lambda: {"categories": {}})
    plan = tf.get_smart_refresh_plan("Fotboll")
    assert plan["due"] is True
    assert plan["start_page"] == 1
    assert plan["end_page"] == 5
