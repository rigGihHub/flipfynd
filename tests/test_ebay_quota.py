from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import pytest
import requests
from src import ebay_quota as quota
from src import ebay_browse_context as browse


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(quota, "_ROOT", tmp_path)
    monkeypatch.setattr(quota, "_STATE", {})


def payload(remaining=2, resource="buy.browse"):
    reset = datetime.fromtimestamp(quota.time.time() + 3600, timezone.utc).isoformat()
    return {"rateLimits": [{"apiName": "browse", "apiContext": "buy", "resources": [
        {"name": resource, "rates": [{"limit": 5000, "count": 5000-remaining,
          "remaining": remaining, "timeWindow": 86400, "reset": reset}]}]}]}


def test_provider_reset_stops_calls_survives_restart_then_expires(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(quota.time, "time", lambda: clock[0])
    quota._save("app", quota.parse_quota(payload(0)))
    assert quota.blocked_until("app") == 4600
    quota._STATE.clear()
    assert not quota.reserve_call("app")
    clock[0] = 4601
    assert quota.reserve_call("app")


def test_get_items_quota_does_not_block_search():
    quota._save("app", quota.parse_quota(payload(0, "buy.browse.item.getItems")))
    assert quota.reserve_call("app")


def test_concurrent_reservations_cannot_overspend_remaining_calls():
    quota._save("app", quota.parse_quota(payload(2)))
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(lambda _: quota.reserve_call("app"), range(20))) == 2


def test_metadata_calls_are_single_flight_and_never_store_token_or_listings():
    calls = []
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return payload()
    class Session:
        def get(self, url, **kw):
            assert url == quota.URL
            assert kw["params"] == {"api_context": "buy"}
            calls.append(1)
            return Response()
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda _: quota.read_quota("app", "secret-token", session=Session()), range(20)))
    assert len(calls) == 1
    saved = (quota._ROOT / "app.json").read_text()
    assert "secret-token" not in saved
    assert "itemSummaries" not in saved


def test_exhausted_quota_prevents_token_and_browse_requests(monkeypatch):
    key = browse._limit_key("daily-limit", "secret")
    quota._save(key, quota.parse_quota(payload(0)))
    monkeypatch.setattr(browse.requests, "post", lambda *a, **kw: pytest.fail("Must not mint a token"))
    monkeypatch.setattr(browse.requests, "get", lambda *a, **kw: pytest.fail("Must not call Browse"))
    with pytest.raises(requests.HTTPError) as error:
        browse.fetch_ebay_active_context("card", client_id="daily-limit", client_secret="secret")
    assert error.value.ebay_stage == "COOLDOWN"
    assert error.value.retry_after_seconds > 3500


def test_failed_analytics_does_not_discard_known_provider_limit():
    quota._save("app", quota.parse_quota(payload(0)))
    class Session:
        def get(self, *a, **kw): raise requests.Timeout()
    result = quota.read_quota("app", "token", session=Session())
    assert result["status"] == "QUOTA_CHECK_FAILED"
    assert not quota.reserve_call("app")


def test_provider_labels_and_missing_optional_count_still_enforce_limit():
    data = payload(0)
    data["rateLimits"][0]["apiName"] = "Browse API"
    del data["rateLimits"][0]["resources"][0]["rates"][0]["count"]
    result = quota.parse_quota(data)
    assert result["status"] == "OK"
    quota._save("app", result)
    assert not quota.reserve_call("app")


def test_pause_label_uses_daily_reset_and_shows_only_search_quota(monkeypatch):
    from src.ebay_quota_ui import quota_lines
    monkeypatch.setattr(quota.time, "time", lambda: 1790744400)
    data = quota.parse_quota(payload(0))
    bulk = quota.parse_quota(payload(5000, "buy.browse.item.bulk"))
    data["rates"] += bulk["rates"]
    data["paused_until"] = quota.time.time() + 900
    lines = quota_lines(data)
    assert len(lines) == 2
    assert "bulk" not in str(lines)
    assert lines[0].split("Återställs ")[1].split(" svensk")[0] in lines[1]
