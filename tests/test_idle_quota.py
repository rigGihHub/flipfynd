from threading import Event, Thread
import time
from src import idle_quota, ebay_quota, ebay_browse_context


def test_idle_page_renders_even_when_ebay_never_replies(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    entered, release = Event(), Event()
    monkeypatch.setattr(ebay_quota, '_ROOT', tmp_path)
    def slow_fetch(**kwargs):
        entered.set()
        assert release.wait(5)
        return {'status': 'OK', 'rates': []}
    monkeypatch.setattr(ebay_browse_context, 'fetch_configured_quota', slow_fetch)
    app = AppTest.from_string("""
import streamlit as st
from src.idle_quota import render_counter
render_counter(('idle-page-test', 'secret'))
st.text_input('Sök kort')
st.button('Hitta fynd')
""", default_timeout=2)
    try:
        app.run()
        assert entered.wait(1)
        assert not app.exception
        assert app.text_input[0].label == 'Sök kort'
        assert app.button[-1].label == 'Hitta fynd'
        assert any('bakgrunden' in c.value for c in app.caption)
    finally:
        release.set()


def test_quota_metadata_single_flight_and_cache():
    entered, release = Event(), Event()
    calls = []
    def fetch():
        calls.append(1)
        entered.set()
        assert release.wait(3)
        return {'status': 'OK', 'remaining': 99}
    key = 'single-flight-' + str(time.monotonic())
    try:
        assert idle_quota.request(key, fetch, now=10)[0] == {}
        assert entered.wait(1)
        for _ in range(5):
            value, pending = idle_quota.request(key, fetch, now=11)
            assert pending and value == {}
        assert len(calls) == 1
    finally:
        release.set()
    idle_quota._TASKS[key]['future'].result(timeout=2)
    assert idle_quota.request(key, fetch, now=12) == ({'status': 'OK', 'remaining': 99}, False)
    assert len(calls) == 1


def test_quota_state_read_and_pause_stay_available_during_http(monkeypatch, tmp_path):
    monkeypatch.setattr(ebay_quota, '_ROOT', tmp_path)
    entered, release = Event(), Event()
    class Session:
        def get(self, *args, **kwargs):
            entered.set()
            assert release.wait(3)
            raise ebay_quota.requests.Timeout()
    key = 'blocked-http-test'
    thread = Thread(target=lambda: ebay_quota.read_quota(key, 'token', session=Session()))
    thread.start()
    try:
        assert entered.wait(1)
        # Previously these operations blocked on the same lock as network I/O.
        assert ebay_quota.quota_status(key) == {}
        ebay_quota.pause(key, 100)
    finally:
        release.set()
        thread.join(timeout=3)
    assert not thread.is_alive()
    assert ebay_quota.quota_status(key)['paused_until'] > time.time()
