import json

import src.tradera_fetcher as tf


def _use_temp_state(monkeypatch, tmp_path):
    state_path = tmp_path / "tradera_fetch_state.json"
    monkeypatch.setattr(tf, "STATE_PATH", state_path)
    return state_path


def test_market_sync_starts_on_page_one(monkeypatch, tmp_path):
    _use_temp_state(monkeypatch, tmp_path)
    status = tf.get_market_sync_status("Hockey - NHL")
    assert status["next_page"] == 1
    assert status["complete"] is False


def test_market_batch_advances_resume_point(monkeypatch, tmp_path):
    _use_temp_state(monkeypatch, tmp_path)
    for page in range(1, 13):
        tf.mark_page_loaded("Hockey - NHL", page)
    tf.mark_market_batch("Hockey - NHL", 1, 12, "angiven slutsida 12")
    status = tf.get_market_sync_status("Hockey - NHL")
    assert status["next_page"] == 13
    assert status["max_page_loaded"] == 12
    assert status["complete"] is False


def test_empty_page_marks_market_complete(monkeypatch, tmp_path):
    _use_temp_state(monkeypatch, tmp_path)
    tf.mark_market_batch("Fotboll", 25, 29, "inga annonser på sida 29")
    status = tf.get_market_sync_status("Fotboll")
    assert status["complete"] is True
    assert status["next_page"] == 30
    assert status["completed_at"]


def test_reset_market_sync_keeps_loaded_pages(monkeypatch, tmp_path):
    state_path = _use_temp_state(monkeypatch, tmp_path)
    tf.mark_page_loaded("Fotboll", 1)
    tf.mark_market_batch("Fotboll", 1, 12, "angiven slutsida 12")
    tf.reset_market_sync("Fotboll")
    status = tf.get_market_sync_status("Fotboll")
    assert status["loaded_pages"] == [1]
    # Restart means page 1 again, but already saved ads remain available for dedupe.
    assert status["next_page"] == 1
    assert status["complete"] is False


def test_market_batch_default_is_cloud_bounded():
    assert 1 <= tf.MARKET_BATCH_PAGES <= 12
