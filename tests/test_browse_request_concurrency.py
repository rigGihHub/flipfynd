from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
import time

import requests

from src import ebay_browse_context as browse, ebay_quota


def test_inventory_workers_overlap_http_but_keep_dispatch_pacing_and_quota(monkeypatch, tmp_path):
    monkeypatch.setattr(ebay_quota, '_ROOT', tmp_path)
    monkeypatch.setattr(ebay_quota, '_STATE', {})
    monkeypatch.setattr(browse, '_RATE_LIMITS', {})
    monkeypatch.setattr(browse, '_LAST_BROWSE_AT', 0.0)
    monkeypatch.setattr(browse, '_get_token', lambda *args, **kwargs: 'test-token')
    entered, release = Event(), Event()
    starts, lock = [], Lock()
    claims = []
    monkeypatch.setattr(ebay_quota, 'reserve_call', lambda key: (claims.append(key) or True))
    class Response:
        ok = True
        status_code = 200
        def json(self):
            return {'itemSummaries': []}
    def get(*args, **kwargs):
        with lock:
            starts.append(time.monotonic())
            if len(starts) == 3:
                entered.set()
        release.wait(4)
        return Response()
    monkeypatch.setattr(requests, 'get', get)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(browse.fetch_ebay_active_context, str(n),
                   client_id='concurrency', client_secret='test') for n in range(3)]
        try:
            assert entered.wait(2), 'HTTP waiting must not block the other inventory workers'
        finally:
            release.set()
        assert all(future.result()['status'] == 'ACTIVE_CONTEXT_ONLY' for future in futures)
    assert len(claims) == 3
    assert all(later - earlier >= .13 for earlier, later in zip(starts, starts[1:]))
