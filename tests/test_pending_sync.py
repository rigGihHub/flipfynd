from pathlib import Path

from src.pending_sync import (
    clear_pending,
    get_pending,
    load_pending,
    payload_fingerprint,
    pending_summary,
    record_pending,
)


def test_missing_pending_file_is_empty(tmp_path):
    state = load_pending(tmp_path / "pending.json")
    assert state["schema_version"] == 1
    assert state["pending"] == {}


def test_record_pending_keeps_latest_complete_namespace_snapshot(tmp_path):
    path = tmp_path / "pending.json"
    record_pending(path, "sold_comps", [{"id": 1}], error="offline")
    record_pending(path, "sold_comps", [{"id": 1}, {"id": 2}], error="offline again")
    entry = get_pending(path, "sold_comps")
    assert entry is not None
    assert entry["payload"] == [{"id": 1}, {"id": 2}]
    assert entry["last_error"] == "offline again"
    assert entry["fingerprint"] == payload_fingerprint(entry["payload"])


def test_namespaces_are_independent_and_clear_is_explicit(tmp_path):
    path = tmp_path / "pending.json"
    record_pending(path, "sold_comps", [{"id": 1}])
    record_pending(path, "flip_journal", {"schema_version": 1, "entries": [{"id": "x"}]})
    summary = pending_summary(path)
    assert summary["count"] == 2
    assert set(summary["namespaces"]) == {"sold_comps", "flip_journal"}
    assert clear_pending(path, "sold_comps") is True
    assert get_pending(path, "sold_comps") is None
    assert get_pending(path, "flip_journal") is not None
    assert clear_pending(path, "sold_comps") is False


def test_corrupt_pending_file_fails_closed_to_empty(tmp_path):
    path = Path(tmp_path) / "pending.json"
    path.write_text("not-json", encoding="utf-8")
    assert pending_summary(path)["count"] == 0


def test_fingerprint_is_stable_for_equivalent_dict_order():
    assert payload_fingerprint({"b": 2, "a": 1}) == payload_fingerprint({"a": 1, "b": 2})
