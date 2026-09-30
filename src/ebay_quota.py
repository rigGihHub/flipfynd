"""Official Browse usage metadata; never stores marketplace listings or tokens."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
import json
import time

import requests

URL = "https://api.ebay.com/developer/analytics/v1_beta/rate_limit/"
_ROOT = Path(__file__).resolve().parent.parent / "ebay_quota_state"
_LOCK = RLock()
_STATE = {}


def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.timestamp() if dt.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def parse_quota(payload):
    rows = []
    for api in payload.get("rateLimits") or []:
        if api.get("apiName") != "browse" or api.get("apiContext") != "buy":
            continue
        for resource in api.get("resources") or []:
            name = str(resource.get("name") or "")
            for rate in resource.get("rates") or []:
                if not all(isinstance(rate.get(k), int) and rate[k] >= 0
                           for k in ("limit", "remaining", "count", "timeWindow")):
                    continue
                reset = timestamp(rate.get("reset"))
                if reset is None:
                    continue
                # Separate getItems quotas must not block item_summary/search.
                normalized = name.casefold().replace("_", "").replace("/", ".")
                applies = ("search" in normalized or normalized in {"browse", "buy.browse", "*", "all"})
                rows.append({"resource": name, **{k: rate[k] for k in
                    ("limit", "remaining", "count", "timeWindow")},
                    "reset": rate["reset"], "reset_at": reset, "applies_to_search": applies})
    return {"status": "OK" if rows else "NO_QUOTA_DATA", "rates": rows,
            "checked_at": datetime.now(timezone.utc).isoformat()}


def _load(key):
    if key not in _STATE:
        try:
            _STATE[key] = json.loads((_ROOT / (key + ".json")).read_text())
        except (OSError, ValueError):
            _STATE[key] = {}
    return _STATE[key]


def _save(key, state):
    _STATE[key] = state
    try:
        _ROOT.mkdir(exist_ok=True)
        path = _ROOT / (key + ".json")
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def quota_status(key):
    with _LOCK:
        return deepcopy(_load(key))


def pause(key, seconds, *, reason="HTTP_429"):
    with _LOCK:
        state = _load(key)
        state["paused_until"] = max(state.get("paused_until", 0), time.time() + seconds)
        state["pause_reason"] = reason
        _save(key, state)


def blocked_until(key):
    with _LOCK:
        state = _load(key)
        resets = [r["reset_at"] for r in state.get("rates", [])
                  if r.get("applies_to_search") and r.get("remaining") == 0
                  and r["reset_at"] > time.time()]
        return max([state.get("paused_until", 0), *resets])


def read_quota(key, token, *, session=requests, timeout=5):
    # Single-flight, at most one metadata request/minute across all sessions.
    # Do not hammer Analytics when its own quota or availability is impaired.
    with _LOCK:
        prior = _load(key)
        if time.time() - prior.get("last_check", 0) < 60:
            return deepcopy(prior)
        try:
            response = session.get(URL, params={"api_context": "buy", "api_name": "browse"},
                headers={"Authorization": "Bearer " + token}, timeout=timeout)
            response.raise_for_status()
            fresh = parse_quota(response.json()) if response.status_code != 204 else {"status": "NO_QUOTA_DATA"}
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            fresh = {"status": "QUOTA_CHECK_FAILED", "http_status": getattr(getattr(exc, "response", None), "status_code", None)}
        fresh["last_check"] = time.time()
        # A successful Analytics refresh is authoritative for usage, but an
        # existing Retry-After pause is still honoured even with remaining quota.
        fresh["paused_until"] = prior.get("paused_until", 0)
        fresh["pause_reason"] = prior.get("pause_reason")
        if fresh["status"] != "OK":
            fresh["rates"] = prior.get("rates", [])
        _save(key, fresh)
        return deepcopy(fresh)


def reserve_call(key):
    """Atomically claim one locally reported search allowance across workers."""
    with _LOCK:
        if blocked_until(key) > time.time():
            return False
        state = _load(key)
        for rate in state.get("rates", []):
            if rate.get("applies_to_search") and rate["reset_at"] > time.time():
                rate["remaining"] = max(0, rate["remaining"] - 1)
        return True
