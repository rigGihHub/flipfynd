from src.momentum_change_detector import detect_momentum_changes, normalize_snapshot


def snap(value, when, metric="prospect_rank"):
    return {"player_name":"Ada Prospect","sport":"Hockey","metric":metric,"value":value,
            "observed_at":when,"source_name":"League","source_url":"https://example.test/source"}


def test_detects_numeric_change_without_interpreting_it():
    out=detect_momentum_changes([snap(18,"2026-08-01T00:00:00Z"),snap(9,"2026-09-01T00:00:00Z")])
    c=out["changes"][0]
    assert c["before"]==18 and c["after"]==9 and c["delta"]==-9.0
    assert c["interpretation"] is None and c["buy_signal_created"] is False


def test_detects_categorical_change():
    out=detect_momentum_changes([snap("AHL","2026-08-01T00:00:00Z","league"),snap("NHL","2026-09-01T00:00:00Z","league")])
    assert out["change_count"]==1 and out["changes"][0]["delta"] is None


def test_unchanged_snapshot_is_not_a_change():
    out=detect_momentum_changes([snap(9,"2026-08-01T00:00:00Z"),snap(9,"2026-09-01T00:00:00Z")])
    assert out["status"]=="INSUFFICIENT_DATA" and out["change_count"]==0


def test_rejects_unattributed_snapshot():
    assert normalize_snapshot({"player_name":"Ada","metric":"rank","value":1})["status"]=="REJECTED"
