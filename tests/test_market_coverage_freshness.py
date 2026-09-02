from datetime import datetime, timezone, timedelta

import src.tradera_fetcher as tf


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(tf, "STATE_PATH", tmp_path / "state.json")


def test_coverage_reports_contiguous_pages_without_fake_percent(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    now = datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc)
    tf.save_fetch_state({
        "categories": {
            "Hockey - NHL": {
                "loaded_pages": [1, 2, 3, 4],
                "market_next_page": 5,
                "last_fetch_at": (now - timedelta(hours=2)).isoformat(),
            }
        }
    })
    status = tf.get_market_coverage_status("Hockey - NHL", now=now)
    assert status["contiguous_to"] == 4
    assert status["coverage_percent"] is None
    assert "Sida 1–4" in status["coverage_label"]
    assert status["freshness"] == "fresh"


def test_complete_market_is_100_percent(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    now = datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc)
    tf.save_fetch_state({
        "categories": {
            "Fotboll": {
                "loaded_pages": [1, 2, 3],
                "market_next_page": 4,
                "market_complete": True,
                "market_completed_at": (now - timedelta(hours=3)).isoformat(),
            }
        }
    })
    status = tf.get_market_coverage_status("Fotboll", now=now)
    assert status["coverage_percent"] == 100
    assert status["complete"] is True
    assert status["coverage_label"] == "Hela marknaden inläst"


def test_stale_market_is_flagged(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    now = datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc)
    tf.save_fetch_state({
        "categories": {
            "Fotboll": {
                "loaded_pages": [1],
                "last_fetch_at": (now - timedelta(hours=30)).isoformat(),
            }
        }
    })
    status = tf.get_market_coverage_status("Fotboll", now=now)
    assert status["freshness"] == "stale"
    assert status["freshness_label"] == "Gammal – uppdatera"


def test_page_timestamp_updates_when_page_loaded(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    tf.mark_page_loaded("Hockey - NHL", 7)
    state = tf.load_fetch_state()
    info = state["categories"]["Hockey - NHL"]
    assert 7 in info["loaded_pages"]
    assert info["page_loaded_at"]["7"]
