import base64
import zlib
from src.browser_search_backup import encode_snapshot, decode_snapshot
from src import resumable_search as jobs


def snapshot(status="COMPLETED"):
    return {"status": status, "params": {"widgets": {"search_budget": 1000}},
            "results": [{"titel": "Sparat fynd", "asking_price_opportunity": {"net_margin": 1}}],
            "debug": {"tradera_possible_finds": 1}}


def test_browser_backup_recovers_completed_results_after_server_files_are_lost(tmp_path, monkeypatch):
    token = jobs.new_token()
    original = snapshot()
    blob = encode_snapshot(token, original)
    monkeypatch.setattr(jobs, "_ROOT", tmp_path)
    recovered = decode_snapshot(token, blob)
    assert jobs.load(token) is None
    assert jobs.restore_browser_snapshot(token, recovered)
    assert jobs.load(token)["results"] == original["results"]
    assert jobs.load(token)["params"]["widgets"]["search_budget"] == 1000
    assert not jobs.restore_browser_snapshot(token, snapshot("FAILED"))


def test_backup_rejects_wrong_token_malformed_and_oversized_content():
    token = jobs.new_token()
    assert decode_snapshot(jobs.new_token(), encode_snapshot(token, snapshot())) is None
    assert decode_snapshot(token, "bad content") is None
    assert decode_snapshot(token, base64.b64encode(zlib.compress(b"x" * 32_000_001)).decode()) is None
    assert decode_snapshot("../bad", encode_snapshot(token, snapshot())) is None


def test_running_browser_copy_never_claims_process_work_survived_a_restart():
    token = jobs.new_token()
    result = decode_snapshot(token, encode_snapshot(token, snapshot("RUNNING")))
    assert result["status"] == "INTERRUPTED"
    assert result["params"]["widgets"]["search_budget"] == 1000
